"""
SEO Vector Store Service
ChromaDB 기반 벡터 저장소 - RAG 시스템의 핵심

Features:
- 도메인/페이지/수정이력 임베딩
- 관련 컨텍스트 검색
- 효과적 패턴 학습
"""
import logging
import hashlib
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SEOVectorStore:
    """
    ChromaDB 기반 벡터 저장소
    SEO 데이터 임베딩 및 RAG 검색 담당
    """

    def __init__(self, persist_directory: str = None):
        """
        벡터 저장소 초기화

        Args:
            persist_directory: ChromaDB 저장 경로
        """
        if persist_directory is None:
            persist_directory = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'data', 'chromadb'
            )

        self.persist_directory = persist_directory
        self._client = None
        self._collections = None

    @property
    def client(self):
        """Lazy initialization of ChromaDB client"""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings

                print(f"[VectorStore] Initializing ChromaDB at {self.persist_directory}", flush=True)

                # 디렉토리 생성
                os.makedirs(self.persist_directory, exist_ok=True)

                self._client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    )
                )
                print(f"[VectorStore] ChromaDB initialized successfully", flush=True)
            except ImportError as e:
                print(f"[VectorStore] ChromaDB not installed: {e}", flush=True)
                return None
            except Exception as e:
                import traceback
                print(f"[VectorStore] Failed to initialize ChromaDB: {e}\n{traceback.format_exc()}", flush=True)
                return None

        return self._client

    @property
    def collections(self):
        """Lazy initialization of collections"""
        if self._collections is None and self.client:
            self._collections = self._init_collections()
        return self._collections or {}

    def _init_collections(self) -> Dict:
        """컬렉션 초기화"""
        collections = {}
        collection_names = [
            ('domain_knowledge', '도메인 메타정보, 구조, 히스토리'),
            ('page_context', '페이지 SEO 상태, 메트릭, Core Web Vitals'),
            ('fix_history', 'AI 수정 이력 및 효과성'),
            ('analysis_cache', 'AI 분석 결과'),
            ('site_structure', '사이트 트리 구조, 내부 링크, 계층'),
            ('sitemap_entries', 'Sitemap 항목 - priority, changefreq, lastmod'),
            ('suggestion_tracking', 'AI 제안 추적 데이터 - 적용 후 효과성 학습'),  # NEW
        ]

        for name, description in collection_names:
            try:
                collections[name] = self.client.get_or_create_collection(
                    name=name,
                    metadata={
                        "hnsw:space": "cosine",
                        "description": description,
                    }
                )
                logger.debug(f"Collection '{name}' initialized")
            except Exception as e:
                logger.error(f"Failed to create collection '{name}': {e}")

        return collections

    def is_available(self) -> bool:
        """벡터 저장소 사용 가능 여부"""
        return self.client is not None

    # =========================================================================
    # 임베딩 메서드
    # =========================================================================

    def embed_domain(self, domain) -> Optional[str]:
        """
        도메인 데이터 임베딩

        Args:
            domain: Domain 모델 인스턴스

        Returns:
            문서 ID 또는 None
        """
        if not self.is_available():
            return None

        try:
            from ..seo_knowledge_builder import SEOKnowledgeBuilder

            # SEOKnowledgeBuilder로 컨텍스트 빌드
            builder = SEOKnowledgeBuilder(domain)
            context = builder.build_full_context()
            text = builder.to_ai_context()

            doc_id = f"domain_{domain.id}"

            # 메타데이터
            metadata = {
                "domain_id": domain.id,
                "domain_name": domain.domain_name,
                "total_pages": getattr(domain, 'total_pages', 0) or 0,
                "avg_seo_score": float(domain.avg_seo_score or 0),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            self.collections['domain_knowledge'].upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata],
            )

            logger.info(f"Embedded domain: {domain.domain_name}")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to embed domain {domain.id}: {e}")
            return None

    def embed_page(self, page) -> Optional[str]:
        """
        페이지 데이터 임베딩 (트리 구조 + SEO 메트릭 + Core Web Vitals 포함)

        Args:
            page: Page 모델 인스턴스

        Returns:
            문서 ID 또는 None
        """
        if not self.is_available():
            return None

        try:
            # 트리 구조 정보 수집
            children_count = page.children.count() if hasattr(page, 'children') else 0
            parent_url = page.parent_page.url if page.parent_page else None
            sibling_count = page.domain.pages.filter(
                depth_level=page.depth_level
            ).exclude(id=page.id).count()

            # 텍스트 구성 (트리 구조 정보 추가)
            text_parts = [
                f"URL: {page.url}",
                f"Title: {page.title or 'N/A'}",
                f"Description: {page.description[:200] if page.description else 'N/A'}",  # NEW
                f"Path: {page.path}",
                f"Depth Level: {page.depth_level}",
                f"Parent URL: {parent_url or 'Root'}",
                f"Children Count: {children_count}",
                f"Sibling Count: {sibling_count}",
            ]

            # 자식 페이지 URL 목록 (10개)
            if children_count > 0:
                child_urls = list(page.children.values_list('url', flat=True)[:10])
                text_parts.append(f"Child Pages: {', '.join(child_urls)}")

            # 최신 메트릭 추가 (확장)
            latest_metrics = page.seo_metrics.order_by('-snapshot_date').first()
            if latest_metrics:
                # 기본 스코어
                text_parts.extend([
                    f"SEO Score: {latest_metrics.seo_score}",
                    f"Performance Score: {latest_metrics.performance_score}",
                    f"Accessibility Score: {latest_metrics.accessibility_score}",  # NEW
                    f"Best Practices Score: {latest_metrics.best_practices_score}",  # NEW
                    f"Indexed: {latest_metrics.is_indexed}",
                    f"Mobile Friendly: {latest_metrics.mobile_friendly}",  # NEW
                ])

                # Core Web Vitals (NEW)
                cwv_parts = []
                if latest_metrics.lcp:
                    cwv_parts.append(f"LCP: {latest_metrics.lcp}ms")
                if latest_metrics.fid:
                    cwv_parts.append(f"FID: {latest_metrics.fid}ms")
                if latest_metrics.cls:
                    cwv_parts.append(f"CLS: {latest_metrics.cls}")
                if latest_metrics.fcp:
                    cwv_parts.append(f"FCP: {latest_metrics.fcp}ms")
                if cwv_parts:
                    text_parts.append(f"Core Web Vitals: {', '.join(cwv_parts)}")

                # GSC 메트릭 (NEW)
                gsc_parts = []
                if latest_metrics.impressions:
                    gsc_parts.append(f"Impressions: {latest_metrics.impressions}")
                if latest_metrics.clicks:
                    gsc_parts.append(f"Clicks: {latest_metrics.clicks}")
                if latest_metrics.ctr:
                    gsc_parts.append(f"CTR: {latest_metrics.ctr}%")
                if latest_metrics.avg_position:
                    gsc_parts.append(f"Avg Position: {latest_metrics.avg_position}")
                if gsc_parts:
                    text_parts.append(f"GSC Metrics: {', '.join(gsc_parts)}")

                # 키워드 (10개)
                if latest_metrics.top_queries:
                    keywords = [q.get('query', '') for q in latest_metrics.top_queries[:10]]
                    text_parts.append(f"Top Keywords: {', '.join(keywords)}")

            # 이슈 추가 (15개로 확장 + severity 추가)
            issues = page.seo_issues.filter(status='open').order_by('-severity')[:15]
            if issues:
                issue_texts = [f"[{i.severity}] {i.issue_type}: {i.title}" for i in issues]
                text_parts.append(f"Issues ({len(issues)}): {'; '.join(issue_texts)}")

            text = "\n".join(text_parts)
            doc_id = f"page_{page.id}"

            # 메타데이터 (확장)
            metadata = {
                "page_id": page.id,
                "domain_id": page.domain_id,
                "url": page.url,
                "seo_score": float(latest_metrics.seo_score) if latest_metrics and latest_metrics.seo_score else 0,
                "performance_score": float(latest_metrics.performance_score) if latest_metrics and latest_metrics.performance_score else 0,  # NEW
                "issue_count": page.seo_issues.filter(status='open').count(),
                "critical_issue_count": page.seo_issues.filter(status='open', severity='critical').count(),  # NEW
                "depth_level": page.depth_level,
                "children_count": children_count,
                "sibling_count": sibling_count,
                "has_parent": page.parent_page is not None,
                "is_leaf": children_count == 0,
                "has_description": bool(page.description),  # NEW
                "impressions": int(latest_metrics.impressions or 0) if latest_metrics else 0,  # NEW
                "clicks": int(latest_metrics.clicks or 0) if latest_metrics else 0,  # NEW
            }

            self.collections['page_context'].upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata],
            )

            logger.debug(f"Embedded page: {page.url}")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to embed page {page.id}: {e}")
            return None

    def embed_site_structure(self, domain) -> Optional[str]:
        """
        사이트 전체 트리 구조 임베딩

        Args:
            domain: Domain 모델 인스턴스

        Returns:
            문서 ID 또는 None
        """
        if not self.is_available():
            return None

        try:
            from collections import defaultdict

            pages = domain.pages.all().select_related('parent_page')

            # 트리 구조 분석
            depth_stats = defaultdict(int)
            orphan_pages = []
            leaf_pages = []
            hub_pages = []  # 많은 자식을 가진 페이지

            for page in pages:
                depth_stats[page.depth_level] += 1

                # 고아 페이지 (depth > 0인데 parent 없음)
                if page.depth_level > 0 and not page.parent_page:
                    orphan_pages.append(page.url)

                # 리프 페이지 (자식 없음)
                children_count = page.children.count()
                if children_count == 0:
                    leaf_pages.append(page.url)

                # 허브 페이지 (자식 3개 이상)
                if children_count >= 3:
                    hub_pages.append({
                        'url': page.url,
                        'children': children_count,
                        'title': page.title,
                    })

            # 트리 구조 텍스트 생성
            text_parts = [
                f"=== Site Structure for {domain.domain_name} ===",
                f"Total Pages: {pages.count()}",
                f"Max Depth: {max(depth_stats.keys()) if depth_stats else 0}",
                "",
                "Depth Distribution:",
            ]

            for depth in sorted(depth_stats.keys()):
                text_parts.append(f"  Level {depth}: {depth_stats[depth]} pages")

            text_parts.extend([
                "",
                f"Orphan Pages (no parent): {len(orphan_pages)}",
            ])
            if orphan_pages[:5]:
                text_parts.append(f"  Examples: {', '.join(orphan_pages[:5])}")

            text_parts.extend([
                "",
                f"Leaf Pages (no children): {len(leaf_pages)}",
                f"Hub Pages (3+ children): {len(hub_pages)}",
            ])

            if hub_pages[:5]:
                text_parts.append("Top Hub Pages:")
                for hub in sorted(hub_pages, key=lambda x: x['children'], reverse=True)[:5]:
                    text_parts.append(f"  - {hub['url']} ({hub['children']} children)")

            # 구조 품질 평가
            quality_issues = []
            if len(orphan_pages) > 0:
                quality_issues.append(f"{len(orphan_pages)} orphan pages need parents")
            if max(depth_stats.keys(), default=0) > 4:
                quality_issues.append("Deep hierarchy (>4 levels) may hurt SEO")
            if len(hub_pages) == 0 and pages.count() > 10:
                quality_issues.append("No hub pages - consider creating topic clusters")

            text_parts.extend([
                "",
                "Structure Quality Issues:",
                "  " + ("; ".join(quality_issues) if quality_issues else "No major issues"),
            ])

            text = "\n".join(text_parts)
            doc_id = f"structure_{domain.id}"

            metadata = {
                "domain_id": domain.id,
                "domain_name": domain.domain_name,
                "total_pages": pages.count(),
                "max_depth": max(depth_stats.keys()) if depth_stats else 0,
                "orphan_count": len(orphan_pages),
                "leaf_count": len(leaf_pages),
                "hub_count": len(hub_pages),
                "has_quality_issues": len(quality_issues) > 0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            self.collections['site_structure'].upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata],
            )

            logger.info(f"Embedded site structure for {domain.domain_name}")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to embed site structure for domain {domain.id}: {e}")
            return None

    def embed_fix_history(self, fix_history) -> Optional[str]:
        """
        AI 수정 이력 임베딩

        Args:
            fix_history: AIFixHistory 모델 인스턴스

        Returns:
            문서 ID 또는 None
        """
        if not self.is_available():
            return None

        try:
            text = f"""
Issue Type: {fix_history.issue_type}
Original: {fix_history.original_value or 'N/A'}
Fixed: {fix_history.fixed_value}
Explanation: {fix_history.ai_explanation or 'N/A'}
Effectiveness: {fix_history.effectiveness}
Recurred: {fix_history.issue_recurred}
Confidence: {fix_history.ai_confidence or 0}
"""

            doc_id = f"fix_{fix_history.id}"

            metadata = {
                "fix_id": fix_history.id,
                "page_id": fix_history.page_id,
                "domain_id": fix_history.page.domain_id if fix_history.page else None,
                "issue_type": fix_history.issue_type,
                "effectiveness": fix_history.effectiveness,
                "recurred": fix_history.issue_recurred,
                "confidence": float(fix_history.ai_confidence or 0),
            }

            self.collections['fix_history'].upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata],
            )

            logger.debug(f"Embedded fix history: {fix_history.id}")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to embed fix history {fix_history.id}: {e}")
            return None

    def embed_analysis_result(self, domain, analysis_type: str, result: Dict) -> Optional[str]:
        """
        AI 분석 결과 임베딩

        Args:
            domain: Domain 모델 인스턴스
            analysis_type: 분석 유형
            result: 분석 결과 딕셔너리

        Returns:
            문서 ID 또는 None
        """
        if not self.is_available():
            return None

        try:
            import json

            text = f"""
Domain: {domain.domain_name}
Analysis Type: {analysis_type}
Summary: {result.get('summary', {})}
Top Priorities: {result.get('top_priorities', [])}
Insights: {result.get('insights', [])}
"""

            # 해시 기반 ID
            content_hash = hashlib.sha256(
                f"{domain.id}_{analysis_type}_{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]
            doc_id = f"analysis_{content_hash}"

            metadata = {
                "domain_id": domain.id,
                "domain_name": domain.domain_name,
                "analysis_type": analysis_type,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            self.collections['analysis_cache'].upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata],
            )

            logger.debug(f"Embedded analysis result for {domain.domain_name}")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to embed analysis result: {e}")
            return None

    def embed_sitemap_entries(self, domain) -> Dict:
        """
        Sitemap 항목 임베딩 (NEW - 벡터 저장소 개선)

        Args:
            domain: Domain 모델 인스턴스

        Returns:
            임베딩 결과 {'embedded': int, 'errors': list}
        """
        if not self.is_available():
            return {'embedded': 0, 'errors': ['Vector store not available']}

        result = {'embedded': 0, 'errors': []}

        try:
            from seo_analyzer.models import SitemapEntry

            entries = SitemapEntry.objects.filter(domain=domain).select_related('page')

            for entry in entries:
                try:
                    # 텍스트 구성
                    text_parts = [
                        f"=== Sitemap Entry ===",
                        f"URL: {entry.loc}",
                        f"Priority: {entry.priority}",
                        f"Change Frequency: {entry.changefreq}",
                        f"Last Modified: {entry.lastmod}",
                        f"Status: {entry.status}",
                        f"HTTP Status: {entry.http_status_code}",
                        f"AI Suggested: {entry.ai_suggested}",
                    ]

                    # 연결된 페이지 정보
                    if entry.page:
                        text_parts.extend([
                            f"Page Title: {entry.page.title or 'N/A'}",
                            f"Page Depth: {entry.page.depth_level}",
                        ])

                        # 페이지 SEO 스코어
                        page_metrics = entry.page.seo_metrics.order_by('-snapshot_date').first()
                        if page_metrics:
                            text_parts.append(f"Page SEO Score: {page_metrics.seo_score}")

                    text = "\n".join(text_parts)
                    doc_id = f"sitemap_{entry.id}"

                    metadata = {
                        "entry_id": entry.id,
                        "domain_id": domain.id,
                        "page_id": entry.page_id,
                        "url": entry.loc,
                        "priority": float(entry.priority) if entry.priority else 0.5,
                        "changefreq": entry.changefreq or 'monthly',
                        "status": entry.status,
                        "http_status": entry.http_status_code or 200,
                        "ai_suggested": entry.ai_suggested,
                        "has_page": entry.page is not None,
                    }

                    self.collections['sitemap_entries'].upsert(
                        ids=[doc_id],
                        documents=[text],
                        metadatas=[metadata],
                    )

                    result['embedded'] += 1

                except Exception as e:
                    result['errors'].append(f"Entry {entry.id}: {str(e)}")

            logger.info(f"Embedded {result['embedded']} sitemap entries for {domain.domain_name}")

        except Exception as e:
            result['errors'].append(str(e))
            logger.error(f"Failed to embed sitemap entries: {e}")

        return result

    def embed_suggestion_tracking(self, suggestion) -> Optional[str]:
        """
        AI 제안 추적 데이터 임베딩 (tracking/tracked 상태만)

        추적중이거나 완료된 제안의 전체 추적 데이터를 임베딩하여
        AI가 "어떤 제안이 효과적이었는지" 학습할 수 있게 함

        Args:
            suggestion: AISuggestion 모델 인스턴스 (status=tracking/tracked)

        Returns:
            문서 ID 또는 None
        """
        if not self.is_available():
            return None

        # tracking/tracked 상태만 임베딩
        if suggestion.status not in ('tracking', 'tracked'):
            return None

        try:
            from seo_analyzer.models import SuggestionTrackingSnapshot, SuggestionEffectivenessLog

            text_parts = [
                f"=== AI 제안 추적 데이터 ===",
                f"제안 ID: {suggestion.id}",
                f"제안 유형: {suggestion.suggestion_type}",
                f"제안 제목: {suggestion.title}",
                f"제안 설명: {suggestion.description[:300] if suggestion.description else 'N/A'}",
                f"예상 영향: {suggestion.expected_impact or 'N/A'}",
                f"상태: {suggestion.status}",
            ]

            # 페이지 정보
            if suggestion.page:
                text_parts.extend([
                    f"대상 페이지 URL: {suggestion.page.url}",
                    f"대상 페이지 제목: {suggestion.page.title or 'N/A'}",
                ])

            # 추적 기간 정보
            if suggestion.tracking_started_at:
                text_parts.append(f"추적 시작일: {suggestion.tracking_started_at.strftime('%Y-%m-%d')}")
            if suggestion.tracking_ended_at:
                text_parts.append(f"추적 종료일: {suggestion.tracking_ended_at.strftime('%Y-%m-%d')}")
            text_parts.append(f"추적 일수: {suggestion.tracking_days}일")

            # 기준 메트릭 (적용 전)
            baseline = suggestion.baseline_metrics or {}
            if baseline:
                text_parts.extend([
                    f"",
                    f"--- 기준 메트릭 (적용 전) ---",
                    f"노출수: {baseline.get('impressions', 'N/A')}",
                    f"클릭수: {baseline.get('clicks', 'N/A')}",
                    f"CTR: {baseline.get('ctr', 'N/A')}%",
                    f"평균 순위: {baseline.get('position', 'N/A')}",
                    f"SEO 점수: {baseline.get('seo_score', 'N/A')}",
                    f"Health 점수: {baseline.get('health_score', 'N/A')}",
                ])

            # 최종 메트릭 (추적 완료 시)
            final = suggestion.final_metrics or {}
            if final and suggestion.status == 'tracked':
                text_parts.extend([
                    f"",
                    f"--- 최종 메트릭 (추적 완료) ---",
                    f"노출수: {final.get('impressions', 'N/A')}",
                    f"클릭수: {final.get('clicks', 'N/A')}",
                    f"CTR: {final.get('ctr', 'N/A')}%",
                    f"평균 순위: {final.get('position', 'N/A')}",
                    f"SEO 점수: {final.get('seo_score', 'N/A')}",
                ])

                # 변화량 계산
                if baseline:
                    text_parts.append(f"")
                    text_parts.append(f"--- 변화량 ---")

                    for metric in ['impressions', 'clicks']:
                        base_val = baseline.get(metric, 0) or 0
                        final_val = final.get(metric, 0) or 0
                        if base_val > 0:
                            change = final_val - base_val
                            pct = round((change / base_val) * 100, 1)
                            text_parts.append(f"{metric}: {change:+d} ({pct:+.1f}%)")

                    # CTR 변화
                    base_ctr = baseline.get('ctr', 0) or 0
                    final_ctr = final.get('ctr', 0) or 0
                    ctr_change = final_ctr - base_ctr
                    text_parts.append(f"CTR: {ctr_change:+.2f}%p")

                    # 순위 변화 (낮을수록 좋음)
                    base_pos = baseline.get('position', 0) or 0
                    final_pos = final.get('position', 0) or 0
                    if base_pos > 0 and final_pos > 0:
                        pos_change = final_pos - base_pos
                        direction = "개선" if pos_change < 0 else "하락"
                        text_parts.append(f"순위: {pos_change:+.1f} ({direction})")

            # AI 효과 분석 결과
            impact = suggestion.impact_analysis or {}
            if impact:
                text_parts.extend([
                    f"",
                    f"--- AI 효과 분석 ---",
                    f"전체 효과: {impact.get('overall_effect', 'N/A')}",
                    f"신뢰도: {impact.get('confidence', 'N/A')}",
                    f"요약: {impact.get('summary', 'N/A')}",
                ])

                # 요인 분석
                factors = impact.get('factors', [])
                if factors:
                    text_parts.append(f"요인:")
                    for factor in factors[:5]:
                        if isinstance(factor, dict):
                            text_parts.append(f"  - {factor.get('factor', factor)}: {factor.get('impact', '')}")
                        else:
                            text_parts.append(f"  - {factor}")

            # 효과성 점수
            if suggestion.effectiveness_score is not None:
                text_parts.append(f"효과성 점수: {suggestion.effectiveness_score}/100")

            # 일별 추적 스냅샷 요약 (최대 10개 키포인트)
            snapshots = SuggestionTrackingSnapshot.objects.filter(
                suggestion=suggestion
            ).order_by('day_number')

            if snapshots.exists():
                text_parts.extend([
                    f"",
                    f"--- 일별 추적 데이터 (요약) ---",
                ])

                total_snapshots = snapshots.count()
                # 첫날, 7일, 14일, 30일, 60일, 90일, 마지막 날 등 키포인트
                key_days = [1, 7, 14, 30, 60, 90]

                for snapshot in snapshots:
                    if snapshot.day_number in key_days or snapshot == snapshots.last():
                        text_parts.append(
                            f"Day {snapshot.day_number}: "
                            f"impressions={snapshot.impressions}, "
                            f"clicks={snapshot.clicks}, "
                            f"ctr={snapshot.ctr or 0:.2f}%, "
                            f"position={snapshot.avg_position or 'N/A'}"
                        )

                text_parts.append(f"총 스냅샷 수: {total_snapshots}개")

            # 효과성 분석 로그
            effectiveness_logs = SuggestionEffectivenessLog.objects.filter(
                suggestion=suggestion
            ).order_by('-created_at')[:3]

            if effectiveness_logs:
                text_parts.extend([
                    f"",
                    f"--- 효과성 분석 로그 ---",
                ])

                for log in effectiveness_logs:
                    ai_analysis = log.ai_analysis or {}
                    text_parts.append(
                        f"[{log.analysis_type}] Day {log.days_since_applied}: "
                        f"효과성={log.effectiveness_score or 'N/A'}, "
                        f"결론={ai_analysis.get('conclusion', 'N/A')}"
                    )

            text = "\n".join(text_parts)
            doc_id = f"tracking_{suggestion.id}"

            # 메타데이터
            metadata = {
                "suggestion_id": suggestion.id,
                "domain_id": suggestion.domain_id,
                "page_id": suggestion.page_id,
                "suggestion_type": suggestion.suggestion_type,
                "status": suggestion.status,
                "priority": suggestion.priority,
                "tracking_days": suggestion.tracking_days,
                "effectiveness_score": float(suggestion.effectiveness_score) if suggestion.effectiveness_score else 0,
                "is_auto_applicable": suggestion.is_auto_applicable,
                # 변화량 요약 (검색 필터용)
                "impressions_change_pct": self._calc_change_pct(baseline, final, 'impressions'),
                "clicks_change_pct": self._calc_change_pct(baseline, final, 'clicks'),
                "effect_positive": impact.get('overall_effect') == 'positive' if impact else False,
            }

            self.collections['suggestion_tracking'].upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata],
            )

            logger.info(f"Embedded suggestion tracking: {suggestion.id} ({suggestion.status})")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to embed suggestion tracking {suggestion.id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _calc_change_pct(self, baseline: Dict, final: Dict, metric: str) -> float:
        """변화율 계산 헬퍼"""
        if not baseline or not final:
            return 0.0
        base_val = baseline.get(metric, 0) or 0
        final_val = final.get(metric, 0) or 0
        if base_val > 0:
            return round(((final_val - base_val) / base_val) * 100, 1)
        return 0.0

    def embed_fix_history_from_suggestion(self, suggestion) -> Optional[str]:
        """
        SEO 오토픽스에서 생성된 AI 제안을 fix_history 컬렉션에 임베딩

        오토픽스 적용 → AI 제안 생성 → 벡터 임베딩 흐름에서 사용

        Args:
            suggestion: AISuggestion 모델 인스턴스 (source='seo_autofix')

        Returns:
            문서 ID 또는 None
        """
        if not self.is_available():
            return None

        try:
            action_data = suggestion.action_data or {}

            # 오토픽스 소스인지 확인
            source = action_data.get('source', '')

            text_parts = [
                f"=== SEO 오토픽스 히스토리 ===",
                f"제안 ID: {suggestion.id}",
                f"제안 유형: {suggestion.suggestion_type}",
                f"이슈 유형: {action_data.get('issue_type', 'N/A')}",
                f"수정 방법: {action_data.get('fix_method', 'N/A')}",
                f"",
                f"--- 변경 내용 ---",
                f"변경 전: {action_data.get(f'old_{suggestion.suggestion_type}', '없음')[:200]}",
                f"변경 후: {action_data.get(f'new_{suggestion.suggestion_type}', '')[:200]}",
            ]

            # 페이지 정보
            if suggestion.page:
                text_parts.extend([
                    f"",
                    f"--- 대상 페이지 ---",
                    f"URL: {suggestion.page.url}",
                    f"제목: {suggestion.page.title or 'N/A'}",
                ])

            # 추적 정보 (추적 시작된 경우)
            if suggestion.status in ('tracking', 'tracked'):
                text_parts.extend([
                    f"",
                    f"--- 추적 상태 ---",
                    f"상태: {suggestion.status}",
                    f"추적 일수: {suggestion.tracking_days}일",
                ])
                if suggestion.effectiveness_score:
                    text_parts.append(f"효과성 점수: {suggestion.effectiveness_score}")

            document = "\n".join(text_parts)
            doc_id = f"autofix_suggestion_{suggestion.id}"

            # 메타데이터
            metadata = {
                'suggestion_id': str(suggestion.id),
                'domain_id': str(suggestion.domain_id) if suggestion.domain_id else 'N/A',
                'page_id': str(suggestion.page_id) if suggestion.page_id else 'N/A',
                'suggestion_type': suggestion.suggestion_type,
                'issue_type': action_data.get('issue_type', ''),
                'source': source,
                'status': suggestion.status,
                'created_at': suggestion.created_at.isoformat() if suggestion.created_at else '',
            }

            self.collections['fix_history'].upsert(
                ids=[doc_id],
                documents=[document],
                metadatas=[metadata]
            )

            logger.info(f"Embedded autofix suggestion {suggestion.id} to fix_history")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to embed autofix suggestion {suggestion.id}: {e}")
            return None

    def embed_all_tracking_suggestions(self, domain) -> Dict:
        """
        도메인의 모든 추적중/완료된 제안 임베딩

        Args:
            domain: Domain 모델 인스턴스

        Returns:
            임베딩 결과 {'embedded': int, 'errors': list}
        """
        if not self.is_available():
            return {'embedded': 0, 'errors': ['Vector store not available']}

        result = {'embedded': 0, 'errors': []}

        try:
            from seo_analyzer.models import AISuggestion

            # tracking/tracked 상태의 제안만 조회
            suggestions = AISuggestion.objects.filter(
                domain=domain,
                status__in=['tracking', 'tracked']
            ).select_related('page')

            for suggestion in suggestions:
                try:
                    if self.embed_suggestion_tracking(suggestion):
                        result['embedded'] += 1
                except Exception as e:
                    result['errors'].append(f"Suggestion {suggestion.id}: {str(e)}")

            logger.info(f"Embedded {result['embedded']} tracking suggestions for {domain.domain_name}")

        except Exception as e:
            result['errors'].append(str(e))
            logger.error(f"Failed to embed tracking suggestions: {e}")

        return result

    # =========================================================================
    # 검색 메서드
    # =========================================================================

    def query_relevant_context(
        self,
        query: str,
        domain_id: int = None,
        collection_names: List[str] = None,
        n_results: int = 10,  # 10개로 확장 (AI 학습 향상)
    ) -> Dict:
        """
        쿼리에 관련된 컨텍스트 검색 (RAG Retrieval)

        Args:
            query: 검색 쿼리
            domain_id: 도메인 ID (필터링)
            collection_names: 검색할 컬렉션 목록
            n_results: 결과 수

        Returns:
            컬렉션별 검색 결과
        """
        if not self.is_available():
            return {}

        results = {}
        collections = collection_names or list(self.collections.keys())

        for coll_name in collections:
            collection = self.collections.get(coll_name)
            if not collection:
                continue

            where_filter = None
            if domain_id:
                where_filter = {"domain_id": domain_id}

            try:
                result = collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where_filter,
                )
                results[coll_name] = {
                    'documents': result['documents'][0] if result['documents'] else [],
                    'metadatas': result['metadatas'][0] if result['metadatas'] else [],
                    'distances': result['distances'][0] if result.get('distances') else [],
                }
            except Exception as e:
                logger.error(f"Query failed for collection '{coll_name}': {e}")
                results[coll_name] = {'error': str(e)}

        return results

    def get_effective_fixes(
        self,
        issue_type: str = None,
        domain_id: int = None,
        limit: int = 10  # 10개로 확장 (AI 학습 향상)
    ) -> List[Dict]:
        """
        효과적이었던 수정 패턴 조회

        Args:
            issue_type: 이슈 유형 필터
            domain_id: 도메인 ID 필터
            limit: 결과 수

        Returns:
            효과적 수정 패턴 목록
        """
        if not self.is_available():
            return []

        try:
            # where 필터 구성
            where_filter = {"effectiveness": "effective"}
            if issue_type:
                where_filter["issue_type"] = issue_type
            if domain_id:
                where_filter["domain_id"] = domain_id

            query_text = f"effective fix patterns"
            if issue_type:
                query_text += f" for {issue_type}"

            result = self.collections['fix_history'].query(
                query_texts=[query_text],
                n_results=limit,
                where=where_filter if len(where_filter) > 1 else None,
            )

            fixes = []
            for doc, meta in zip(
                result['documents'][0] if result['documents'] else [],
                result['metadatas'][0] if result['metadatas'] else [],
            ):
                fixes.append({
                    'document': doc,
                    'metadata': meta,
                })

            return fixes

        except Exception as e:
            logger.error(f"Failed to get effective fixes: {e}")
            return []

    def get_similar_pages(
        self,
        page,
        n_results: int = 5
    ) -> List[Dict]:
        """
        유사한 페이지 검색

        Args:
            page: Page 모델 인스턴스
            n_results: 결과 수

        Returns:
            유사 페이지 목록
        """
        if not self.is_available():
            return []

        try:
            query = f"URL: {page.url}\nTitle: {page.title}\nPath: {page.path}"

            result = self.collections['page_context'].query(
                query_texts=[query],
                n_results=n_results + 1,  # 자기 자신 제외
                where={"domain_id": page.domain_id},
            )

            pages = []
            for doc, meta in zip(
                result['documents'][0] if result['documents'] else [],
                result['metadatas'][0] if result['metadatas'] else [],
            ):
                # 자기 자신 제외
                if meta.get('page_id') != page.id:
                    pages.append({
                        'document': doc,
                        'metadata': meta,
                    })

            return pages[:n_results]

        except Exception as e:
            logger.error(f"Failed to get similar pages: {e}")
            return []

    def get_effective_tracking_patterns(
        self,
        suggestion_type: str = None,
        domain_id: int = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        효과적이었던 AI 제안 추적 패턴 조회

        이 메서드는 AI가 새 제안을 생성할 때 "어떤 유형의 제안이
        실제로 효과적이었는지" 학습하는 데 사용됨

        Args:
            suggestion_type: 제안 유형 필터 (title, description, content 등)
            domain_id: 도메인 ID 필터
            limit: 결과 수

        Returns:
            효과적 추적 패턴 목록
        """
        if not self.is_available():
            return []

        try:
            # 긍정적 효과가 있었던 제안만 검색
            where_filter = {"effect_positive": True}

            if suggestion_type:
                where_filter["suggestion_type"] = suggestion_type
            if domain_id:
                where_filter["domain_id"] = domain_id

            query_text = "효과적인 AI 제안 패턴"
            if suggestion_type:
                query_text += f" {suggestion_type} 유형"

            result = self.collections['suggestion_tracking'].query(
                query_texts=[query_text],
                n_results=limit,
                where=where_filter if len(where_filter) > 1 else None,
            )

            patterns = []
            for doc, meta in zip(
                result['documents'][0] if result['documents'] else [],
                result['metadatas'][0] if result['metadatas'] else [],
            ):
                patterns.append({
                    'document': doc,
                    'metadata': meta,
                    'effectiveness_score': meta.get('effectiveness_score', 0),
                    'impressions_change_pct': meta.get('impressions_change_pct', 0),
                    'clicks_change_pct': meta.get('clicks_change_pct', 0),
                })

            # 효과성 점수로 정렬
            patterns.sort(key=lambda x: x['effectiveness_score'], reverse=True)
            return patterns

        except Exception as e:
            logger.error(f"Failed to get effective tracking patterns: {e}")
            return []

    def get_tracking_insights_for_page(
        self,
        page,
        n_results: int = 5
    ) -> List[Dict]:
        """
        특정 페이지에 대한 과거 추적 인사이트 조회

        이 페이지 또는 유사한 페이지에서 어떤 제안이 효과적이었는지

        Args:
            page: Page 모델 인스턴스
            n_results: 결과 수

        Returns:
            관련 추적 인사이트 목록
        """
        if not self.is_available():
            return []

        try:
            # 페이지 URL과 제목으로 유사한 추적 기록 검색
            query = f"페이지 URL: {page.url}\n페이지 제목: {page.title or ''}"

            result = self.collections['suggestion_tracking'].query(
                query_texts=[query],
                n_results=n_results,
                where={"domain_id": page.domain_id},
            )

            insights = []
            for doc, meta in zip(
                result['documents'][0] if result['documents'] else [],
                result['metadatas'][0] if result['metadatas'] else [],
            ):
                insights.append({
                    'document': doc,
                    'metadata': meta,
                    'suggestion_type': meta.get('suggestion_type'),
                    'effectiveness_score': meta.get('effectiveness_score', 0),
                    'effect_positive': meta.get('effect_positive', False),
                })

            return insights

        except Exception as e:
            logger.error(f"Failed to get tracking insights for page: {e}")
            return []

    # =========================================================================
    # 관리 메서드
    # =========================================================================

    def sync_domain(self, domain) -> Dict:
        """
        도메인 전체 동기화 (페이지 + Sitemap + 수정이력)

        Args:
            domain: Domain 모델 인스턴스

        Returns:
            동기화 결과
        """
        if not self.is_available():
            return {'success': False, 'error': 'Vector store not available'}

        result = {
            'domain_embedded': False,
            'structure_embedded': False,
            'pages_embedded': 0,
            'sitemap_embedded': 0,
            'fixes_embedded': 0,
            'tracking_embedded': 0,  # NEW: 추적 제안
            'errors': [],
        }

        try:
            # 도메인 임베딩
            if self.embed_domain(domain):
                result['domain_embedded'] = True

            # 사이트 트리 구조 임베딩
            if self.embed_site_structure(domain):
                result['structure_embedded'] = True

            # 페이지 임베딩 (트리 정보 + CWV + GSC 메트릭 포함)
            for page in domain.pages.select_related('parent_page').all():
                if self.embed_page(page):
                    result['pages_embedded'] += 1

            # Sitemap 항목 임베딩 (NEW)
            sitemap_result = self.embed_sitemap_entries(domain)
            result['sitemap_embedded'] = sitemap_result.get('embedded', 0)
            if sitemap_result.get('errors'):
                result['errors'].extend(sitemap_result['errors'])

            # 수정 이력 임베딩
            from seo_analyzer.models import AIFixHistory
            fixes = AIFixHistory.objects.filter(page__domain=domain)
            for fix in fixes:
                if self.embed_fix_history(fix):
                    result['fixes_embedded'] += 1

            # 추적 제안 임베딩 (NEW: AI 학습용)
            tracking_result = self.embed_all_tracking_suggestions(domain)
            result['tracking_embedded'] = tracking_result.get('embedded', 0)
            if tracking_result.get('errors'):
                result['errors'].extend(tracking_result['errors'])

            logger.info(f"Synced domain {domain.domain_name}: {result}")

        except Exception as e:
            result['errors'].append(str(e))
            logger.error(f"Domain sync failed: {e}")

        return result

    def delete_domain_data(self, domain_id: int) -> bool:
        """
        도메인 데이터 삭제

        Args:
            domain_id: 도메인 ID

        Returns:
            성공 여부
        """
        if not self.is_available():
            return False

        try:
            # 각 컬렉션에서 도메인 데이터 삭제
            for coll_name, collection in self.collections.items():
                try:
                    # domain_id로 필터링된 문서 삭제
                    collection.delete(
                        where={"domain_id": domain_id}
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete from {coll_name}: {e}")

            logger.info(f"Deleted vector data for domain {domain_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete domain data: {e}")
            return False

    def get_stats(self) -> Dict:
        """
        벡터 저장소 통계

        Returns:
            컬렉션별 문서 수
        """
        if not self.is_available():
            return {'available': False}

        stats = {'available': True, 'collections': {}}

        for name, collection in self.collections.items():
            try:
                stats['collections'][name] = collection.count()
            except Exception as e:
                stats['collections'][name] = f"Error: {e}"

        return stats


# 싱글톤 인스턴스
_vector_store_instance = None


def get_vector_store() -> SEOVectorStore:
    """벡터 저장소 싱글톤 인스턴스 반환"""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = SEOVectorStore()
    return _vector_store_instance
