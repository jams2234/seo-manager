"""
AI Base Utilities

Common utilities for AI services:
- Page content fetching (Playwright/requests)
- SEO element extraction
- Page context building
"""
import logging
import requests
from typing import Dict, List, Optional
from urllib.parse import urlparse

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


class AIBaseService:
    """Base class for AI services with common utilities."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    # =========================================================================
    # Web Page Fetching
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
            }
        except Exception as e:
            logger.error(f"Request fetch failed for {url}: {e}")
            return {'success': False, 'error': str(e)}

    def _fetch_with_playwright(self, url: str) -> Dict:
        """Fetch page with Playwright for JS-rendered content."""
        if not PLAYWRIGHT_AVAILABLE:
            return self._fetch_with_requests(url)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until='networkidle', timeout=30000)
                html = page.content()
                browser.close()

            seo_elements = self._extract_seo_elements(html)
            text_content = self._extract_text_content(html)

            return {
                'success': True,
                'html': html,
                'text_content': text_content,
                'seo_elements': seo_elements,
                'js_rendered': True,
            }
        except Exception as e:
            logger.error(f"Playwright fetch failed for {url}: {e}")
            return self._fetch_with_requests(url)  # Fallback

    # =========================================================================
    # SEO Element Extraction
    # =========================================================================

    def _extract_seo_elements(self, html: str) -> Dict:
        """Extract key SEO elements from HTML."""
        if not BS4_AVAILABLE:
            return {}

        try:
            soup = BeautifulSoup(html, 'html.parser')
            elements = {}

            # Title
            title_tag = soup.find('title')
            elements['title'] = title_tag.get_text(strip=True) if title_tag else None

            # Meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            elements['meta_description'] = meta_desc.get('content', '').strip() if meta_desc else None

            # H1 tags
            h1_tags = soup.find_all('h1')
            elements['h1_tags'] = [h1.get_text(strip=True) for h1 in h1_tags]

            # H2 tags
            h2_tags = soup.find_all('h2')
            elements['h2_tags'] = [h2.get_text(strip=True) for h2 in h2_tags[:10]]

            # Canonical URL
            canonical = soup.find('link', rel='canonical')
            elements['canonical_url'] = canonical.get('href') if canonical else None

            # OG tags
            og_title = soup.find('meta', property='og:title')
            og_desc = soup.find('meta', property='og:description')
            elements['og_title'] = og_title.get('content') if og_title else None
            elements['og_description'] = og_desc.get('content') if og_desc else None

            # Images without alt
            images = soup.find_all('img')
            elements['total_images'] = len(images)
            elements['images_without_alt'] = len([
                img for img in images
                if not img.get('alt') or img.get('alt').strip() == ''
            ])

            # Internal/External links
            links = soup.find_all('a', href=True)
            internal_links = []
            external_links = []
            for link in links:
                href = link.get('href', '')
                if href.startswith('/') or href.startswith('#'):
                    internal_links.append(href)
                elif href.startswith('http'):
                    external_links.append(href)
            elements['internal_links_count'] = len(internal_links)
            elements['external_links_count'] = len(external_links)

            # Word count
            body = soup.find('body')
            if body:
                text = body.get_text(separator=' ', strip=True)
                elements['word_count'] = len(text.split())
            else:
                elements['word_count'] = 0

            return elements

        except Exception as e:
            logger.error(f"Failed to extract SEO elements: {e}")
            return {}

    def _extract_text_content(self, html: str) -> str:
        """Extract main text content from HTML."""
        if not BS4_AVAILABLE:
            return ""

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()

            # Get text
            text = soup.get_text(separator='\n', strip=True)

            # Limit to ~5000 chars for AI context
            return text[:5000] if len(text) > 5000 else text

        except Exception as e:
            logger.error(f"Failed to extract text content: {e}")
            return ""

    # =========================================================================
    # Page Context Building
    # =========================================================================

    def build_page_context(self, page, fetch_live: bool = True) -> Dict:
        """
        Build comprehensive page context for AI analysis.

        Args:
            page: Page model instance
            fetch_live: Whether to fetch live page content

        Returns:
            Comprehensive context dictionary
        """
        context = {
            'page_info': {
                'url': page.url,
                'path': page.path,
                'title': page.title,
                'description': page.description,
                'depth_level': page.depth_level,
            },
            'domain_info': {
                'name': page.domain.domain_name,
                'avg_seo_score': page.domain.avg_seo_score,
            },
            'tree_info': {
                'parent_url': page.parent_page.url if page.parent_page else None,
                'children_count': page.children.count() if hasattr(page, 'children') else 0,
                'depth_level': page.depth_level,
            },
        }

        # Add latest SEO metrics
        latest_metrics = page.seo_metrics.first()
        if latest_metrics:
            context['seo_metrics'] = {
                'seo_score': latest_metrics.seo_score,
                'performance_score': latest_metrics.performance_score,
                'is_indexed': latest_metrics.is_indexed,
                'top_queries': latest_metrics.top_queries[:5] if latest_metrics.top_queries else [],
            }

        # Add open issues
        open_issues = page.seo_issues.filter(status='open')[:10]
        context['open_issues'] = [
            {
                'type': issue.issue_type,
                'title': issue.title,
                'severity': issue.severity,
            }
            for issue in open_issues
        ]

        # Fetch live content if requested
        if fetch_live:
            live_content = self.fetch_page_content(page.url)
            if live_content.get('success'):
                context['live_content'] = {
                    'seo_elements': live_content.get('seo_elements', {}),
                    'text_preview': live_content.get('text_content', '')[:2000],
                }

        return context


# Singleton instance for common utilities
_base_service_instance = None


def get_base_service() -> AIBaseService:
    """Get singleton instance of AIBaseService."""
    global _base_service_instance
    if _base_service_instance is None:
        _base_service_instance = AIBaseService()
    return _base_service_instance
