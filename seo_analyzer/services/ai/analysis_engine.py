"""
AI Analysis Engine
RAG + Claude API로 종합 SEO 분석 및 제안 생성

Features:
- 도메인 컨텍스트 빌드
- RAG 관련 지식 검색
- Claude 기반 분석
- 제안 자동 생성
"""
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timezone
import json

from django.db import transaction
from django.utils import timezone as dj_timezone

logger = logging.getLogger(__name__)


class AIAnalysisEngine:
    """
    AI 분석 엔진
    RAG + Claude API로 종합적인 SEO 분석 및 제안 생성
    """

    def __init__(self):
        self._claude_client = None
        self._vector_store = None

    @property
    def claude_client(self):
        """Lazy initialization of Claude client"""
        if self._claude_client is None:
            try:
                from .claude_client import ClaudeAPIClient
                self._claude_client = ClaudeAPIClient()
            except Exception as e:
                logger.error(f"Failed to initialize Claude client: {e}")
        return self._claude_client

    @property
    def vector_store(self):
        """Lazy initialization of vector store"""
        if self._vector_store is None:
            from .vector_store import get_vector_store
            self._vector_store = get_vector_store()
        return self._vector_store

    def run_full_analysis(
        self,
        domain,
        progress_callback: Callable[[int, int, str], None] = None,
    ) -> Dict:
        """
        도메인 전체 AI 분석 실행

        Args:
            domain: Domain 모델 인스턴스
            progress_callback: 진행률 콜백 (current, total, message)

        Returns:
            분석 결과 딕셔너리
        """
        result = {
            'suggestions': [],
            'insights': [],
            'summary': {},
            'success': True,
            'error': None,
        }

        try:
            # Step 1: 도메인 컨텍스트 빌드 (10%)
            self._update_progress(progress_callback, 10, 100, "도메인 컨텍스트 구축 중...")
            context_text, full_context = self._build_domain_context(domain)

            # Step 2: RAG - 관련 지식 검색 (30%)
            self._update_progress(progress_callback, 30, 100, "관련 지식 검색 중...")
            rag_context = self._retrieve_relevant_knowledge(domain, full_context)

            # Step 3: 과거 효과적 수정 패턴 조회 (50%)
            self._update_progress(progress_callback, 50, 100, "과거 수정 패턴 분석 중...")
            effective_patterns = self._get_effective_patterns(domain)

            # Step 3.5: 실제 페이지 URL 목록 가져오기
            from seo_analyzer.models import Page
            page_urls = list(
                Page.objects.filter(domain=domain)
                .values_list('url', flat=True)
                .order_by('url')[:50]
            )

            # Step 4: Claude 분석 (70%)
            self._update_progress(progress_callback, 70, 100, "AI 분석 진행 중...")
            analysis_result = self._run_claude_analysis(
                context_text,
                rag_context,
                effective_patterns,
                page_urls=page_urls,
                gsc_connected=domain.search_console_connected,
            )

            # Step 5: 제안 생성 (90%)
            self._update_progress(progress_callback, 90, 100, "제안 생성 중...")
            result['suggestions'] = self._generate_suggestions(analysis_result, domain)
            result['insights'] = analysis_result.get('insights', [])
            result['summary'] = {
                'health_score': analysis_result.get('health_score'),
                'top_priorities': analysis_result.get('top_priorities', []),
                'quick_wins': analysis_result.get('quick_wins', []),
                'overall_strategy': analysis_result.get('overall_strategy', ''),
                'analyzed_at': dj_timezone.now().isoformat(),
            }

            # 분석 결과 벡터 DB에 저장
            if self.vector_store.is_available():
                self.vector_store.embed_analysis_result(domain, 'full_analysis', result)

            self._update_progress(progress_callback, 100, 100, "분석 완료")

        except Exception as e:
            logger.error(f"AI analysis failed: {e}", exc_info=True)
            result['success'] = False
            result['error'] = str(e)

        return result

    def _build_domain_context(self, domain) -> tuple:
        """도메인 컨텍스트 빌드"""
        try:
            from .seo_knowledge_builder import SEOKnowledgeBuilder

            builder = SEOKnowledgeBuilder(domain)
            full_context = builder.build_full_context()
            context_text = builder.to_ai_context()

            return context_text, full_context
        except Exception as e:
            logger.error(f"Failed to build domain context: {e}")
            # 폴백: 기본 컨텍스트
            basic_context = f"""
도메인: {domain.domain_name}
총 페이지: {domain.pages.count()}
평균 SEO 점수: {domain.avg_seo_score or 'N/A'}
"""
            return basic_context, {}

    def _retrieve_relevant_knowledge(self, domain, context: Dict) -> str:
        """RAG: 관련 지식 검색"""
        if not self.vector_store.is_available():
            return ""

        try:
            # 주요 이슈 유형 추출
            seo_health = context.get('seo_health', {})
            issue_patterns = seo_health.get('issue_patterns', [])
            top_issues = [p.get('issue_type', '') for p in issue_patterns[:5]]

            # 쿼리 구성
            query = f"""
도메인: {domain.domain_name}
주요 이슈: {', '.join(top_issues) if top_issues else 'N/A'}
평균 SEO 점수: {context.get('domain_overview', {}).get('avg_seo_score', 'N/A')}
"""

            # 벡터 검색
            results = self.vector_store.query_relevant_context(
                query=query,
                domain_id=domain.id,
                n_results=10,
            )

            # 컨텍스트 조합
            context_parts = []

            # 사이트 트리 구조 (우선순위 높음)
            structure_results = results.get('site_structure', {}).get('documents', [])
            if structure_results:
                context_parts.append("=== 사이트 트리 구조 ===")
                context_parts.extend(structure_results[:2])

            # 과거 수정 이력
            fix_results = results.get('fix_history', {}).get('documents', [])
            if fix_results:
                context_parts.append("=== 과거 AI 수정 이력 ===")
                context_parts.extend(fix_results[:5])

            # 분석 캐시
            analysis_results = results.get('analysis_cache', {}).get('documents', [])
            if analysis_results:
                context_parts.append("=== 이전 분석 결과 ===")
                context_parts.extend(analysis_results[:3])

            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return ""

    def _get_effective_patterns(self, domain) -> List[Dict]:
        """효과적이었던 수정 패턴 조회"""
        try:
            from seo_analyzer.models import AIFixHistory

            effective_fixes = AIFixHistory.objects.filter(
                page__domain=domain,
                effectiveness='effective',
            ).order_by('-ai_confidence')[:10]

            return [
                {
                    'issue_type': fix.issue_type,
                    'pattern': fix.fixed_value[:200] if fix.fixed_value else None,
                    'explanation': fix.ai_explanation[:200] if fix.ai_explanation else None,
                    'confidence': fix.ai_confidence,
                }
                for fix in effective_fixes
            ]
        except Exception as e:
            logger.error(f"Failed to get effective patterns: {e}")
            return []

    def _run_claude_analysis(
        self,
        context_text: str,
        rag_context: str,
        effective_patterns: List[Dict],
        page_urls: List[str] = None,
        gsc_connected: bool = False,
    ) -> Dict:
        """Claude API로 종합 분석"""
        if not self.claude_client:
            logger.warning("Claude client not available")
            return self._generate_fallback_analysis()

        try:
            # 효과적 패턴 텍스트
            patterns_text = ""
            if effective_patterns:
                patterns_text = "\n=== 효과적이었던 수정 패턴 ===\n"
                for p in effective_patterns[:5]:
                    patterns_text += f"- {p['issue_type']}: {p['pattern'][:100] if p['pattern'] else 'N/A'}... (신뢰도: {p['confidence']})\n"

            # 실제 페이지 URL 목록
            page_urls_text = ""
            if page_urls:
                page_urls_text = "\n=== 실제 페이지 URL 목록 (page_suggestions에서 사용할 것) ===\n"
                for url in page_urls[:50]:  # 최대 50개
                    page_urls_text += f"- {url}\n"

            # GSC 연동 상태 추가
            gsc_status_text = f"\n=== Google Search Console 연동 상태 ===\n연동됨: {'예' if gsc_connected else '아니오'}\n"
            if gsc_connected:
                gsc_status_text += "※ GSC가 연동되어 있으므로 'GSC 연동' 관련 제안은 제외해주세요.\n"

            system = """당신은 SEO 전문가 AI입니다.
제공된 데이터를 분석하여 실행 가능한 SEO 개선안을 제시합니다.

분석 원칙:
1. 데이터 기반 - Search Console, Lighthouse 데이터 활용
2. 우선순위 - 영향도와 구현 난이도 기준
3. 학습 - 과거 효과적이었던 패턴 참고
4. 구체성 - 모호한 조언 대신 구체적인 액션 제시

⚠️ 중요 규칙 (반드시 준수):

1. 페이지별 제안 (title, description, content, keyword 등):
   - 반드시 page_suggestions 배열에만 넣으세요!
   - top_priorities, quick_wins에 넣지 마세요!
   - page_url은 반드시 "실제 페이지 URL 목록"에서 정확히 복사하세요
   - title 제안: suggestion_type="title", old_title(현재값), new_title(새 제목 50-60자) 필수
   - description 제안: suggestion_type="description", old_description(현재값), new_description(새 설명 120-160자) 필수

2. top_priorities는 사이트 전체 이슈만:
   - robots.txt, HTTPS, 사이트 속도, 구조적 문제 등
   - ❌ 개별 페이지 제목/설명 수정은 절대 넣지 마세요 → page_suggestions에!
   - ❌ "메인 페이지 메타 설명 누락" → page_suggestions의 description 타입으로!

3. quick_wins는 사이트 전체 기술적 개선만:
   - sitemap 제출, canonical, schema 등
   - 개별 페이지 수정은 절대 넣지 마세요

4. 모호한 제안 금지:
   - ❌ "제목 태그 중복 제거" (어떤 페이지? 현재 제목? 새 제목?)
   - ✅ page_suggestions에 페이지별로 old_title, new_title 명시

JSON 형식으로 응답하세요."""

            prompt = f"""다음 도메인에 대한 종합 SEO 분석을 수행해주세요:

{context_text}

{rag_context}

{patterns_text}

{page_urls_text}

{gsc_status_text}

다음 JSON 형식으로 응답하세요:
{{
    "health_score": 0-100,
    "top_priorities": [
        {{
            "priority": 1,
            "category": "카테고리 (예: 기술적 SEO, 사이트 구조, 성능)",
            "issue_name": "사이트 전체 이슈명 (예: robots.txt 누락, HTTPS 미적용, 사이트 속도 저하)",
            "affected_page": "'전체 사이트' 또는 여러 페이지에 공통 영향",
            "description": "문제 상황과 해결 방법을 구체적으로 설명",
            "specific_action": "즉시 실행 가능한 구체적 액션",
            "expected_impact": "예상 효과",
            "effort": "low|medium|high"
        }}
    ],

    ⚠️ top_priorities 규칙:
    - 사이트 전체에 영향을 미치는 기술적 문제만 포함
    - 절대 금지: 개별 페이지 제목/메타설명 수정 → page_suggestions에 넣으세요!
    - 예: ❌ "메인 페이지 메타 설명 누락" → ✅ page_suggestions에 description 타입으로 제공
    "quick_wins": [
        {{
            "description": "사이트 전체 기술적 개선 (예: sitemap 제출, robots.txt 설정)",
            "action": "실행할 액션",
            "affected_scope": "전체 사이트",
            "win_type": "og_tags|canonical|schema|sitemap|indexing|robots"
        }}
    ],

    ⚠️ quick_wins 규칙:
    - 사이트 전체에 적용되는 기술적 개선만 포함
    - 절대 금지: 개별 페이지 제목/설명/콘텐츠 수정 → page_suggestions에 넣으세요
    - 예: ❌ "제목 태그 중복 제거" → ✅ page_suggestions에 페이지별로 old_title/new_title 제공
    "insights": [
        {{
            "type": "insight_type",
            "title": "인사이트 제목",
            "description": "상세 설명",
            "data_source": "데이터 출처"
        }}
    ],
    "page_suggestions": [
        {{
            "page_url": "반드시 위 '실제 페이지 URL 목록'에서 정확히 복사 (예: https://example.com/page)",
            "suggestion_type": "title|description|content|structure|keyword|internal_link",
            "current_issue": "현재 문제 (구체적으로)",
            "suggested_action": "제안 액션",
            "expected_improvement": "예상 개선",

            "old_title": "title 타입 필수: 현재 제목 (페이지에서 가져온 값)",
            "new_title": "title 타입 필수: 새 제목 (50-60자, SEO 최적화)",

            "old_description": "description 타입 필수: 현재 메타설명",
            "new_description": "description 타입 필수: 새 메타설명 (120-160자, 키워드 포함)",

            "manual_guide": "content/structure 등 자동 적용 불가시 수동 가이드"
        }}
    ],

    중요: title/description 제안에는 반드시 old_xxx와 new_xxx 값을 모두 제공하세요.
    값이 없으면 자동 적용이 불가능합니다.
    "overall_strategy": "전체 SEO 전략 요약 (한국어, 2-3문장)"
}}"""

            # Claude API 호출
            result = self.claude_client.analyze_json(prompt, system=system, use_cache=False)

            if result.get('success'):
                return result.get('parsed', {})
            else:
                logger.error(f"Claude analysis failed: {result.get('error')}")
                return self._generate_fallback_analysis()

        except Exception as e:
            logger.error(f"Claude analysis error: {e}")
            return self._generate_fallback_analysis()

    def _generate_fallback_analysis(self) -> Dict:
        """폴백 분석 결과"""
        return {
            'health_score': None,
            'top_priorities': [],
            'quick_wins': [],
            'insights': [],
            'page_suggestions': [],
            'overall_strategy': 'AI 분석을 사용할 수 없습니다. 나중에 다시 시도해주세요.',
        }

    def _generate_suggestions(self, analysis: Dict, domain) -> List[Dict]:
        """분석 결과로부터 제안 생성"""
        from seo_analyzer.models import Page, AIFixHistory
        from datetime import timedelta
        from django.utils import timezone

        suggestions = []
        gsc_connected = domain.search_console_connected

        # GSC 관련 키워드 (연동된 경우 이 키워드 포함 제안 필터링)
        gsc_filter_keywords = ['gsc 연동', 'gsc 미연동', 'search console 연동',
                               'search console 미연동', 'gsc 연결', 'gsc 미연결']

        # 이미 AI로 수정된 페이지+필드 조합 조회 (최근 30일)
        # 재수정 허용: 'ineffective', 'negative' (효과 없거나 부정적)
        # 재수정 안함: 'effective', 'partial', 'unknown' (효과적이거나 아직 측정 안됨)
        recent_fixes = AIFixHistory.objects.filter(
            page__domain=domain,
            created_at__gte=timezone.now() - timedelta(days=30),
            effectiveness__in=['effective', 'partial', 'unknown'],  # 이것들은 스킵
        ).values_list('page_id', 'issue_type')

        # (page_id, field_type) 세트로 변환
        already_fixed = set()
        for page_id, issue_type in recent_fixes:
            # issue_type에서 필드 타입 추출 (예: 'title_optimization' → 'title')
            field_type = issue_type.split('_')[0] if issue_type else ''
            if field_type in ['title', 'description', 'keyword', 'structure']:
                already_fixed.add((page_id, field_type))

        def should_filter_gsc_suggestion(title: str, desc: str) -> bool:
            """GSC가 연동된 경우, GSC 연동 관련 제안 필터링"""
            if not gsc_connected:
                return False
            combined = (title + ' ' + desc).lower()
            return any(kw in combined for kw in gsc_filter_keywords)

        def is_vague_suggestion(title: str, desc: str) -> bool:
            """모호한 제안인지 확인 (구체적인 이슈명/액션이 없는 경우)"""
            combined = (title + ' ' + desc).lower()
            # 모호한 패턴들
            vague_patterns = [
                r'\d+개의?\s*(critical|이슈|문제|오류)',  # "N개의 Critical 이슈"
                r'이슈가\s*\d+개',  # "이슈가 N개"
                r'문제가\s*\d+개',  # "문제가 N개"
                r'즉시\s*해결이?\s*필요',  # "즉시 해결 필요" (구체적 내용 없이)
                r'전체.*성능에.*영향',  # "전체 성능에 영향" (무엇이 영향인지 없음)
            ]
            import re
            for pattern in vague_patterns:
                if re.search(pattern, combined):
                    # 구체적인 이슈명이나 액션이 있으면 통과
                    specific_keywords = ['h1', 'h2', 'title', 'meta', 'alt', 'canonical', 'sitemap',
                                        'robots', 'schema', 'og:', 'description', 'keyword', 'link']
                    if any(kw in combined for kw in specific_keywords):
                        return False
                    return True
            return False

        def is_page_specific_meta_suggestion(priority_item: dict) -> tuple:
            """top_priorities에 잘못 들어온 페이지별 메타 제안인지 확인
            Returns: (is_meta_suggestion, suggestion_type, page_url)
            """
            combined = (
                (priority_item.get('issue_name', '') or '') + ' ' +
                (priority_item.get('description', '') or '') + ' ' +
                (priority_item.get('specific_action', '') or '')
            ).lower()
            affected_page = priority_item.get('affected_page', '')

            # 특정 페이지에 대한 메타 설명/제목 수정인지 확인
            if affected_page and affected_page != '전체 사이트' and 'http' in affected_page:
                if any(kw in combined for kw in ['메타 설명', 'meta description', 'description 누락', '설명 누락']):
                    return (True, 'description', affected_page)
                if any(kw in combined for kw in ['제목 태그', 'title 태그', 'title 누락', '제목 누락', 'title tag']):
                    return (True, 'title', affected_page)

            return (False, None, None)

        # 1. 우선순위 기반 제안
        for priority in analysis.get('top_priorities', []):
            action_type = priority.get('action_type', '')
            category = (priority.get('category', '') or '').lower()
            desc = (priority.get('description', '') or '').lower()

            # GSC 연동된 경우 GSC 연동 관련 제안 스킵
            title_text = priority.get('issue_name') or priority.get('description', '')
            if should_filter_gsc_suggestion(title_text, desc):
                logger.debug(f"Skipping GSC-related suggestion (GSC already connected): {title_text}")
                continue

            # 모호한 제안 스킵
            if is_vague_suggestion(title_text, desc):
                logger.debug(f"Skipping vague suggestion: {title_text}")
                continue

            # 페이지별 메타 제안이 top_priorities에 잘못 들어왔는지 확인
            is_meta, meta_type, page_url = is_page_specific_meta_suggestion(priority)
            if is_meta:
                # page_suggestions 스타일로 변환
                page = None
                if page_url:
                    page = Page.objects.filter(
                        domain=domain,
                        url__icontains=page_url
                    ).first()

                # 현재 값 가져오기
                old_value = ''
                if page and meta_type == 'description':
                    old_value = page.description or ''
                elif page and meta_type == 'title':
                    old_value = page.title or ''

                # specific_action에서 새 값 추출 시도
                new_value = priority.get('specific_action', '')

                suggestions.append({
                    'type': meta_type,  # 'title' or 'description'
                    'priority': priority.get('priority', 1),
                    'title': priority.get('issue_name', '') or priority.get('description', ''),
                    'description': f"대상: {page_url} | 예상 효과: {priority.get('expected_impact', '')}",
                    'expected_impact': priority.get('expected_impact', ''),
                    'action_data': {
                        'page_url': page_url,
                        'suggestion_type': meta_type,
                        f'old_{meta_type}': old_value,
                        f'new_{meta_type}': new_value,
                        'suggested_action': priority.get('specific_action', ''),
                    },
                    'is_auto_applicable': bool(new_value),  # 새 값이 있으면 자동 적용 가능
                    'page_id': page.id if page else None,
                    'page_url': page_url,
                })
                logger.info(f"Converted top_priority meta suggestion to {meta_type} type: {title_text}")
                continue  # 이미 처리했으므로 아래 priority_action 처리 스킵

            # 자동화 가능한 priority_action 타입 판단
            auto_action_types = [
                'gsc_submit_sitemap', 'submit_sitemap', 'sitemap',
                'gsc_request_indexing', 'request_indexing', 'indexing',
                'regenerate_sitemap',
            ]
            is_auto = action_type in auto_action_types

            # 카테고리/설명에서 자동화 가능 여부 추론
            if not is_auto:
                if 'sitemap' in desc and ('submit' in desc or '제출' in desc):
                    is_auto = True
                    priority['action_type'] = 'gsc_submit_sitemap'
                elif 'index' in desc or '색인' in desc:
                    is_auto = True
                    priority['action_type'] = 'gsc_request_indexing'

            # 새 스키마 필드 사용 (issue_name, specific_action)
            issue_name = priority.get('issue_name', '')
            specific_action = priority.get('specific_action', '')
            affected_page = priority.get('affected_page', '')

            # 제목: issue_name > description
            sugg_title = issue_name if issue_name else priority.get('description', '')

            # 설명: specific_action + affected_page
            sugg_desc_parts = []
            if specific_action:
                sugg_desc_parts.append(f"액션: {specific_action}")
            if affected_page:
                sugg_desc_parts.append(f"대상: {affected_page}")
            sugg_desc_parts.append(f"예상 효과: {priority.get('expected_impact', '')}")
            sugg_description = ' | '.join(sugg_desc_parts)

            suggestions.append({
                'type': 'priority_action',
                'priority': priority.get('priority', 1),
                'title': sugg_title,
                'description': sugg_description,
                'expected_impact': f"영향도: 높음, 노력: {priority.get('effort', 'medium')}",
                'action_data': priority,
                'is_auto_applicable': is_auto,
            })

        # 2. 페이지별 제안
        for page_sugg in analysis.get('page_suggestions', []):
            # 페이지 찾기
            page_url = page_sugg.get('page_url', '')
            page = None
            if page_url:
                page = Page.objects.filter(
                    domain=domain,
                    url__icontains=page_url
                ).first() or Page.objects.filter(
                    domain=domain,
                    path__icontains=page_url
                ).first()

            # 페이지를 찾았으면 현재 값들을 action_data에 추가 (before/after 비교용)
            if page:
                # 현재 제목
                if page.title:
                    page_sugg['old_title'] = page.title
                # 현재 메타 설명 (Page 모델의 description 필드)
                if page.description:
                    page_sugg['old_description'] = page.description
                # 현재 SEO 점수 (최신 메트릭에서)
                latest_metrics = page.seo_metrics.first()
                if latest_metrics:
                    page_sugg['current_seo_score'] = latest_metrics.seo_score
                    page_sugg['current_performance_score'] = latest_metrics.performance_score

            sugg_type = page_sugg.get('suggestion_type', 'general')

            # 이미 AI로 수정된 필드인지 체크 (최근 30일 내 효과적이었거나 아직 측정 안 된 경우 스킵)
            if page and (page.id, sugg_type) in already_fixed:
                logger.debug(f"Skipping suggestion for page {page.id}, type {sugg_type} - already fixed recently")
                continue

            # 자동 적용 가능 여부 판단 (확장)
            is_auto = False

            # title 타입: new_title이 있어야 자동 적용 가능
            if sugg_type == 'title' and page_sugg.get('new_title'):
                is_auto = True

            # description 타입: new_description이 있어야 자동 적용 가능
            elif sugg_type == 'description' and page_sugg.get('new_description'):
                is_auto = True

            # keyword 타입: keywords가 있으면 AI가 자동으로 콘텐츠 최적화 가능
            elif sugg_type == 'keyword' and page_sugg.get('keywords'):
                is_auto = True
                # target_field가 없으면 기본값 설정
                if not page_sugg.get('target_field'):
                    page_sugg['target_field'] = 'description'

            # internal_link 타입: suggested_links가 있거나, 페이지가 있으면 자동으로 관련 페이지 찾아서 링크
            elif sugg_type == 'internal_link':
                if page_sugg.get('suggested_links') or page:
                    is_auto = True

            # structure 타입: sitemap priority/changefreq 변경 가능
            elif sugg_type == 'structure':
                if page_sugg.get('new_priority') or page_sugg.get('new_changefreq'):
                    is_auto = True

            suggestions.append({
                'type': sugg_type,
                'priority': 2,
                'page_id': page.id if page else None,
                'title': page_sugg.get('current_issue', ''),
                'description': page_sugg.get('suggested_action', ''),
                'expected_impact': page_sugg.get('expected_improvement', ''),
                'action_data': page_sugg,
                'is_auto_applicable': is_auto and page is not None,
            })

        # 3. Quick wins
        for i, quick_win in enumerate(analysis.get('quick_wins', [])):
            # quick_win이 문자열이면 dict로 변환
            if isinstance(quick_win, str):
                quick_win_data = {'description': quick_win}
                quick_win_text = quick_win.lower()
            else:
                quick_win_data = quick_win
                quick_win_text = (quick_win.get('description', '') or '').lower()

            # GSC 연동된 경우 GSC 연동 관련 quick_win 스킵
            if should_filter_gsc_suggestion(quick_win_text, ''):
                logger.debug(f"Skipping GSC-related quick_win (GSC already connected): {quick_win_text}")
                continue

            # 모호한 quick_win 스킵
            if is_vague_suggestion(quick_win_text, ''):
                logger.debug(f"Skipping vague quick_win: {quick_win_text}")
                continue

            # 자동화 가능한 quick_win 타입 판단 (win_type 필드 우선)
            win_type = quick_win_data.get('win_type', '') if isinstance(quick_win_data, dict) else ''
            is_auto = False

            # 페이지별 제안이 quick_win으로 들어온 경우 - 일괄 자동 수정 가능하게 변환
            # (AI가 해당 페이지들을 찾아서 일괄 수정)
            description_keywords = ['description', '메타 설명', '설명 최적화', '설명 누락', '설명이 짧', '메타설명']
            title_keywords = ['title 최적화', '제목 최적화', '제목 누락', 'h1 누락', 'h1 태그']

            if any(kw in quick_win_text for kw in description_keywords):
                is_auto = True
                quick_win_data['quick_win_type'] = 'bulk_fix_descriptions'
                quick_win_data['target_field'] = 'description'
                logger.debug(f"Converting description quick_win to auto-applicable: {quick_win_text}")
            elif any(kw in quick_win_text for kw in title_keywords):
                is_auto = True
                quick_win_data['quick_win_type'] = 'bulk_fix_titles'
                quick_win_data['target_field'] = 'title'
                logger.debug(f"Converting title quick_win to auto-applicable: {quick_win_text}")
            # win_type 필드가 있으면 사용
            elif win_type in ['og_tags', 'canonical', 'schema', 'sitemap', 'indexing', 'robots']:
                is_auto = True
                quick_win_data['quick_win_type'] = win_type
            # 없으면 텍스트에서 추론
            elif 'og' in quick_win_text or 'open graph' in quick_win_text:
                is_auto = True
                quick_win_data['quick_win_type'] = 'add_og_tags'
            elif 'canonical' in quick_win_text:
                is_auto = True
                quick_win_data['quick_win_type'] = 'add_canonical'
            elif 'schema' in quick_win_text or 'structured' in quick_win_text:
                is_auto = True
                quick_win_data['quick_win_type'] = 'add_schema'
            elif 'sitemap' in quick_win_text and ('submit' in quick_win_text or '제출' in quick_win_text):
                is_auto = True
                quick_win_data['quick_win_type'] = 'sitemap_submit'
            elif 'index' in quick_win_text or '색인' in quick_win_text:
                is_auto = True
                quick_win_data['quick_win_type'] = 'request_indexing'
            elif 'robots' in quick_win_text:
                is_auto = True
                quick_win_data['quick_win_type'] = 'robots_txt'

            # 새 스키마 필드 사용 (action, affected_scope)
            qw_action = quick_win_data.get('action', '') if isinstance(quick_win_data, dict) else ''
            qw_scope = quick_win_data.get('affected_scope', '') if isinstance(quick_win_data, dict) else ''
            qw_title = quick_win_data.get('description', quick_win) if isinstance(quick_win_data, dict) else quick_win
            qw_desc = qw_action if qw_action else '빠르게 적용 가능한 개선'

            # bulk_fix 타입인 경우 영향받는 페이지 목록 조회
            affected_pages = []
            qw_type = quick_win_data.get('quick_win_type', '') if isinstance(quick_win_data, dict) else ''

            if qw_type == 'bulk_fix_descriptions':
                # 메타 설명이 없거나 짧은 페이지 조회 (120자 미만)
                from django.db.models import Q
                from django.db.models.functions import Length
                short_desc_pages = Page.objects.filter(domain=domain).annotate(
                    desc_len=Length('description')
                ).filter(
                    Q(description__isnull=True) | Q(description='') | Q(desc_len__lt=80)
                ).values('id', 'url', 'title', 'description')[:10]

                for p in short_desc_pages:
                    affected_pages.append({
                        'page_id': p['id'],
                        'url': p['url'],
                        'title': p['title'] or '(제목 없음)',
                        'current_value': p['description'] or '(없음)',
                        'issue': '메타 설명 누락/부족' if not p['description'] else f"메타 설명 짧음 ({len(p['description'] or '')}자)",
                    })
                quick_win_data['affected_pages'] = affected_pages
                qw_desc = f"메타 설명 최적화 ({len(affected_pages)}개 페이지)"

            elif qw_type == 'bulk_fix_titles':
                # 제목이 없거나 짧은 페이지 조회
                from django.db.models import Q
                from django.db.models.functions import Length
                short_title_pages = Page.objects.filter(domain=domain).annotate(
                    title_len=Length('title')
                ).filter(
                    Q(title__isnull=True) | Q(title='') | Q(title_len__lt=30)
                ).values('id', 'url', 'title')[:10]

                for p in short_title_pages:
                    affected_pages.append({
                        'page_id': p['id'],
                        'url': p['url'],
                        'current_value': p['title'] or '(없음)',
                        'issue': '제목 누락' if not p['title'] else f"제목 짧음 ({len(p['title'] or '')}자)",
                    })
                quick_win_data['affected_pages'] = affected_pages
                qw_desc = f"제목 최적화 ({len(affected_pages)}개 페이지)"

            elif qw_scope:
                qw_desc += f" (대상: {qw_scope})"

            # bulk_fix 타입은 quick_win 대신 해당 타입으로 저장
            suggestion_type = qw_type if qw_type in ['bulk_fix_descriptions', 'bulk_fix_titles'] else 'quick_win'

            # quick_win 타입 (canonical, og_tags, schema 등)은 Git 배포 필수이므로 자동 적용 불가
            # bulk_fix 타입만 자동 적용 가능 (DB 직접 업데이트)
            is_auto_applicable = is_auto and suggestion_type in ['bulk_fix_descriptions', 'bulk_fix_titles']

            suggestions.append({
                'type': suggestion_type,
                'priority': 1,
                'page_id': None,
                'title': qw_title,
                'description': qw_desc,
                'expected_impact': '즉시 효과',
                'action_data': quick_win_data,
                'is_auto_applicable': is_auto_applicable,
            })

        return suggestions

    @staticmethod
    def _update_progress(callback, current, total, message):
        """진행률 콜백 호출"""
        if callback:
            try:
                callback(current, total, message)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")


