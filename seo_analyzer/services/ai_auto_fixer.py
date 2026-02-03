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
        from ..models import SEOMetrics, SEOIssue, SitemapEntry

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
        from ..models import AIFixHistory

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
        from ..models import SEOIssue, AIFixHistory

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
        from ..models import AIFixHistory

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
        from ..models import AIFixHistory

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
