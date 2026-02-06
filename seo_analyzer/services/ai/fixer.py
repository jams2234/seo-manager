"""
AI Auto-Fixer Service
Uses Claude AI to generate intelligent SEO fixes based on page context.

Workflow:
1. Fetch live page content (Playwright/requests)
2. Combine with existing SEO data from database
3. AI analyzes and generates contextual fixes
"""
import logging
import requests
from typing import Dict, List, Optional
from urllib.parse import urlparse
from django.utils import timezone

logger = logging.getLogger(__name__)

# Try to import Playwright for JS-rendered pages
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available. Install with: pip install playwright && playwright install chromium")

# BeautifulSoup for HTML parsing
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logger.warning("BeautifulSoup not available. Install with: pip install beautifulsoup4")

from .claude_client import ClaudeAPIClient


class AIAutoFixer:
    """
    AI-powered SEO issue fixer.

    Instead of rule-based template fixes, uses Claude to generate
    contextually appropriate SEO improvements.
    """

    # Issue types that AI can fix
    SUPPORTED_ISSUE_TYPES = [
        'title_too_short',
        'title_too_long',
        'title_missing',
        'meta_description_too_short',
        'meta_description_too_long',
        'meta_description_missing',
        'h1_missing',
        'h1_multiple',
        'low_word_count',
        'missing_alt_text',
    ]

    def __init__(self):
        self.client = ClaudeAPIClient()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    # =========================================================================
    # Web Page Analysis
    # =========================================================================

    def fetch_page_content(self, url: str, use_js_rendering: bool = False) -> Dict:
        """
        Fetch live page content for analysis.

        Args:
            url: Page URL to fetch
            use_js_rendering: Use Playwright for JS-rendered content

        Returns:
            {
                'success': True/False,
                'html': 'raw HTML',
                'text_content': 'extracted text',
                'seo_elements': {...}
            }
        """
        try:
            if use_js_rendering and PLAYWRIGHT_AVAILABLE:
                return self._fetch_with_playwright(url)
            else:
                return self._fetch_with_requests(url)
        except Exception as e:
            logger.error(f"Failed to fetch page {url}: {e}")
            return {'success': False, 'error': str(e)}

    def _fetch_with_requests(self, url: str) -> Dict:
        """Fetch page with simple HTTP request."""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            html = response.text
            seo_elements = self._extract_seo_elements(html)
            text_content = self._extract_text_content(html)

            return {
                'success': True,
                'html': html,
                'text_content': text_content,
                'seo_elements': seo_elements,
                'status_code': response.status_code,
                'method': 'requests',
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'method': 'requests'}

    def _fetch_with_playwright(self, url: str) -> Dict:
        """Fetch page with Playwright (handles JS rendering)."""
        if not PLAYWRIGHT_AVAILABLE:
            return self._fetch_with_requests(url)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until='networkidle', timeout=30000)

                # Wait for content to load
                page.wait_for_timeout(2000)

                html = page.content()
                browser.close()

            seo_elements = self._extract_seo_elements(html)
            text_content = self._extract_text_content(html)

            return {
                'success': True,
                'html': html,
                'text_content': text_content,
                'seo_elements': seo_elements,
                'method': 'playwright',
            }
        except Exception as e:
            logger.warning(f"Playwright fetch failed, falling back to requests: {e}")
            return self._fetch_with_requests(url)

    def _extract_seo_elements(self, html: str) -> Dict:
        """Extract SEO-relevant elements from HTML."""
        if not BS4_AVAILABLE:
            return {}

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Title
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else ''

            # Meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ''

            # H1 tags
            h1_tags = soup.find_all('h1')
            h1_texts = [h1.get_text(strip=True) for h1 in h1_tags]

            # H2 tags (for structure)
            h2_tags = soup.find_all('h2')
            h2_texts = [h2.get_text(strip=True) for h2 in h2_tags[:10]]

            # Canonical
            canonical = soup.find('link', attrs={'rel': 'canonical'})
            canonical_url = canonical.get('href', '') if canonical else ''

            # Meta robots
            robots = soup.find('meta', attrs={'name': 'robots'})
            robots_content = robots.get('content', '') if robots else ''

            # Images without alt
            images = soup.find_all('img')
            images_without_alt = [
                {'src': img.get('src', ''), 'alt': img.get('alt', '')}
                for img in images if not img.get('alt')
            ]

            # Word count
            body = soup.find('body')
            if body:
                # Remove script and style
                for script in body(['script', 'style', 'nav', 'footer', 'header']):
                    script.decompose()
                text = body.get_text(separator=' ', strip=True)
                word_count = len(text.split())
            else:
                word_count = 0

            # Open Graph
            og_title = soup.find('meta', attrs={'property': 'og:title'})
            og_description = soup.find('meta', attrs={'property': 'og:description'})

            return {
                'title': title,
                'title_length': len(title),
                'description': description,
                'description_length': len(description),
                'h1_tags': h1_texts,
                'h1_count': len(h1_texts),
                'h2_tags': h2_texts,
                'canonical_url': canonical_url,
                'robots': robots_content,
                'images_without_alt': images_without_alt[:10],
                'images_without_alt_count': len(images_without_alt),
                'word_count': word_count,
                'og_title': og_title.get('content', '') if og_title else '',
                'og_description': og_description.get('content', '') if og_description else '',
            }
        except Exception as e:
            logger.error(f"Failed to extract SEO elements: {e}")
            return {}

    def _extract_text_content(self, html: str) -> str:
        """Extract main text content from HTML."""
        if not BS4_AVAILABLE:
            return ''

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Remove non-content elements
            for elem in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                elem.decompose()

            # Try to find main content area
            main = soup.find('main') or soup.find('article') or soup.find('body')
            if main:
                text = main.get_text(separator=' ', strip=True)
                # Limit to first 2000 chars for context
                return text[:2000]
            return ''
        except Exception as e:
            logger.error(f"Failed to extract text content: {e}")
            return ''

    def build_page_context(self, page, fetch_live: bool = True) -> Dict:
        """
        Build comprehensive page context from DB + live page.

        Includes:
        - Page metadata and hierarchy
        - SEO metrics (Lighthouse scores, Core Web Vitals)
        - Search Console data (impressions, clicks, CTR, position)
        - Existing issues and suggestions
        - Sitemap entry data
        - Domain context (related pages, keywords)
        - Live page content (if fetch_live=True)

        Args:
            page: Page model instance
            fetch_live: Whether to fetch live page content

        Returns:
            Combined context for AI analysis
        """
        from seo_analyzer.models import SEOMetrics, SEOIssue, SitemapEntry

        # =================================================================
        # 1. Base page context (expanded)
        # =================================================================
        context = {
            'url': page.url,
            'title': page.title,
            'description': page.description,
            'depth_level': page.depth_level,
            'status': page.status,
            'canonical_url': page.canonical_url,
            'has_sitemap_mismatch': page.has_sitemap_mismatch,
            'http_status_code': page.http_status_code,
            'path': page.path,
        }

        # Add parent page info for hierarchy understanding
        if page.parent_page:
            context['parent_page'] = {
                'url': page.parent_page.url,
                'title': page.parent_page.title,
            }

        # Add sitemap entry data from Page model
        if page.sitemap_entry:
            context['sitemap_data'] = page.sitemap_entry

        # =================================================================
        # 2. SEO Metrics (full data from Search Console + Lighthouse)
        # =================================================================
        metrics = SEOMetrics.objects.filter(page=page).order_by('-snapshot_date').first()
        if metrics:
            # Extract keywords as strings from top_queries
            top_queries = metrics.top_queries or []
            if top_queries and isinstance(top_queries[0], dict):
                keywords = [q.get('query', '') for q in top_queries if q.get('query')]
            else:
                keywords = top_queries

            context['db_metrics'] = {
                # Lighthouse scores
                'seo_score': metrics.seo_score,
                'performance_score': metrics.performance_score,
                'accessibility_score': metrics.accessibility_score,
                'best_practices_score': metrics.best_practices_score,

                # Core Web Vitals
                'core_web_vitals': {
                    'lcp': metrics.lcp,  # Largest Contentful Paint
                    'fid': metrics.fid,  # First Input Delay
                    'cls': metrics.cls,  # Cumulative Layout Shift
                    'fcp': metrics.fcp,  # First Contentful Paint
                },

                # Search Console metrics (IMPORTANT for keyword optimization)
                'search_console': {
                    'impressions': metrics.impressions,
                    'clicks': metrics.clicks,
                    'ctr': metrics.ctr,  # Click-through rate
                    'avg_position': metrics.avg_position,
                },

                # Indexing status
                'is_indexed': metrics.is_indexed,
                'index_status': metrics.index_status,
                'coverage_state': metrics.coverage_state,
                'mobile_friendly': metrics.mobile_friendly,

                # Extracted keywords
                'top_queries': top_queries[:10],  # Full data
                'keywords': keywords[:10],  # String list for easy use
            }

        # =================================================================
        # 3. Existing SEO Issues (with full context)
        # =================================================================
        issues = list(SEOIssue.objects.filter(
            page=page,
            status='open'
        ).values(
            'issue_type', 'severity', 'title', 'message',
            'current_value', 'suggested_value', 'fix_suggestion',
            'impact', 'extra_data'
        ))
        context['existing_issues'] = issues

        # =================================================================
        # 4. Sitemap Entry data (if exists)
        # =================================================================
        sitemap_entry = SitemapEntry.objects.filter(page=page).first()
        if sitemap_entry:
            context['sitemap_entry'] = {
                'loc': sitemap_entry.loc,
                'priority': float(sitemap_entry.priority) if sitemap_entry.priority else None,
                'changefreq': sitemap_entry.changefreq,
                'lastmod': sitemap_entry.lastmod.isoformat() if sitemap_entry.lastmod else None,
                'is_valid': sitemap_entry.is_valid,
                'http_status_code': sitemap_entry.http_status_code,
            }

        # =================================================================
        # 5. Domain context (siblings, related pages)
        # =================================================================
        domain = page.domain
        context['domain'] = {
            'name': domain.domain_name,
            'avg_seo_score': domain.avg_seo_score,
            'total_pages': domain.total_pages,
        }

        # Get sibling pages (same depth level) for context
        siblings = list(domain.pages.filter(
            depth_level=page.depth_level
        ).exclude(id=page.id).values('url', 'title')[:5])
        context['sibling_pages'] = siblings

        # Get child pages
        children = list(domain.pages.filter(
            parent_page=page
        ).values('url', 'title')[:5])
        context['child_pages'] = children

        # =================================================================
        # 6. Live page content (if requested)
        # =================================================================
        if fetch_live:
            live_data = self.fetch_page_content(page.url)
            if live_data.get('success'):
                context['live'] = {
                    'seo_elements': live_data.get('seo_elements', {}),
                    'text_content': live_data.get('text_content', ''),
                    'fetch_method': live_data.get('method'),
                }
            else:
                context['live'] = {'error': live_data.get('error')}

        # =================================================================
        # 7. AI Fix History (과거 수정 이력)
        # =================================================================
        from seo_analyzer.models import AIFixHistory

        fix_history = AIFixHistory.objects.filter(
            page=page
        ).order_by('-created_at')[:10]

        if fix_history.exists():
            context['fix_history'] = [
                {
                    'issue_type': h.issue_type,
                    'original_value': h.original_value[:100] if h.original_value else None,
                    'fixed_value': h.fixed_value[:100] if h.fixed_value else None,
                    'ai_explanation': h.ai_explanation[:150] if h.ai_explanation else None,
                    'ai_confidence': h.ai_confidence,
                    'effectiveness': h.effectiveness,
                    'issue_recurred': h.issue_recurred,
                    'recurrence_count': h.recurrence_count,
                    'fixed_at': h.created_at.strftime('%Y-%m-%d'),
                }
                for h in fix_history
            ]

            # 요약 정보
            total_fixes = fix_history.count()
            effective_fixes = sum(1 for h in fix_history if h.effectiveness == 'effective')
            recurred_fixes = sum(1 for h in fix_history if h.issue_recurred)

            context['fix_history_summary'] = {
                'total_fixes': total_fixes,
                'effective_fixes': effective_fixes,
                'recurred_fixes': recurred_fixes,
                'effectiveness_rate': round(effective_fixes / total_fixes * 100, 1) if total_fixes > 0 else 0,
            }

        return context

    def can_fix(self, issue_type: str) -> bool:
        """Check if AI can fix this issue type."""
        return issue_type in self.SUPPORTED_ISSUE_TYPES

    def generate_fix(
        self,
        issue: Dict,
        page_context: Dict,
        domain_context: Dict = None,
    ) -> Dict:
        """
        Generate AI fix for a single issue.

        Args:
            issue: Issue data (type, current_value, etc.)
            page_context: Page data (url, title, content snippet, etc.)
            domain_context: Domain-level context (brand, style, etc.)

        Returns:
            {
                'success': True/False,
                'suggested_value': 'AI generated fix',
                'explanation': 'Why this fix is better',
                'confidence': 0.0-1.0,
            }
        """
        issue_type = issue.get('issue_type', issue.get('type', ''))

        if not self.can_fix(issue_type):
            return {
                'success': False,
                'error': f'Issue type "{issue_type}" not supported for AI fix',
            }

        # Route to appropriate fix generator
        fix_method = self._get_fix_method(issue_type)
        if not fix_method:
            return {
                'success': False,
                'error': f'No fix method for issue type: {issue_type}',
            }

        try:
            return fix_method(issue, page_context, domain_context)
        except Exception as e:
            logger.error(f"AI fix generation failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }

    def generate_batch_fixes(
        self,
        issues: List[Dict],
        page_context: Dict,
        domain_context: Dict = None,
    ) -> Dict:
        """
        Generate AI fixes for multiple issues at once.
        More efficient than individual calls.
        """
        if not issues:
            return {'success': True, 'fixes': []}

        # Filter to supported issues
        supported_issues = [i for i in issues if self.can_fix(i.get('issue_type', i.get('type', '')))]

        if not supported_issues:
            return {
                'success': True,
                'fixes': [],
                'message': 'No supported issues for AI fix',
            }

        # Build combined prompt for efficiency
        try:
            result = self._generate_batch_prompt(supported_issues, page_context, domain_context)
            return result
        except Exception as e:
            logger.error(f"Batch AI fix generation failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }

    def _get_fix_method(self, issue_type: str):
        """Get the appropriate fix method for an issue type."""
        method_map = {
            'title_too_short': self._fix_title,
            'title_too_long': self._fix_title,
            'title_missing': self._fix_title,
            'meta_description_too_short': self._fix_meta_description,
            'meta_description_too_long': self._fix_meta_description,
            'meta_description_missing': self._fix_meta_description,
            'h1_missing': self._fix_h1,
            'h1_multiple': self._fix_h1,
            'low_word_count': self._fix_content,
            'missing_alt_text': self._fix_alt_text,
        }
        return method_map.get(issue_type)

    def _fix_title(
        self,
        issue: Dict,
        page_context: Dict,
        domain_context: Dict = None,
    ) -> Dict:
        """Generate optimized page title using full SEO context."""
        current_title = issue.get('current_value', page_context.get('title', ''))
        url = page_context.get('url', '')
        content_snippet = page_context.get('content_snippet', '')
        brand_name = domain_context.get('brand_name', '') if domain_context else ''

        # Extract rich data from page_context
        db_metrics = page_context.get('db_metrics', {})
        search_console = db_metrics.get('search_console', {})
        keywords = db_metrics.get('keywords', [])
        top_queries = db_metrics.get('top_queries', [])

        # Build Search Console insight text
        sc_text = ""
        if search_console.get('impressions'):
            sc_text = f"""
검색 성과 데이터 (Google Search Console):
- 노출: {search_console.get('impressions', 0):,}회
- 클릭: {search_console.get('clicks', 0):,}회
- CTR: {search_console.get('ctr', 0):.2f}%
- 평균 순위: {search_console.get('avg_position', 0):.1f}위"""

        # Build top queries text with performance
        queries_text = ""
        if top_queries:
            queries_list = []
            for q in top_queries[:5]:
                if isinstance(q, dict):
                    queries_list.append(
                        f"'{q.get('query', '')}' (클릭: {q.get('clicks', 0)}, 순위: {q.get('position', 'N/A')})"
                    )
                else:
                    queries_list.append(str(q))
            queries_text = ", ".join(queries_list)

        # Get sibling pages for consistency
        siblings = page_context.get('sibling_pages', [])
        siblings_text = ""
        if siblings:
            siblings_text = "\n동일 레벨 페이지 제목들: " + ", ".join([s.get('title', '') for s in siblings if s.get('title')])[:200]

        # Build fix history text (과거 수정 이력)
        fix_history = page_context.get('fix_history', [])
        title_history = [h for h in fix_history if 'title' in h.get('issue_type', '')]
        history_text = ""
        if title_history:
            history_items = []
            for h in title_history[:3]:
                status = "✓ 효과적" if h.get('effectiveness') == 'effective' else \
                         "✗ 재발" if h.get('issue_recurred') else "? 미확인"
                history_items.append(
                    f"  - [{h.get('fixed_at')}] '{h.get('fixed_value', '')[:50]}' ({status})"
                )
            history_text = f"""
=== 과거 제목 수정 이력 ===
{chr(10).join(history_items)}
※ 재발한 수정은 피하고, 효과적이었던 패턴 참고"""

        system = """당신은 SEO 전문가입니다. Google Search Console 데이터를 활용하여 검색 성과를 극대화하는 제목을 생성합니다.

제목 최적화 전략:
1. 50-60자 사이 (한글 기준)
2. 실제 검색되는 키워드를 우선 배치 (CTR/순위 기반)
3. 클릭 유도가 잘 되는 키워드 강조
4. 브랜드명은 | 구분자 뒤에 배치
5. 낮은 CTR을 개선하는 방향으로 수정
6. 과거 수정 이력이 있다면 참고하여, 재발한 패턴은 피하고 효과적이었던 패턴을 활용

JSON 형식으로만 응답하세요."""

        prompt = f"""다음 페이지에 대해 검색 성과를 극대화하는 제목을 생성해주세요:

URL: {url}
현재 제목: {current_title or '없음'}
페이지 내용: {content_snippet[:400] if content_snippet else '정보 없음'}
브랜드명: {brand_name or '없음'}
{sc_text}

실제 검색 유입 키워드 (성과순): {queries_text or '정보 없음'}
{siblings_text}
{history_text}

SEO 점수: {db_metrics.get('seo_score', 'N/A')}, 색인 상태: {'색인됨' if db_metrics.get('is_indexed') else '미색인'}

다음 JSON 형식으로 응답하세요:
{{
    "suggested_title": "최적화된 제목 (50-60자)",
    "title_length": 제목길이(숫자),
    "explanation": "이 제목이 검색 성과를 개선하는 이유 (한국어, Search Console 데이터 기반, 과거 이력 참고)",
    "keywords_used": ["사용된", "키워드"],
    "expected_ctr_improvement": "예상 CTR 개선 효과",
    "learned_from_history": "과거 수정에서 배운 점 (해당시)",
    "confidence": 0.0-1.0
}}"""

        result = self.client.analyze_json(prompt, system=system)

        if not result.get('success'):
            return result

        data = result.get('parsed', {})
        return {
            'success': True,
            'suggested_value': data.get('suggested_title', ''),
            'explanation': data.get('explanation', ''),
            'confidence': data.get('confidence', 0.8),
            'metadata': {
                'length': data.get('title_length'),
                'keywords_used': data.get('keywords_used', []),
                'expected_ctr_improvement': data.get('expected_ctr_improvement'),
            }
        }

    def _fix_meta_description(
        self,
        issue: Dict,
        page_context: Dict,
        domain_context: Dict = None,
    ) -> Dict:
        """Generate optimized meta description using full SEO context."""
        current_desc = issue.get('current_value', page_context.get('description', ''))
        title = page_context.get('title', '')
        url = page_context.get('url', '')
        content_snippet = page_context.get('content_snippet', '')

        # Extract rich data
        db_metrics = page_context.get('db_metrics', {})
        search_console = db_metrics.get('search_console', {})
        keywords = db_metrics.get('keywords', [])
        top_queries = db_metrics.get('top_queries', [])

        # Build Search Console data
        sc_text = ""
        if search_console.get('impressions'):
            ctr = search_console.get('ctr', 0)
            ctr_status = "낮음 (개선 필요)" if ctr < 3 else "양호" if ctr < 5 else "우수"
            sc_text = f"""
검색 성과 데이터:
- 노출: {search_console.get('impressions', 0):,}회
- CTR: {ctr:.2f}% ({ctr_status})
- 평균 순위: {search_console.get('avg_position', 0):.1f}위"""

        # Build queries text
        queries_text = ""
        if top_queries:
            queries_list = []
            for q in top_queries[:5]:
                if isinstance(q, dict):
                    queries_list.append(f"'{q.get('query', '')}' (CTR: {q.get('ctr', 0):.1f}%)")
                else:
                    queries_list.append(str(q))
            queries_text = ", ".join(queries_list)

        # Build fix history text (과거 수정 이력)
        fix_history = page_context.get('fix_history', [])
        desc_history = [h for h in fix_history if 'description' in h.get('issue_type', '')]
        history_text = ""
        if desc_history:
            history_items = []
            for h in desc_history[:3]:
                status = "✓ 효과적" if h.get('effectiveness') == 'effective' else \
                         "✗ 재발" if h.get('issue_recurred') else "? 미확인"
                history_items.append(
                    f"  - [{h.get('fixed_at')}] '{h.get('fixed_value', '')[:80]}' ({status})"
                )
            history_text = f"""
=== 과거 메타 설명 수정 이력 ===
{chr(10).join(history_items)}
※ 재발한 수정은 피하고, 효과적이었던 패턴 참고"""

        system = """당신은 SEO 전문가입니다. Google Search Console 데이터를 활용하여 CTR을 극대화하는 메타 설명을 생성합니다.

메타 설명 최적화 전략:
1. 120-160자 사이 (한글 기준)
2. 낮은 CTR을 개선하기 위해 클릭 유도력 있는 문구 사용
3. 실제 검색되는 키워드 자연스럽게 포함
4. 강력한 행동 유도 문구 (CTA) 포함
5. 검색 결과에서 눈에 띄는 가치 제안
6. 과거 수정 이력이 있다면 참고하여, 재발한 패턴은 피하고 효과적이었던 패턴을 활용

JSON 형식으로만 응답하세요."""

        prompt = f"""다음 페이지의 CTR을 개선하는 메타 설명을 생성해주세요:

URL: {url}
페이지 제목: {title or '정보 없음'}
현재 메타 설명: {current_desc or '없음'}
페이지 내용: {content_snippet[:400] if content_snippet else '정보 없음'}
{sc_text}

검색 유입 키워드: {queries_text or '정보 없음'}
{history_text}

다음 JSON 형식으로 응답하세요:
{{
    "suggested_description": "CTR을 높이는 메타 설명 (120-160자)",
    "description_length": 설명길이(숫자),
    "explanation": "이 설명이 CTR을 개선하는 이유 (한국어, 과거 이력 참고)",
    "keywords_used": ["사용된", "키워드"],
    "cta_included": "포함된 행동유도 문구",
    "unique_value_proposition": "차별화된 가치 제안",
    "learned_from_history": "과거 수정에서 배운 점 (해당시)",
    "confidence": 0.0-1.0
}}"""

        result = self.client.analyze_json(prompt, system=system)

        if not result.get('success'):
            return result

        data = result.get('parsed', {})
        return {
            'success': True,
            'suggested_value': data.get('suggested_description', ''),
            'explanation': data.get('explanation', ''),
            'confidence': data.get('confidence', 0.8),
            'metadata': {
                'length': data.get('description_length'),
                'keywords_used': data.get('keywords_used', []),
                'cta': data.get('cta_included'),
                'uvp': data.get('unique_value_proposition'),
            }
        }

    def _fix_h1(
        self,
        issue: Dict,
        page_context: Dict,
        domain_context: Dict = None,
    ) -> Dict:
        """Generate optimized H1 heading."""
        current_h1 = issue.get('current_value', '')
        title = page_context.get('title', '')
        url = page_context.get('url', '')
        content_snippet = page_context.get('content_snippet', '')

        system = """당신은 SEO 전문가입니다. 웹페이지의 최적화된 H1 제목을 생성합니다.

H1 작성 규칙:
1. 페이지당 하나의 H1만 사용
2. 페이지의 주제를 명확히 전달
3. 타이틀 태그와 유사하지만 동일하지 않게
4. 20-70자 사이 권장
5. 주요 키워드 포함

JSON 형식으로만 응답하세요."""

        prompt = f"""다음 페이지에 대해 최적화된 H1 제목을 생성해주세요:

URL: {url}
페이지 제목(title): {title or '정보 없음'}
현재 H1: {current_h1 or '없음'}
페이지 내용 요약: {content_snippet[:300] if content_snippet else '정보 없음'}

다음 JSON 형식으로 응답하세요:
{{
    "suggested_h1": "최적화된 H1 제목",
    "explanation": "이 H1이 좋은 이유 (한국어)",
    "differs_from_title": true/false,
    "confidence": 0.0-1.0
}}"""

        result = self.client.analyze_json(prompt, system=system)

        if not result.get('success'):
            return result

        data = result.get('parsed', {})
        return {
            'success': True,
            'suggested_value': data.get('suggested_h1', ''),
            'explanation': data.get('explanation', ''),
            'confidence': data.get('confidence', 0.8),
        }

    def _fix_content(
        self,
        issue: Dict,
        page_context: Dict,
        domain_context: Dict = None,
    ) -> Dict:
        """Suggest content improvements for low word count."""
        current_word_count = issue.get('current_value', 0)
        title = page_context.get('title', '')
        url = page_context.get('url', '')
        content_snippet = page_context.get('content_snippet', '')

        system = """당신은 SEO 콘텐츠 전문가입니다. 콘텐츠 개선 제안을 제공합니다.

콘텐츠 개선 규칙:
1. 최소 300단어 이상 권장
2. 주제와 관련된 섹션 제안
3. FAQ, 상세 설명 등 추가 가능한 콘텐츠 유형 제안
4. 키워드 자연스럽게 포함하는 방법

JSON 형식으로만 응답하세요."""

        prompt = f"""다음 페이지의 콘텐츠 개선점을 제안해주세요:

URL: {url}
페이지 제목: {title or '정보 없음'}
현재 단어 수: {current_word_count}
현재 내용 샘플: {content_snippet[:500] if content_snippet else '정보 없음'}

다음 JSON 형식으로 응답하세요:
{{
    "suggested_sections": ["추가할 섹션 1", "추가할 섹션 2"],
    "content_ideas": ["콘텐츠 아이디어 1", "콘텐츠 아이디어 2"],
    "target_word_count": 권장단어수(숫자),
    "explanation": "왜 이런 콘텐츠가 필요한지 (한국어)",
    "example_outline": "간단한 콘텐츠 아웃라인",
    "confidence": 0.0-1.0
}}"""

        result = self.client.analyze_json(prompt, system=system)

        if not result.get('success'):
            return result

        data = result.get('parsed', {})
        return {
            'success': True,
            'suggested_value': data.get('example_outline', ''),
            'explanation': data.get('explanation', ''),
            'confidence': data.get('confidence', 0.7),
            'metadata': {
                'sections': data.get('suggested_sections', []),
                'ideas': data.get('content_ideas', []),
                'target_words': data.get('target_word_count'),
            }
        }

    def _fix_alt_text(
        self,
        issue: Dict,
        page_context: Dict,
        domain_context: Dict = None,
    ) -> Dict:
        """Generate alt text for images (placeholder - needs image context)."""
        image_src = issue.get('image_src', '')
        image_filename = image_src.split('/')[-1] if image_src else ''
        page_title = page_context.get('title', '')

        system = """당신은 SEO 및 웹 접근성 전문가입니다. 이미지의 alt 텍스트를 생성합니다.

Alt 텍스트 작성 규칙:
1. 이미지 내용을 정확히 설명
2. 125자 이내
3. 키워드 스터핑 금지
4. 장식용 이미지는 빈 alt 사용
5. 맥락에 맞는 설명

JSON 형식으로만 응답하세요."""

        prompt = f"""다음 이미지에 대한 alt 텍스트를 생성해주세요:

이미지 파일명: {image_filename or '정보 없음'}
이미지 URL: {image_src or '정보 없음'}
페이지 제목: {page_title or '정보 없음'}
페이지 맥락: 이미지가 포함된 페이지의 주제를 고려하세요

다음 JSON 형식으로 응답하세요:
{{
    "suggested_alt": "이미지 설명 alt 텍스트",
    "explanation": "이 alt 텍스트가 적절한 이유",
    "is_decorative": false,
    "confidence": 0.0-1.0
}}"""

        result = self.client.analyze_json(prompt, system=system)

        if not result.get('success'):
            return result

        data = result.get('parsed', {})
        return {
            'success': True,
            'suggested_value': data.get('suggested_alt', ''),
            'explanation': data.get('explanation', ''),
            'confidence': data.get('confidence', 0.6),  # Lower confidence without actual image
            'metadata': {
                'is_decorative': data.get('is_decorative', False),
            }
        }

    def _generate_batch_prompt(
        self,
        issues: List[Dict],
        page_context: Dict,
        domain_context: Dict = None,
    ) -> Dict:
        """Generate fixes for multiple issues using full SEO context."""
        url = page_context.get('url', '')
        title = page_context.get('title', '')
        description = page_context.get('description', '')
        content_snippet = page_context.get('content_snippet', '')
        brand_name = domain_context.get('brand_name', '') if domain_context else ''

        # Extract rich data
        db_metrics = page_context.get('db_metrics', {})
        search_console = db_metrics.get('search_console', {})
        keywords = db_metrics.get('keywords', [])
        top_queries = db_metrics.get('top_queries', [])
        domain_info = page_context.get('domain', {})

        # Build Search Console summary
        sc_text = ""
        if search_console.get('impressions'):
            sc_text = f"""
=== 검색 성과 (Google Search Console) ===
노출: {search_console.get('impressions', 0):,}회 | 클릭: {search_console.get('clicks', 0):,}회
CTR: {search_console.get('ctr', 0):.2f}% | 평균 순위: {search_console.get('avg_position', 0):.1f}위
SEO 점수: {db_metrics.get('seo_score', 'N/A')} | 색인 상태: {'색인됨' if db_metrics.get('is_indexed') else '미색인'}"""

        # Build queries text with performance
        queries_text = ""
        if top_queries:
            queries_list = []
            for q in top_queries[:5]:
                if isinstance(q, dict):
                    queries_list.append(f"'{q.get('query', '')}' (클릭:{q.get('clicks', 0)}, 순위:{q.get('position', 'N/A')})")
                else:
                    queries_list.append(str(q))
            queries_text = ", ".join(queries_list)

        # Build issues list for prompt
        issues_text = []
        for i, issue in enumerate(issues, 1):
            issue_type = issue.get('issue_type', issue.get('type', ''))
            current_value = issue.get('current_value', '')
            issues_text.append(f"{i}. {issue_type}: 현재 값 = '{current_value}'")

        system = """당신은 SEO 전문가입니다. Google Search Console 데이터를 활용하여 검색 성과(CTR, 순위)를 개선하는 방향으로 여러 SEO 이슈를 한번에 수정합니다.

수정 원칙:
- title: 50-60자, 실제 검색되는 키워드 우선 배치, 브랜드명은 | 뒤에
- meta_description: 120-160자, CTR 향상을 위한 강력한 CTA 포함
- h1: 20-70자, 타이틀과 유사하지만 동일하지 않게

중요: 실제 검색 데이터에 기반한 키워드를 활용하세요.

JSON 형식으로만 응답하세요."""

        prompt = f"""다음 페이지의 여러 SEO 이슈를 검색 성과 데이터 기반으로 수정해주세요:

=== 페이지 정보 ===
URL: {url}
도메인: {domain_info.get('name', 'N/A')} (평균 SEO 점수: {domain_info.get('avg_seo_score', 'N/A')})
현재 제목: {title or '없음'}
현재 메타설명: {description or '없음'}
브랜드명: {brand_name or '없음'}
내용: {content_snippet[:300] if content_snippet else '정보 없음'}
{sc_text}

=== 실제 검색 유입 키워드 (성과순) ===
{queries_text or '정보 없음'}

=== 수정할 이슈 ===
{chr(10).join(issues_text)}

다음 JSON 형식으로 응답하세요:
{{
    "fixes": [
        {{
            "issue_type": "이슈타입",
            "suggested_value": "수정된 값",
            "explanation": "이 수정이 검색 성과를 개선하는 이유",
            "confidence": 0.0-1.0
        }}
    ],
    "overall_explanation": "전체 SEO 최적화 전략 (검색 데이터 기반)"
}}"""

        result = self.client.analyze_json(prompt, system=system)

        if not result.get('success'):
            return result

        data = result.get('parsed', {})
        fixes = data.get('fixes', [])

        # Map fixes back to original issues
        fix_results = []
        for issue in issues:
            issue_type = issue.get('issue_type', issue.get('type', ''))
            matching_fix = next(
                (f for f in fixes if f.get('issue_type') == issue_type),
                None
            )
            if matching_fix:
                fix_results.append({
                    'issue_id': issue.get('id'),
                    'issue_type': issue_type,
                    'success': True,
                    'suggested_value': matching_fix.get('suggested_value', ''),
                    'explanation': matching_fix.get('explanation', ''),
                    'confidence': matching_fix.get('confidence', 0.8),
                })
            else:
                fix_results.append({
                    'issue_id': issue.get('id'),
                    'issue_type': issue_type,
                    'success': False,
                    'error': 'No fix generated',
                })

        return {
            'success': True,
            'fixes': fix_results,
            'overall_explanation': data.get('overall_explanation', ''),
        }

    def apply_fix(
        self,
        issue_id: int,
        suggested_value: str,
        ai_explanation: str = None,
        ai_confidence: float = None,
        page_context: Dict = None,
        user=None,
    ) -> Dict:
        """
        Apply an AI-generated fix to an issue.

        This updates the issue status and records the fix history.
        """
        from seo_analyzer.models import SEOIssue, AIFixHistory

        try:
            issue = SEOIssue.objects.select_related('page').get(id=issue_id)

            # Mark previous fixes for same issue type as superseded
            AIFixHistory.objects.filter(
                page=issue.page,
                issue_type=issue.issue_type,
                fix_status__in=['applied', 'deployed']
            ).update(fix_status='superseded')

            # Record fix history
            context_snapshot = {}
            pre_fix_metrics = {}

            if page_context:
                # Store key context data for future reference
                db_metrics = page_context.get('db_metrics', {})
                search_console = db_metrics.get('search_console', {})
                context_snapshot = {
                    'url': page_context.get('url'),
                    'seo_score': db_metrics.get('seo_score'),
                    'keywords': db_metrics.get('keywords', [])[:5],
                    'search_console': search_console,
                    'existing_issues_count': len(page_context.get('existing_issues', [])),
                }
                pre_fix_metrics = {
                    'seo_score': db_metrics.get('seo_score'),
                    'impressions': search_console.get('impressions'),
                    'clicks': search_console.get('clicks'),
                    'ctr': search_console.get('ctr'),
                    'avg_position': search_console.get('avg_position'),
                }

            # Create fix history record
            fix_history = AIFixHistory.objects.create(
                page=issue.page,
                issue=issue,
                issue_type=issue.issue_type,
                original_value=issue.current_value,
                fixed_value=suggested_value,
                ai_explanation=ai_explanation or '',
                ai_confidence=ai_confidence or 0.0,
                ai_model=self.client.model,
                context_snapshot=context_snapshot,
                pre_fix_metrics=pre_fix_metrics,
                fix_status='applied',
            )

            # Update issue
            issue.status = 'auto_fixed'  # Change status to auto_fixed
            issue.suggested_value = suggested_value
            issue.ai_fix_generated = True
            issue.ai_fix_generated_at = timezone.now()
            if ai_confidence:
                issue.ai_fix_confidence = ai_confidence
            if ai_explanation:
                issue.ai_fix_explanation = ai_explanation
            issue.save(update_fields=[
                'status',
                'suggested_value',
                'ai_fix_generated',
                'ai_fix_generated_at',
                'ai_fix_confidence',
                'ai_fix_explanation',
            ])

            return {
                'success': True,
                'issue_id': issue_id,
                'fix_history_id': fix_history.id,
                'message': 'AI fix applied and recorded to history',
            }

        except SEOIssue.DoesNotExist:
            return {
                'success': False,
                'error': 'Issue not found',
            }
        except Exception as e:
            logger.error(f"Failed to apply AI fix: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }

    def check_recurrence(self, page, issue_type: str) -> bool:
        """
        Check if an issue has recurred after being fixed.
        If so, mark the previous fix as recurred.
        """
        from seo_analyzer.models import AIFixHistory

        # Get the most recent fix for this issue type on this page
        last_fix = AIFixHistory.objects.filter(
            page=page,
            issue_type=issue_type,
            fix_status__in=['deployed', 'verified'],
            issue_recurred=False
        ).order_by('-created_at').first()

        if last_fix:
            # Mark as recurred
            last_fix.mark_as_recurred()
            logger.info(
                f"Issue recurrence detected: {issue_type} on {page.url} "
                f"(fix #{last_fix.id}, recurrence count: {last_fix.recurrence_count})"
            )
            return True

        return False

    def get_fix_history_for_context(self, page, issue_type: str = None) -> List[Dict]:
        """
        Get relevant fix history for AI context.
        Returns formatted history for inclusion in AI prompts.
        """
        from seo_analyzer.models import AIFixHistory

        qs = AIFixHistory.objects.filter(page=page)
        if issue_type:
            qs = qs.filter(issue_type=issue_type)

        history = qs.order_by('-created_at')[:5]

        return [
            {
                'issue_type': h.issue_type,
                'original_value': h.original_value[:100] if h.original_value else None,
                'fixed_value': h.fixed_value[:100] if h.fixed_value else None,
                'ai_explanation': h.ai_explanation[:200] if h.ai_explanation else None,
                'ai_confidence': h.ai_confidence,
                'effectiveness': h.effectiveness,
                'issue_recurred': h.issue_recurred,
                'recurrence_count': h.recurrence_count,
                'fixed_at': h.created_at.isoformat(),
            }
            for h in history
        ]

    def apply_suggestion(self, suggestion, deploy_to_git: bool = False) -> Dict:
        """
        Apply an AI suggestion.

        Handles different suggestion types:
        - title: Updates Page.title + optional Git deploy
        - description: Updates Page.description + optional Git deploy
        - content: Provides guide (manual)
        - structure: Provides guide (manual)
        - priority_action/quick_win: Domain-level recommendations

        Args:
            suggestion: AISuggestion model instance
            deploy_to_git: If True, also deploy changes to Git repository

        Returns:
            {
                'success': True/False,
                'message': 'Result message',
                'applied_changes': [...],
                'manual_guide': 'For manual items',
                'git_result': {...} if deploy_to_git
            }
        """
        from seo_analyzer.models import Page, SitemapEntry, AIFixHistory

        suggestion_type = suggestion.suggestion_type
        action_data = suggestion.action_data or {}
        page = suggestion.page
        applied_changes = []

        try:
            # =========================================================
            # Title Optimization
            # =========================================================
            if suggestion_type == 'title' and page:
                new_title = action_data.get('new_title')
                if new_title:
                    old_title = page.title
                    page.title = new_title
                    page.save(update_fields=['title'])

                    # Record history
                    AIFixHistory.objects.create(
                        page=page,
                        issue_type='title_optimization',
                        original_value=old_title or '',
                        fixed_value=new_title,
                        ai_explanation=suggestion.description,
                        ai_confidence=0.85,
                        ai_model=self.client.model,
                        fix_status='applied',
                        context_snapshot={
                            'suggestion_id': suggestion.id,
                            'suggestion_type': suggestion_type,
                        }
                    )

                    applied_changes.append({
                        'field': 'title',
                        'old': old_title,
                        'new': new_title,
                        'page_url': page.url,
                    })

                    # Update suggestion status
                    suggestion.status = 'applied'
                    suggestion.applied_at = timezone.now()
                    suggestion.save(update_fields=['status', 'applied_at'])

                    result = {
                        'success': True,
                        'message': f'제목이 업데이트되었습니다.',
                        'applied_changes': applied_changes,
                    }

                    # Git 배포 (옵션)
                    if deploy_to_git and suggestion.domain.git_enabled:
                        git_result = self._deploy_to_git(suggestion.domain, applied_changes)
                        result['git_result'] = git_result
                        if git_result.get('success'):
                            result['message'] += ' Git 배포 완료.'
                            # Update fix history to deployed status
                            fix_record = AIFixHistory.objects.filter(
                                page=page,
                                issue_type='title_optimization',
                                fix_status='applied'
                            ).order_by('-created_at').first()
                            if fix_record:
                                fix_record.fix_status = 'deployed'
                                fix_record.deployed_at = timezone.now()
                                fix_record.save(update_fields=['fix_status', 'deployed_at'])

                    return result
                else:
                    return {
                        'success': False,
                        'error': 'action_data에 new_title이 없습니다.',
                        'manual_guide': action_data.get('manual_guide'),
                    }

            # =========================================================
            # Meta Description Optimization
            # =========================================================
            elif suggestion_type == 'description' and page:
                new_description = action_data.get('new_description')
                if new_description:
                    old_description = page.description
                    page.description = new_description
                    page.save(update_fields=['description'])

                    # Record history
                    AIFixHistory.objects.create(
                        page=page,
                        issue_type='description_optimization',
                        original_value=old_description or '',
                        fixed_value=new_description,
                        ai_explanation=suggestion.description,
                        ai_confidence=0.85,
                        ai_model=self.client.model,
                        fix_status='applied',
                        context_snapshot={
                            'suggestion_id': suggestion.id,
                            'suggestion_type': suggestion_type,
                        }
                    )

                    applied_changes.append({
                        'field': 'description',
                        'old': old_description[:100] if old_description else None,
                        'new': new_description,
                        'page_url': page.url,
                    })

                    # Update suggestion status
                    suggestion.status = 'applied'
                    suggestion.applied_at = timezone.now()
                    suggestion.save(update_fields=['status', 'applied_at'])

                    result = {
                        'success': True,
                        'message': f'메타 설명이 업데이트되었습니다.',
                        'applied_changes': applied_changes,
                    }

                    # Git 배포 (옵션)
                    if deploy_to_git and suggestion.domain.git_enabled:
                        git_result = self._deploy_to_git(suggestion.domain, applied_changes)
                        result['git_result'] = git_result
                        if git_result.get('success'):
                            result['message'] += ' Git 배포 완료.'
                            # Update fix history to deployed status
                            fix_record = AIFixHistory.objects.filter(
                                page=page,
                                issue_type='description_optimization',
                                fix_status='applied'
                            ).order_by('-created_at').first()
                            if fix_record:
                                fix_record.fix_status = 'deployed'
                                fix_record.deployed_at = timezone.now()
                                fix_record.save(update_fields=['fix_status', 'deployed_at'])

                    return result
                else:
                    return {
                        'success': False,
                        'error': 'action_data에 new_description이 없습니다.',
                        'manual_guide': action_data.get('manual_guide'),
                    }

            # =========================================================
            # Sitemap Entry Updates (priority, changefreq) + XML Regeneration
            # =========================================================
            elif suggestion_type == 'structure' and page:
                # Check if this is a sitemap-related suggestion
                new_priority = action_data.get('new_priority')
                new_changefreq = action_data.get('new_changefreq')

                if new_priority is not None or new_changefreq:
                    sitemap_entry = SitemapEntry.objects.filter(page=page).first()
                    if sitemap_entry:
                        changes = []
                        if new_priority is not None:
                            old_priority = sitemap_entry.priority
                            sitemap_entry.priority = new_priority
                            changes.append(f'priority: {old_priority} → {new_priority}')
                            applied_changes.append({
                                'field': 'sitemap_priority',
                                'old': float(old_priority) if old_priority else None,
                                'new': new_priority,
                            })

                        if new_changefreq:
                            old_changefreq = sitemap_entry.changefreq
                            sitemap_entry.changefreq = new_changefreq
                            changes.append(f'changefreq: {old_changefreq} → {new_changefreq}')
                            applied_changes.append({
                                'field': 'sitemap_changefreq',
                                'old': old_changefreq,
                                'new': new_changefreq,
                            })

                        sitemap_entry.save()

                        # Update suggestion status
                        suggestion.status = 'applied'
                        suggestion.applied_at = timezone.now()
                        suggestion.save(update_fields=['status', 'applied_at'])

                        result = {
                            'success': True,
                            'message': f'사이트맵 설정이 업데이트되었습니다: {", ".join(changes)}',
                            'applied_changes': applied_changes,
                        }

                        # Sitemap XML 재생성 및 Git 배포 (옵션)
                        if deploy_to_git and suggestion.domain.git_enabled:
                            sitemap_result = self._regenerate_and_deploy_sitemap(suggestion.domain)
                            result['sitemap_result'] = sitemap_result
                            if sitemap_result.get('success'):
                                result['message'] += ' sitemap.xml 배포 완료.'
                            else:
                                result['message'] += f' sitemap.xml 배포 실패: {sitemap_result.get("error")}'

                        return result

                # Fall through to manual guide
                return {
                    'success': False,
                    'error': '자동 적용 불가 - 수동 적용이 필요합니다.',
                    'manual_guide': action_data.get('manual_guide') or suggestion.description,
                }

            # =========================================================
            # Content Improvements - Manual only
            # =========================================================
            elif suggestion_type == 'content':
                return {
                    'success': False,
                    'error': '콘텐츠 수정은 자동 적용이 불가능합니다.',
                    'manual_guide': action_data.get('manual_guide') or suggestion.description,
                    'suggested_changes': action_data.get('changes', []),
                }

            # =========================================================
            # Keyword Optimization - AI가 콘텐츠에 키워드 자연스럽게 삽입
            # =========================================================
            elif suggestion_type == 'keyword':
                return self._apply_keyword_optimization(
                    suggestion, page, domain, action_data, deploy_to_git
                )

            # =========================================================
            # Internal Link - 관련 페이지 자동 연결
            # =========================================================
            elif suggestion_type == 'internal_link':
                return self._apply_internal_link(
                    suggestion, page, domain, action_data, deploy_to_git
                )

            # =========================================================
            # Quick Win - 구체적 코드 변경 자동 생성
            # =========================================================
            elif suggestion_type == 'quick_win':
                return self._apply_quick_win(
                    suggestion, page, domain, action_data, deploy_to_git
                )

            # =========================================================
            # Priority Action - 외부 API 자동 실행 (GSC 등)
            # =========================================================
            elif suggestion_type == 'priority_action':
                return self._apply_priority_action(
                    suggestion, page, domain, action_data, deploy_to_git
                )

            # =========================================================
            # Performance - Manual technical changes (일부 자동화)
            # =========================================================
            elif suggestion_type == 'performance':
                return self._apply_performance_optimization(
                    suggestion, page, domain, action_data, deploy_to_git
                )

            # =========================================================
            # General recommendations - 수동 적용
            # =========================================================
            elif suggestion_type == 'general':
                return {
                    'success': False,
                    'error': '일반 권장 사항은 수동 검토 후 적용하세요.',
                    'manual_guide': action_data.get('manual_guide') or suggestion.description,
                }

            # =========================================================
            # Bulk Fix Descriptions - 여러 페이지의 메타 설명 일괄 최적화
            # =========================================================
            elif suggestion_type == 'bulk_fix_descriptions':
                return self._apply_bulk_fix_descriptions(
                    suggestion, action_data, deploy_to_git
                )

            # =========================================================
            # Bulk Fix Titles - 여러 페이지의 제목 일괄 최적화
            # =========================================================
            elif suggestion_type == 'bulk_fix_titles':
                return self._apply_bulk_fix_titles(
                    suggestion, action_data, deploy_to_git
                )

            # =========================================================
            # Unknown type
            # =========================================================
            else:
                return {
                    'success': False,
                    'error': f'알 수 없는 제안 유형: {suggestion_type}',
                    'manual_guide': action_data.get('manual_guide') or suggestion.description,
                }

        except Exception as e:
            logger.error(f"Failed to apply suggestion {suggestion.id}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }

    def _deploy_to_git(self, domain, changes: List[Dict]) -> Dict:
        """
        Deploy changes to Git repository.

        Args:
            domain: Domain model instance
            changes: List of change dicts with field, old, new, page_url

        Returns:
            GitDeployer result dict
        """
        try:
            from .git_deployer.deployer import GitDeployer

            # Convert changes to fixes format expected by GitDeployer
            fixes = []
            for change in changes:
                fixes.append({
                    'page_url': change.get('page_url'),
                    'field': change.get('field'),
                    'old_value': change.get('old'),
                    'new_value': change.get('new'),
                })

            deployer = GitDeployer(domain)
            result = deployer.deploy_fixes(fixes)

            return result

        except Exception as e:
            logger.error(f"Git deployment failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }

    def _regenerate_and_deploy_sitemap(self, domain) -> Dict:
        """
        Regenerate sitemap.xml from DB entries and deploy to Git.

        Args:
            domain: Domain model instance

        Returns:
            {
                'success': True/False,
                'message': 'Result',
                'commit_hash': '...' if success
            }
        """
        try:
            from .sitemap_editor import SitemapEditorService
            from .git_deployer.deployer import GitDeployer

            # Step 1: Generate XML from current DB entries
            editor = SitemapEditorService()
            xml_result = editor.generate_preview_xml(domain)

            if xml_result.get('error'):
                return {
                    'success': False,
                    'error': f'XML 생성 실패: {xml_result.get("message")}',
                }

            xml_content = xml_result['xml_content']

            # Step 2: Deploy to Git
            deployer = GitDeployer(domain)
            deploy_result = deployer.deploy_sitemap(
                xml_content,
                commit_message='AI: Update sitemap.xml (priority/changefreq changes)'
            )

            if deploy_result.get('error'):
                return {
                    'success': False,
                    'error': deploy_result.get('message'),
                }

            return {
                'success': True,
                'message': 'sitemap.xml 재생성 및 배포 완료',
                'commit_hash': deploy_result.get('commit_hash'),
            }

        except Exception as e:
            logger.error(f"Sitemap regeneration failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }

    # =========================================================
    # Keyword Optimization - AI가 콘텐츠에 키워드 자연스럽게 삽입
    # =========================================================
    def _apply_keyword_optimization(
        self, suggestion, page, domain, action_data: Dict, deploy_to_git: bool
    ) -> Dict:
        """
        키워드 최적화 자동 적용

        AI가 기존 콘텐츠에 타겟 키워드를 자연스럽게 삽입한 새 버전을 생성하고
        DB 업데이트 및 Git 배포를 수행합니다.

        action_data 예시:
        {
            "keywords": ["암호화폐", "비트코인 분석"],
            "target_field": "description",  # title, description, content
            "current_text": "...",
            "density_target": 2.0
        }
        """
        from django.utils import timezone

        keywords = action_data.get('keywords', [])
        target_field = action_data.get('target_field', 'description')

        if not keywords:
            return {
                'success': False,
                'error': '키워드가 지정되지 않았습니다.',
            }

        # 현재 텍스트 가져오기
        current_text = ''
        if target_field == 'title':
            current_text = page.title or ''
        elif target_field == 'description':
            current_text = page.description or ''
        elif target_field == 'content':
            # 콘텐츠는 별도 처리 필요
            current_text = action_data.get('current_text', '')

        if not current_text:
            return {
                'success': False,
                'error': f'{target_field}에 최적화할 콘텐츠가 없습니다.',
            }

        try:
            # Claude AI로 키워드 최적화된 텍스트 생성
            optimized_text = self._generate_keyword_optimized_text(
                current_text, keywords, target_field
            )

            if not optimized_text:
                return {
                    'success': False,
                    'error': '키워드 최적화 텍스트 생성 실패',
                }

            # DB 업데이트
            old_value = current_text
            if target_field == 'title':
                page.title = optimized_text
                page.save(update_fields=['title', 'updated_at'])
            elif target_field == 'description':
                page.description = optimized_text
                page.save(update_fields=['description', 'updated_at'])

            # AIFixHistory 기록
            from seo_analyzer.models import AIFixHistory
            AIFixHistory.objects.create(
                page=page,
                issue_type=f'keyword_optimization_{target_field}',
                original_value=old_value,
                fixed_value=optimized_text,
                fix_status='applied',
                ai_explanation=f'키워드 최적화: {", ".join(keywords)}',
                ai_model='claude-sonnet-4-20250514',
                context_snapshot={
                    'keywords': keywords,
                    'target_field': target_field,
                    'suggestion_id': suggestion.id,
                },
            )

            # Suggestion 상태 업데이트
            suggestion.status = 'applied'
            suggestion.applied_at = timezone.now()
            suggestion.save(update_fields=['status', 'applied_at'])

            result = {
                'success': True,
                'message': f'{target_field} 키워드 최적화 완료',
                'applied_changes': [{
                    'field': target_field,
                    'old': old_value[:100] + '...' if len(old_value) > 100 else old_value,
                    'new': optimized_text[:100] + '...' if len(optimized_text) > 100 else optimized_text,
                    'page_url': page.url,
                    'keywords': keywords,
                }],
            }

            # Git 배포
            if deploy_to_git and domain.git_enabled:
                git_result = self._deploy_to_git(domain, [{
                    'field': target_field,
                    'old': old_value,
                    'new': optimized_text,
                    'page_url': page.url,
                }])
                result['git_result'] = git_result
                if git_result.get('success'):
                    result['message'] += ' Git 배포 완료.'

            return result

        except Exception as e:
            logger.error(f"Keyword optimization failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _generate_keyword_optimized_text(
        self, current_text: str, keywords: list, field_type: str
    ) -> str:
        """Claude AI를 사용해 키워드 최적화된 텍스트 생성"""
        try:
            from .claude_client import ClaudeClient

            client = ClaudeClient()

            # 필드 타입별 가이드라인
            guidelines = {
                'title': '60자 이내, 핵심 키워드를 앞쪽에 배치, 클릭을 유도하는 제목',
                'description': '155자 이내, 자연스러운 문장, 핵심 가치 전달',
                'content': '자연스러운 문맥 유지, 키워드 스터핑 금지, 가독성 우선',
            }

            prompt = f"""다음 텍스트에 아래 키워드를 자연스럽게 포함하여 SEO 최적화된 버전을 작성하세요.

## 현재 텍스트:
{current_text}

## 타겟 키워드:
{', '.join(keywords)}

## 가이드라인:
- 필드 타입: {field_type}
- {guidelines.get(field_type, '자연스러운 문맥 유지')}
- 키워드 스터핑 금지 - 부자연스러운 반복 NO
- 원본 의미 보존
- 가독성 유지

## 응답 형식:
최적화된 텍스트만 반환 (설명 없이)"""

            response = client.complete(prompt, max_tokens=1000)

            # 응답 정리
            optimized = response.strip()
            if optimized.startswith('"') and optimized.endswith('"'):
                optimized = optimized[1:-1]

            return optimized

        except Exception as e:
            logger.error(f"Failed to generate keyword optimized text: {e}")
            return None

    # =========================================================
    # Internal Link - 관련 페이지 자동 연결
    # =========================================================
    def _apply_internal_link(
        self, suggestion, page, domain, action_data: Dict, deploy_to_git: bool
    ) -> Dict:
        """
        내부 링크 자동 삽입

        AI가 현재 페이지 콘텐츠를 분석하고 관련 페이지로의 링크를 자동 삽입합니다.

        action_data 예시:
        {
            "suggested_links": [
                {"url": "/guide/basics", "anchor_text": "기본 가이드", "context": "초보자를 위한"},
                {"url": "/analysis/trends", "anchor_text": "트렌드 분석"}
            ],
            "target_field": "content"
        }
        """
        from django.utils import timezone
        from seo_analyzer.models import Page

        suggested_links = action_data.get('suggested_links', [])

        if not suggested_links:
            # AI가 자동으로 관련 페이지 찾기
            suggested_links = self._find_related_pages_for_linking(page, domain)

        if not suggested_links:
            return {
                'success': False,
                'error': '삽입할 내부 링크가 없습니다.',
            }

        try:
            # 페이지 콘텐츠 또는 description에 링크 삽입
            current_content = page.description or ''
            if not current_content:
                return {
                    'success': False,
                    'error': '링크를 삽입할 콘텐츠가 없습니다.',
                }

            # AI로 링크가 삽입된 콘텐츠 생성
            linked_content = self._generate_content_with_links(
                current_content, suggested_links, domain
            )

            if not linked_content or linked_content == current_content:
                return {
                    'success': False,
                    'error': '링크 삽입 텍스트 생성 실패',
                }

            # DB 업데이트
            old_value = current_content
            page.description = linked_content
            page.save(update_fields=['description', 'updated_at'])

            # AIFixHistory 기록
            from seo_analyzer.models import AIFixHistory
            AIFixHistory.objects.create(
                page=page,
                issue_type='internal_link_insertion',
                original_value=old_value,
                fixed_value=linked_content,
                fix_status='applied',
                ai_explanation=f'{len(suggested_links)}개 내부 링크 자동 삽입',
                ai_model='claude-sonnet-4-20250514',
                context_snapshot={
                    'links_added': [link.get('url') for link in suggested_links],
                    'suggestion_id': suggestion.id,
                },
            )

            # Suggestion 상태 업데이트
            suggestion.status = 'applied'
            suggestion.applied_at = timezone.now()
            suggestion.save(update_fields=['status', 'applied_at'])

            result = {
                'success': True,
                'message': f'{len(suggested_links)}개 내부 링크 삽입 완료',
                'applied_changes': [{
                    'field': 'description',
                    'old': old_value[:100] + '...' if len(old_value) > 100 else old_value,
                    'new': linked_content[:100] + '...' if len(linked_content) > 100 else linked_content,
                    'page_url': page.url,
                    'links_added': len(suggested_links),
                }],
            }

            # Git 배포
            if deploy_to_git and domain.git_enabled:
                git_result = self._deploy_to_git(domain, [{
                    'field': 'description',
                    'old': old_value,
                    'new': linked_content,
                    'page_url': page.url,
                }])
                result['git_result'] = git_result
                if git_result.get('success'):
                    result['message'] += ' Git 배포 완료.'

            return result

        except Exception as e:
            logger.error(f"Internal link insertion failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _find_related_pages_for_linking(self, page, domain) -> list:
        """도메인 내 관련 페이지 찾기"""
        from seo_analyzer.models import Page

        related = []
        all_pages = Page.objects.filter(domain=domain).exclude(id=page.id)[:20]

        # 간단한 관련성 검사 (제목/설명 기반)
        page_title = (page.title or '').lower()
        page_desc = (page.description or '').lower()

        for other in all_pages:
            other_title = (other.title or '').lower()
            # 공통 단어가 있으면 관련 페이지로 간주
            page_words = set(page_title.split() + page_desc.split())
            other_words = set(other_title.split())

            common = page_words & other_words
            if len(common) >= 2:  # 2개 이상 공통 단어
                related.append({
                    'url': other.url,
                    'anchor_text': other.title or other.path,
                    'relevance': len(common),
                })

        # 관련성 높은 순 정렬, 최대 3개
        related.sort(key=lambda x: x['relevance'], reverse=True)
        return related[:3]

    def _generate_content_with_links(
        self, content: str, links: list, domain
    ) -> str:
        """AI를 사용해 콘텐츠에 내부 링크 자연스럽게 삽입"""
        try:
            from .claude_client import ClaudeClient

            client = ClaudeClient()

            links_info = '\n'.join([
                f"- URL: {link['url']}, 앵커텍스트: {link['anchor_text']}"
                for link in links
            ])

            prompt = f"""다음 콘텐츠에 아래 내부 링크들을 자연스럽게 삽입하세요.

## 현재 콘텐츠:
{content}

## 삽입할 링크:
{links_info}

## 규칙:
1. 링크는 HTML <a href="URL">앵커텍스트</a> 형식으로 삽입
2. 문맥에 맞는 위치에 자연스럽게 삽입
3. 강제로 모든 링크를 넣지 않아도 됨 - 자연스러운 것만
4. 원본 의미와 가독성 유지

## 응답:
링크가 삽입된 콘텐츠만 반환 (설명 없이)"""

            response = client.complete(prompt, max_tokens=2000)
            return response.strip()

        except Exception as e:
            logger.error(f"Failed to generate content with links: {e}")
            return content  # 실패 시 원본 반환

    # =========================================================
    # Quick Win - 구체적 코드 변경 자동 생성
    # =========================================================
    def _apply_quick_win(
        self, suggestion, page, domain, action_data: Dict, deploy_to_git: bool
    ) -> Dict:
        """
        Quick Win 자동 적용

        Meta tag 추가, Open Graph 설정, Schema.org 등 빠른 개선 자동 적용

        action_data 예시:
        {
            "quick_win_type": "add_og_tags",  # add_meta, add_og_tags, add_schema, add_canonical
            "changes": [
                {"tag": "og:title", "value": "..."},
                {"tag": "og:description", "value": "..."}
            ]
        }
        """
        from django.utils import timezone

        quick_win_type = action_data.get('quick_win_type', action_data.get('category', ''))
        changes = action_data.get('changes', [])

        if not quick_win_type:
            # AI가 타입 결정
            quick_win_type = self._determine_quick_win_type(suggestion, action_data)

        try:
            result = None

            if quick_win_type in ['add_og_tags', 'og_tags', 'open_graph']:
                result = self._apply_og_tags(page, domain, action_data, deploy_to_git)

            elif quick_win_type in ['add_canonical', 'canonical']:
                result = self._apply_canonical(page, domain, action_data, deploy_to_git)

            elif quick_win_type in ['add_schema', 'schema', 'structured_data']:
                result = self._apply_schema(page, domain, action_data, deploy_to_git)

            elif quick_win_type in ['sitemap_submit', 'submit_sitemap']:
                result = self._submit_sitemap_to_gsc(domain)

            elif quick_win_type in ['request_indexing', 'indexing']:
                result = self._request_indexing_for_page(page, domain)

            else:
                # 일반 quick win - AI가 코드 변경 생성
                result = self._apply_generic_quick_win(
                    suggestion, page, domain, action_data, deploy_to_git
                )

            if result and result.get('success'):
                # Suggestion 상태 업데이트
                suggestion.status = 'applied'
                suggestion.applied_at = timezone.now()
                suggestion.save(update_fields=['status', 'applied_at'])

            return result or {
                'success': False,
                'error': f'지원하지 않는 quick_win 타입: {quick_win_type}',
            }

        except Exception as e:
            logger.error(f"Quick win failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _determine_quick_win_type(self, suggestion, action_data: Dict) -> str:
        """제안 내용에서 quick win 타입 추론"""
        desc = (suggestion.description or '').lower()
        title = (suggestion.title or '').lower()

        if 'og' in desc or 'open graph' in desc:
            return 'add_og_tags'
        if 'canonical' in desc:
            return 'add_canonical'
        if 'schema' in desc or 'structured' in desc:
            return 'add_schema'
        if 'sitemap' in desc and 'submit' in desc:
            return 'sitemap_submit'
        if 'index' in desc or '색인' in title:
            return 'request_indexing'

        return 'generic'

    def _apply_og_tags(self, page, domain, action_data: Dict, deploy_to_git: bool) -> Dict:
        """Open Graph 태그 적용 - Git 배포 필수"""
        # page가 None이면 사이트 전체 대상이므로 자동 적용 불가
        if not page:
            return {
                'success': False,
                'error': 'OG 태그 설정은 개별 페이지 단위로 적용해야 합니다.',
                'manual_guide': '각 페이지의 <head> 섹션에 og:title, og:description 등 OG 메타 태그를 추가하세요.',
            }

        og_tags = {
            'og:title': page.title,
            'og:description': page.description,
            'og:url': page.url,
            'og:type': 'website',
        }

        # Git 배포가 활성화되어 있어야 실제 적용 가능
        if not domain.git_enabled:
            return {
                'success': False,
                'error': 'Git 배포가 설정되지 않았습니다.',
                'manual_guide': f'수동으로 {page.url}의 <head>에 OG 메타 태그 추가',
                'og_tags': og_tags,
            }

        if deploy_to_git:
            changes = [{
                'field': 'og_tags',
                'old': '',
                'new': str(og_tags),
                'page_url': page.url,
            }]
            git_result = self._deploy_to_git(domain, changes)

            return {
                'success': git_result.get('success', False),
                'message': 'Open Graph 태그 배포' + (' 완료' if git_result.get('success') else ' 실패'),
                'og_tags': og_tags,
                'git_result': git_result,
            }

        return {
            'success': False,
            'error': 'Git 배포 옵션을 활성화해야 합니다.',
            'manual_guide': f'수동으로 {page.url}의 <head>에 OG 메타 태그 추가',
            'og_tags': og_tags,
        }

    def _apply_canonical(self, page, domain, action_data: Dict, deploy_to_git: bool) -> Dict:
        """Canonical URL 설정 - Git 배포 필수"""
        # page가 None이면 사이트 전체 대상이므로 자동 적용 불가
        if not page:
            return {
                'success': False,
                'error': 'Canonical URL 설정은 개별 페이지 단위로 적용해야 합니다.',
                'manual_guide': '각 페이지의 <head> 섹션에 <link rel="canonical" href="페이지URL"> 태그를 추가하세요.',
            }

        canonical_url = action_data.get('canonical_url', page.url)

        # Git 배포가 활성화되어 있어야 실제 적용 가능
        if not domain.git_enabled:
            return {
                'success': False,
                'error': 'Git 배포가 설정되지 않았습니다.',
                'manual_guide': f'수동으로 {page.url}의 <head>에 <link rel="canonical" href="{canonical_url}"> 추가',
                'canonical_url': canonical_url,
            }

        if deploy_to_git:
            changes = [{
                'field': 'canonical',
                'old': '',
                'new': canonical_url,
                'page_url': page.url,
            }]
            git_result = self._deploy_to_git(domain, changes)

            return {
                'success': git_result.get('success', False),
                'message': 'Canonical URL 설정' + (' 완료' if git_result.get('success') else ' 실패'),
                'canonical_url': canonical_url,
                'git_result': git_result,
            }

        return {
            'success': False,
            'error': 'Git 배포 옵션을 활성화해야 합니다.',
            'manual_guide': f'수동으로 {page.url}의 <head>에 <link rel="canonical" href="{canonical_url}"> 추가',
            'canonical_url': canonical_url,
        }

    def _apply_schema(self, page, domain, action_data: Dict, deploy_to_git: bool) -> Dict:
        """Schema.org 구조화 데이터 추가 - Git 배포 필수"""
        # page가 None이면 사이트 전체 대상이므로 자동 적용 불가
        if not page:
            return {
                'success': False,
                'error': 'Schema.org 데이터는 개별 페이지 단위로 적용해야 합니다.',
                'manual_guide': '각 페이지에 JSON-LD 형식의 구조화 데이터를 추가하세요.',
            }

        schema_type = action_data.get('schema_type', 'WebPage')

        schema_data = {
            "@context": "https://schema.org",
            "@type": schema_type,
            "name": page.title,
            "description": page.description,
            "url": page.url,
        }

        # Git 배포가 활성화되어 있어야 실제 적용 가능
        if not domain.git_enabled:
            import json
            return {
                'success': False,
                'error': 'Git 배포가 설정되지 않았습니다.',
                'manual_guide': f'수동으로 {page.url}에 Schema.org JSON-LD 추가',
                'schema': schema_data,
            }

        if deploy_to_git:
            import json
            changes = [{
                'field': 'schema',
                'old': '',
                'new': json.dumps(schema_data, ensure_ascii=False),
                'page_url': page.url,
            }]
            git_result = self._deploy_to_git(domain, changes)

            return {
                'success': git_result.get('success', False),
                'message': 'Schema.org 데이터 배포' + (' 완료' if git_result.get('success') else ' 실패'),
                'schema': schema_data,
                'git_result': git_result,
            }

        return {
            'success': False,
            'error': 'Git 배포 옵션을 활성화해야 합니다.',
            'manual_guide': f'수동으로 {page.url}에 Schema.org JSON-LD 추가',
            'schema': schema_data,
        }

    def _apply_generic_quick_win(
        self, suggestion, page, domain, action_data: Dict, deploy_to_git: bool
    ) -> Dict:
        """일반 Quick Win - AI가 코드 변경 생성"""
        # AI를 사용해 제안에 맞는 코드 변경 생성
        return {
            'success': True,
            'message': 'Quick Win 권장사항이 기록되었습니다.',
            'manual_guide': action_data.get('manual_guide') or suggestion.description,
            'note': '이 Quick Win은 수동 검토 후 적용하세요.',
        }

    # =========================================================
    # Priority Action - 외부 API 자동 실행
    # =========================================================
    def _apply_priority_action(
        self, suggestion, page, domain, action_data: Dict, deploy_to_git: bool
    ) -> Dict:
        """
        Priority Action 자동 실행

        Google Search Console API 등 외부 서비스 연동 자동 실행

        action_data 예시:
        {
            "action_type": "gsc_submit_sitemap",  # gsc_*, analytics_*
            "category": "기술적 SEO"
        }
        """
        from django.utils import timezone

        action_type = action_data.get('action_type', '')
        category = action_data.get('category', '')

        # 카테고리/설명에서 액션 타입 추론
        if not action_type:
            action_type = self._determine_priority_action_type(suggestion, action_data)

        try:
            result = None

            # Google Search Console 관련 액션
            if action_type in ['gsc_submit_sitemap', 'submit_sitemap', 'sitemap']:
                result = self._submit_sitemap_to_gsc(domain)

            elif action_type in ['gsc_request_indexing', 'request_indexing', 'indexing']:
                if page:
                    result = self._request_indexing_for_page(page, domain)
                else:
                    result = self._request_indexing_for_domain(domain)

            elif action_type in ['gsc_verify', 'verify_site']:
                result = self._verify_gsc_connection(domain)

            elif action_type in ['gsc_fetch_data', 'fetch_analytics']:
                result = self._fetch_gsc_data(domain)

            # 기타 자동화 가능한 액션
            elif action_type in ['regenerate_sitemap']:
                result = self._regenerate_and_deploy_sitemap(domain)

            else:
                # 자동화 불가능한 액션은 가이드 제공
                return {
                    'success': True,
                    'message': 'Priority Action이 기록되었습니다.',
                    'manual_guide': action_data.get('manual_guide') or action_data.get('description') or suggestion.description,
                    'category': category,
                    'note': '이 액션은 수동 실행이 필요합니다.',
                }

            if result and result.get('success'):
                # Suggestion 상태 업데이트
                suggestion.status = 'applied'
                suggestion.applied_at = timezone.now()
                suggestion.save(update_fields=['status', 'applied_at'])

            return result or {
                'success': False,
                'error': f'Priority Action 실행 실패: {action_type}',
            }

        except Exception as e:
            logger.error(f"Priority action failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _determine_priority_action_type(self, suggestion, action_data: Dict) -> str:
        """제안 내용에서 priority action 타입 추론"""
        desc = (suggestion.description or '').lower()
        title = (suggestion.title or '').lower()
        category = (action_data.get('category', '') or '').lower()

        if 'sitemap' in desc and ('submit' in desc or '제출' in title):
            return 'gsc_submit_sitemap'
        if 'index' in desc or '색인' in title:
            return 'gsc_request_indexing'
        if 'search console' in desc and ('연동' in title or 'connect' in desc):
            return 'gsc_verify'
        if 'sitemap' in desc and ('regenerate' in desc or '재생성' in title):
            return 'regenerate_sitemap'

        return 'manual'

    def _submit_sitemap_to_gsc(self, domain) -> Dict:
        """Google Search Console에 Sitemap 제출"""
        try:
            from .google_search_console import get_gsc_service

            service = get_gsc_service(domain)
            site_url = f"{domain.protocol}://{domain.domain_name}/"
            sitemap_url = f"{site_url}sitemap.xml"

            result = service.submit_sitemap(site_url, sitemap_url)

            return {
                'success': result.get('success', False),
                'message': result.get('message', 'Sitemap 제출 ' + ('완료' if result.get('success') else '실패')),
                'sitemap_url': sitemap_url,
                'gsc_result': result,
            }

        except Exception as e:
            logger.error(f"Sitemap submission to GSC failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Google Search Console API가 설정되지 않았거나 오류가 발생했습니다.',
            }

    def _request_indexing_for_page(self, page, domain) -> Dict:
        """단일 페이지 색인 요청"""
        try:
            from .google_search_console import get_gsc_service

            service = get_gsc_service(domain)
            result = service.request_indexing(page.url)

            return {
                'success': result.get('success', False),
                'message': f'{page.url} 색인 요청 ' + ('완료' if result.get('success') else '실패'),
                'page_url': page.url,
                'gsc_result': result,
            }

        except Exception as e:
            logger.error(f"Indexing request failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Google Indexing API가 설정되지 않았거나 오류가 발생했습니다.',
            }

    def _request_indexing_for_domain(self, domain) -> Dict:
        """도메인 전체 페이지 색인 요청"""
        try:
            from .google_search_console import get_gsc_service
            from seo_analyzer.models import Page

            service = get_gsc_service(domain)
            pages = Page.objects.filter(domain=domain)[:50]  # 최대 50개
            urls = [p.url for p in pages]

            result = service.batch_request_indexing(urls)

            return {
                'success': result.get('success', False),
                'message': f'{result.get("success_count", 0)}개 페이지 색인 요청 완료',
                'total_pages': len(urls),
                'gsc_result': result,
            }

        except Exception as e:
            logger.error(f"Batch indexing request failed: {e}")
            return {'success': False, 'error': str(e)}

    def _verify_gsc_connection(self, domain) -> Dict:
        """Google Search Console 연결 확인"""
        try:
            from .google_search_console import get_gsc_service

            service = get_gsc_service(domain)
            site_url = f"{domain.protocol}://{domain.domain_name}/"

            result = service.get_site_info(site_url)

            if result.get('success'):
                return {
                    'success': True,
                    'message': 'Google Search Console 연결 확인됨',
                    'site_url': result.get('site_url'),
                    'permission_level': result.get('permission_level'),
                }
            else:
                return {
                    'success': False,
                    'message': 'Google Search Console 연결 실패',
                    'error': result.get('error'),
                    'manual_guide': '1. Google Search Console에서 사이트 소유권 확인\n2. 서비스 계정에 권한 부여',
                }

        except Exception as e:
            logger.error(f"GSC verification failed: {e}")
            return {'success': False, 'error': str(e)}

    def _fetch_gsc_data(self, domain) -> Dict:
        """Google Search Console 데이터 가져오기"""
        try:
            from .google_search_console import get_gsc_service

            service = get_gsc_service(domain)
            site_url = f"{domain.protocol}://{domain.domain_name}/"

            # 최근 28일 데이터
            analytics = service.get_search_analytics(site_url)

            if analytics.get('success'):
                return {
                    'success': True,
                    'message': f'{analytics.get("row_count", 0)}개 검색 데이터 수집 완료',
                    'data_summary': {
                        'rows': analytics.get('row_count'),
                        'start_date': analytics.get('start_date'),
                        'end_date': analytics.get('end_date'),
                    },
                }
            else:
                return {
                    'success': False,
                    'error': analytics.get('error'),
                }

        except Exception as e:
            logger.error(f"GSC data fetch failed: {e}")
            return {'success': False, 'error': str(e)}

    # =========================================================
    # Performance Optimization - 성능 최적화
    # =========================================================
    def _apply_performance_optimization(
        self, suggestion, page, domain, action_data: Dict, deploy_to_git: bool
    ) -> Dict:
        """
        성능 최적화 제안 적용

        일부 성능 최적화는 자동 적용 가능
        """
        perf_type = action_data.get('performance_type', '')
        technical_changes = action_data.get('technical_changes', [])

        # 자동화 가능한 성능 최적화
        if perf_type in ['lazy_loading', 'image_optimization']:
            return {
                'success': True,
                'message': '성능 최적화 권장사항이 기록되었습니다.',
                'manual_guide': suggestion.description,
                'technical_changes': technical_changes,
            }

        # 대부분의 성능 최적화는 수동 필요
        return {
            'success': True,
            'message': '성능 최적화는 기술적 검토가 필요합니다.',
            'manual_guide': action_data.get('manual_guide') or suggestion.description,
            'technical_changes': technical_changes,
        }

    # =========================================================
    # Bulk Fix Descriptions - 여러 페이지 메타 설명 일괄 수정
    # =========================================================
    def _apply_bulk_fix_descriptions(
        self, suggestion, action_data: Dict, deploy_to_git: bool
    ) -> Dict:
        """
        여러 페이지의 메타 설명을 AI로 생성하여 일괄 업데이트

        action_data 예시:
        {
            "affected_pages": [
                {"page_id": 1, "url": "...", "title": "...", "current_value": "..."},
                ...
            ]
        }
        """
        from seo_analyzer.models import Page, AIFixHistory
        from django.utils import timezone

        affected_pages = action_data.get('affected_pages', [])
        if not affected_pages:
            return {
                'success': False,
                'error': 'affected_pages가 비어있습니다.',
            }

        domain = suggestion.domain
        applied_changes = []
        failed_pages = []

        for page_info in affected_pages:
            page_id = page_info.get('page_id')
            if not page_id:
                continue

            try:
                page = Page.objects.get(id=page_id, domain=domain)
                old_description = page.description or ''

                # AI로 새 메타 설명 생성
                new_description = self._generate_meta_description(page)
                if not new_description:
                    failed_pages.append({
                        'url': page.url,
                        'error': 'AI 설명 생성 실패'
                    })
                    continue

                # DB 업데이트
                page.description = new_description
                page.save(update_fields=['description'])

                # AIFixHistory 기록
                AIFixHistory.objects.create(
                    page=page,
                    issue_type='description_optimization',
                    original_value=old_description,
                    fixed_value=new_description,
                    ai_explanation=f'Bulk fix: {suggestion.title}',
                    ai_confidence=0.80,
                    ai_model=self.client.model,
                    fix_status='applied',
                    context_snapshot={
                        'suggestion_id': suggestion.id,
                        'suggestion_type': 'bulk_fix_descriptions',
                        'bulk_fix': True,
                    }
                )

                applied_changes.append({
                    'field': 'description',
                    'old': old_description[:100] if old_description else None,
                    'new': new_description,
                    'page_url': page.url,
                    'page_id': page_id,
                })

            except Page.DoesNotExist:
                failed_pages.append({
                    'page_id': page_id,
                    'error': '페이지를 찾을 수 없음'
                })
            except Exception as e:
                logger.error(f"Bulk fix description error for page {page_id}: {e}")
                failed_pages.append({
                    'page_id': page_id,
                    'url': page_info.get('url'),
                    'error': str(e)
                })

        if not applied_changes:
            return {
                'success': False,
                'error': '적용된 변경사항이 없습니다.',
                'failed_pages': failed_pages,
            }

        # 제안 상태 업데이트
        suggestion.status = 'applied'
        suggestion.applied_at = timezone.now()
        suggestion.save(update_fields=['status', 'applied_at'])

        result = {
            'success': True,
            'message': f'{len(applied_changes)}개 페이지의 메타 설명이 업데이트되었습니다.',
            'applied_changes': applied_changes,
            'failed_pages': failed_pages if failed_pages else None,
        }

        # Git 배포 (옵션)
        if deploy_to_git and domain.git_enabled:
            git_result = self._deploy_to_git(domain, applied_changes)
            result['git_result'] = git_result
            if git_result.get('success'):
                result['message'] += ' Git 배포 완료.'
                # 배포 상태 업데이트
                for change in applied_changes:
                    fix_record = AIFixHistory.objects.filter(
                        page_id=change['page_id'],
                        issue_type='description_optimization',
                        fix_status='applied'
                    ).order_by('-created_at').first()
                    if fix_record:
                        fix_record.fix_status = 'deployed'
                        fix_record.deployed_at = timezone.now()
                        fix_record.save(update_fields=['fix_status', 'deployed_at'])

        return result

    def _generate_meta_description(self, page) -> str:
        """
        AI를 사용하여 페이지의 메타 설명 생성

        Args:
            page: Page 모델 인스턴스

        Returns:
            생성된 메타 설명 (80-160자)
        """
        try:
            prompt = f"""다음 웹페이지의 SEO 최적화된 메타 설명을 작성해주세요.

페이지 정보:
- URL: {page.url}
- 제목: {page.title or '(없음)'}
- 현재 설명: {page.description or '(없음)'}

요구사항:
1. 80-160자 사이로 작성
2. 페이지의 핵심 내용을 정확히 요약
3. 클릭을 유도하는 매력적인 문구 사용
4. 주요 키워드를 자연스럽게 포함
5. 한국어로 작성

메타 설명만 출력하세요 (따옴표나 설명 없이):"""

            response = self.client.generate(prompt)
            if response and isinstance(response, str):
                # 따옴표 제거 및 정리
                description = response.strip().strip('"\'')
                # 길이 제한
                if len(description) > 160:
                    description = description[:157] + '...'
                return description
            return None
        except Exception as e:
            logger.error(f"Meta description generation failed for {page.url}: {e}")
            return None

    # =========================================================
    # Bulk Fix Titles - 여러 페이지 제목 일괄 수정
    # =========================================================
    def _apply_bulk_fix_titles(
        self, suggestion, action_data: Dict, deploy_to_git: bool
    ) -> Dict:
        """
        여러 페이지의 제목을 AI로 최적화하여 일괄 업데이트

        action_data 예시:
        {
            "affected_pages": [
                {"page_id": 1, "url": "...", "title": "...", "current_value": "..."},
                ...
            ]
        }
        """
        from seo_analyzer.models import Page, AIFixHistory
        from django.utils import timezone

        affected_pages = action_data.get('affected_pages', [])
        if not affected_pages:
            return {
                'success': False,
                'error': 'affected_pages가 비어있습니다.',
            }

        domain = suggestion.domain
        applied_changes = []
        failed_pages = []

        for page_info in affected_pages:
            page_id = page_info.get('page_id')
            if not page_id:
                continue

            try:
                page = Page.objects.get(id=page_id, domain=domain)
                old_title = page.title or ''

                # AI로 새 제목 생성
                new_title = self._generate_optimized_title(page)
                if not new_title:
                    failed_pages.append({
                        'url': page.url,
                        'error': 'AI 제목 생성 실패'
                    })
                    continue

                # DB 업데이트
                page.title = new_title
                page.save(update_fields=['title'])

                # AIFixHistory 기록
                AIFixHistory.objects.create(
                    page=page,
                    issue_type='title_optimization',
                    original_value=old_title,
                    fixed_value=new_title,
                    ai_explanation=f'Bulk fix: {suggestion.title}',
                    ai_confidence=0.80,
                    ai_model=self.client.model,
                    fix_status='applied',
                    context_snapshot={
                        'suggestion_id': suggestion.id,
                        'suggestion_type': 'bulk_fix_titles',
                        'bulk_fix': True,
                    }
                )

                applied_changes.append({
                    'field': 'title',
                    'old': old_title[:100] if old_title else None,
                    'new': new_title,
                    'page_url': page.url,
                    'page_id': page_id,
                })

            except Page.DoesNotExist:
                failed_pages.append({
                    'page_id': page_id,
                    'error': '페이지를 찾을 수 없음'
                })
            except Exception as e:
                logger.error(f"Bulk fix title error for page {page_id}: {e}")
                failed_pages.append({
                    'page_id': page_id,
                    'url': page_info.get('url'),
                    'error': str(e)
                })

        if not applied_changes:
            return {
                'success': False,
                'error': '적용된 변경사항이 없습니다.',
                'failed_pages': failed_pages,
            }

        # 제안 상태 업데이트
        suggestion.status = 'applied'
        suggestion.applied_at = timezone.now()
        suggestion.save(update_fields=['status', 'applied_at'])

        result = {
            'success': True,
            'message': f'{len(applied_changes)}개 페이지의 제목이 업데이트되었습니다.',
            'applied_changes': applied_changes,
            'failed_pages': failed_pages if failed_pages else None,
        }

        # Git 배포 (옵션)
        if deploy_to_git and domain.git_enabled:
            git_result = self._deploy_to_git(domain, applied_changes)
            result['git_result'] = git_result
            if git_result.get('success'):
                result['message'] += ' Git 배포 완료.'
                # 배포 상태 업데이트
                for change in applied_changes:
                    fix_record = AIFixHistory.objects.filter(
                        page_id=change['page_id'],
                        issue_type='title_optimization',
                        fix_status='applied'
                    ).order_by('-created_at').first()
                    if fix_record:
                        fix_record.fix_status = 'deployed'
                        fix_record.deployed_at = timezone.now()
                        fix_record.save(update_fields=['fix_status', 'deployed_at'])

        return result

    def _generate_optimized_title(self, page) -> str:
        """
        AI를 사용하여 페이지의 SEO 최적화된 제목 생성

        Args:
            page: Page 모델 인스턴스

        Returns:
            생성된 제목 (30-60자)
        """
        try:
            prompt = f"""다음 웹페이지의 SEO 최적화된 제목을 작성해주세요.

페이지 정보:
- URL: {page.url}
- 현재 제목: {page.title or '(없음)'}
- 메타 설명: {page.description or '(없음)'}

요구사항:
1. 30-60자 사이로 작성
2. 페이지의 핵심 내용을 명확히 전달
3. 주요 키워드를 앞쪽에 배치
4. 클릭을 유도하는 매력적인 문구 사용
5. 브랜드명이 있다면 끝에 " | 브랜드명" 형식으로 포함
6. 한국어로 작성

제목만 출력하세요 (따옴표나 설명 없이):"""

            response = self.client.generate(prompt)
            if response and isinstance(response, str):
                # 따옴표 제거 및 정리
                title = response.strip().strip('"\'')
                # 길이 제한
                if len(title) > 70:
                    title = title[:67] + '...'
                return title
            return None
        except Exception as e:
            logger.error(f"Title generation failed for {page.url}: {e}")
            return None