class QuickAnalysisEngine:
    """
    빠른 분석 엔진
    특정 페이지나 이슈에 대한 빠른 분석
    """

    def __init__(self):
        self._claude_client = None

    @property
    def claude_client(self):
        if self._claude_client is None:
            try:
                from .claude_client import ClaudeAPIClient
                self._claude_client = ClaudeAPIClient()
            except Exception as e:
                logger.error(f"Failed to initialize Claude client: {e}")
        return self._claude_client

    def analyze_page(self, page) -> Dict:
        """단일 페이지 분석"""
        if not self.claude_client:
            return {'error': 'Claude client not available'}

        try:
            from .ai_auto_fixer import AIAutoFixer

            fixer = AIAutoFixer()
            context = fixer.build_page_context(page, fetch_live=True)

            prompt = f"""
다음 페이지에 대한 빠른 SEO 분석을 수행해주세요:

URL: {page.url}
제목: {page.title or 'N/A'}
경로: {page.path}

컨텍스트:
{json.dumps(context, ensure_ascii=False, indent=2)[:2000]}

JSON 형식으로 3-5개의 개선 제안을 제시하세요:
{{
    "suggestions": [
        {{
            "type": "제안 유형",
            "issue": "현재 문제",
            "action": "제안 액션",
            "priority": 1-3
        }}
    ]
}}
"""

            result = self.claude_client.analyze_json(prompt, use_cache=True)

            if result.get('success'):
                return result.get('parsed', {})
            else:
                return {'error': result.get('error')}

        except Exception as e:
            logger.error(f"Page analysis failed: {e}")
            return {'error': str(e)}

    def analyze_issue(self, issue) -> Dict:
        """단일 이슈 분석"""
        if not self.claude_client:
            return {'error': 'Claude client not available'}

        try:
            prompt = f"""
다음 SEO 이슈에 대한 해결 방안을 제시해주세요:

이슈 유형: {issue.issue_type}
제목: {issue.title}
메시지: {issue.message}
현재 값: {issue.current_value or 'N/A'}
심각도: {issue.severity}

JSON 형식으로 응답하세요:
{{
    "analysis": "이슈 분석",
    "solution": "해결 방안",
    "suggested_value": "제안값 (해당 시)",
    "implementation_steps": ["단계 1", "단계 2"],
    "expected_impact": "예상 효과"
}}
"""

            result = self.claude_client.analyze_json(prompt, use_cache=True)

            if result.get('success'):
                return result.get('parsed', {})
            else:
                return {'error': result.get('error')}

        except Exception as e:
            logger.error(f"Issue analysis failed: {e}")
            return {'error': str(e)}
