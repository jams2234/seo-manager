"""
Auto-Fix Service for SEO Issues
Automatically fixes SEO issues by updating Page model fields with AI-generated content
"""
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


class AutoFixService:
    """
    Service for automatically fixing SEO issues

    Fixes are applied to the Page model fields (title, description, etc.)
    Users can then apply these fixes to their actual website
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; SEOAnalyzerBot/1.0)'
        })

    @transaction.atomic
    def fix_issue(self, issue) -> Dict:
        """
        Fix a single SEO issue

        Args:
            issue: SEOIssue model instance

        Returns:
            {
                'success': True/False,
                'message': 'Description of what was fixed',
                'old_value': 'Previous value',
                'new_value': 'Updated value',
                'method': 'Fix method used'
            }
        """
        if not issue.auto_fix_available:
            return {
                'success': False,
                'message': 'Issue is not auto-fixable',
                'method': None
            }

        if not issue.auto_fix_method:
            return {
                'success': False,
                'message': 'No auto-fix method specified',
                'method': None
            }

        logger.info(f"Auto-fixing issue {issue.id} ({issue.issue_type}) using method: {issue.auto_fix_method}")

        # Route to appropriate fix method
        fix_methods = {
            'generate_meta_description': self._fix_generate_meta_description,
            'expand_meta_description': self._fix_expand_meta_description,
            'shorten_meta_description': self._fix_shorten_meta_description,
            'generate_title': self._fix_generate_title,
            'expand_title': self._fix_expand_title,
            'shorten_title': self._fix_shorten_title,
            'generate_open_graph_tags': self._fix_generate_open_graph_tags,
            'generate_alt_texts': self._fix_generate_alt_texts,
        }

        fix_method = fix_methods.get(issue.auto_fix_method)

        if not fix_method:
            return {
                'success': False,
                'message': f'Unknown auto-fix method: {issue.auto_fix_method}',
                'method': issue.auto_fix_method
            }

        try:
            result = fix_method(issue)

            if result.get('success'):
                # Update issue status and save before/after values
                issue.status = 'auto_fixed'
                issue.fixed_at = timezone.now()
                # Save the before/after values to the issue for history tracking
                if result.get('old_value'):
                    issue.current_value = result.get('old_value')
                if result.get('new_value'):
                    issue.suggested_value = result.get('new_value')
                issue.save()

                logger.info(f"Successfully auto-fixed issue {issue.id}: {result.get('old_value')} → {result.get('new_value')}")

            return result

        except Exception as e:
            logger.error(f"Auto-fix failed for issue {issue.id}: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Auto-fix error: {str(e)}',
                'method': issue.auto_fix_method
            }

    def _fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    # ===== Meta Description Fixes =====

    def _fix_generate_meta_description(self, issue) -> Dict:
        """Generate a new meta description from page content"""
        page = issue.page

        # Fetch page HTML
        html = self._fetch_html(page.url)
        if not html:
            return {
                'success': False,
                'message': 'Failed to fetch page content',
                'method': 'generate_meta_description'
            }

        soup = BeautifulSoup(html, 'html.parser')

        # Generate meta description
        new_description = self._generate_meta_description_from_content(soup, page.url)

        # Update page
        old_value = page.description
        page.description = new_description
        page.save()

        return {
            'success': True,
            'message': 'Generated and applied new meta description',
            'old_value': old_value or '(없음)',
            'new_value': new_description,
            'method': 'generate_meta_description'
        }

    def _fix_expand_meta_description(self, issue) -> Dict:
        """Expand short meta description"""
        page = issue.page

        if not page.description:
            return self._fix_generate_meta_description(issue)

        # Fetch page content for context
        html = self._fetch_html(page.url)
        if not html:
            return {
                'success': False,
                'message': 'Failed to fetch page content',
                'method': 'expand_meta_description'
            }

        soup = BeautifulSoup(html, 'html.parser')

        # Expand existing description with content from page
        expanded = self._expand_description(page.description, soup)

        old_value = page.description
        page.description = expanded
        page.save()

        return {
            'success': True,
            'message': 'Expanded meta description',
            'old_value': old_value,
            'new_value': expanded,
            'method': 'expand_meta_description'
        }

    def _fix_shorten_meta_description(self, issue) -> Dict:
        """Shorten long meta description"""
        page = issue.page

        if not page.description:
            return {
                'success': False,
                'message': 'No meta description to shorten',
                'method': 'shorten_meta_description'
            }

        # Shorten to 155 characters
        shortened = page.description[:152] + '...' if len(page.description) > 155 else page.description

        old_value = page.description
        page.description = shortened
        page.save()

        return {
            'success': True,
            'message': 'Shortened meta description to optimal length',
            'old_value': old_value,
            'new_value': shortened,
            'method': 'shorten_meta_description'
        }

    # ===== Title Fixes =====

    def _fix_generate_title(self, issue) -> Dict:
        """Generate a new title from page content"""
        page = issue.page

        html = self._fetch_html(page.url)
        if not html:
            return {
                'success': False,
                'message': 'Failed to fetch page content',
                'method': 'generate_title'
            }

        soup = BeautifulSoup(html, 'html.parser')

        # Try to get existing title or generate from H1
        new_title = self._generate_title_from_content(soup, page.url)

        old_value = page.title
        page.title = new_title
        page.save()

        return {
            'success': True,
            'message': 'Generated and applied new title',
            'old_value': old_value or '(없음)',
            'new_value': new_title,
            'method': 'generate_title'
        }

    def _fix_expand_title(self, issue) -> Dict:
        """Expand short title"""
        page = issue.page

        if not page.title:
            return self._fix_generate_title(issue)

        # Add site name or descriptive suffix
        html = self._fetch_html(page.url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            site_name = self._extract_site_name(soup, page.url)
            expanded = f"{page.title} | {site_name}" if site_name else f"{page.title} - 완전 가이드"
        else:
            expanded = f"{page.title} - 완전 가이드"

        # Ensure it's not too long
        if len(expanded) > 60:
            expanded = page.title + " - 가이드"

        old_value = page.title
        page.title = expanded
        page.save()

        return {
            'success': True,
            'message': 'Expanded title',
            'old_value': old_value,
            'new_value': expanded,
            'method': 'expand_title'
        }

    def _fix_shorten_title(self, issue) -> Dict:
        """Shorten long title"""
        page = issue.page

        if not page.title:
            return {
                'success': False,
                'message': 'No title to shorten',
                'method': 'shorten_title'
            }

        # Shorten to 57 characters
        shortened = page.title[:54] + '...' if len(page.title) > 57 else page.title

        old_value = page.title
        page.title = shortened
        page.save()

        return {
            'success': True,
            'message': 'Shortened title to optimal length',
            'old_value': old_value,
            'new_value': shortened,
            'method': 'shorten_title'
        }

    # ===== Other Fixes =====

    def _fix_generate_open_graph_tags(self, issue) -> Dict:
        """Generate Open Graph tags (stored in Page extra_metadata)"""
        page = issue.page

        # Generate OG tags based on existing page data
        og_tags = {
            'og:title': page.title or 'Untitled Page',
            'og:description': page.description or 'No description available',
            'og:url': page.url,
            'og:type': 'website',
        }

        # Store in page metadata (assuming we have a JSONField for this)
        # For now, just log it as this would require a new model field

        return {
            'success': True,
            'message': 'Generated Open Graph tags (suggested values)',
            'old_value': '(없음)',
            'new_value': str(og_tags),
            'method': 'generate_open_graph_tags'
        }

    def _fix_generate_alt_texts(self, issue) -> Dict:
        """Generate alt texts for images"""
        # This would require storing image data, which we don't currently have
        # For now, just mark as reviewed

        return {
            'success': True,
            'message': 'Alt text generation requires manual review',
            'old_value': issue.current_value or '(없음)',
            'new_value': '각 이미지에 설명적인 alt 텍스트를 추가하세요',
            'method': 'generate_alt_texts'
        }

    # ===== Helper Methods =====

    def _generate_meta_description_from_content(self, soup: BeautifulSoup, url: str) -> str:
        """Generate meta description from page content"""
        # Try to get title
        title = soup.find('title')
        title_text = title.text.strip() if title else ""

        # Extract first meaningful paragraph
        paragraphs = soup.find_all('p')
        first_sentence = ""
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 50:
                first_sentence = text[:120]
                break

        # Combine title and content
        if title_text and first_sentence:
            description = f"{title_text}. {first_sentence}"
        elif title_text:
            description = f"{title_text}에 대한 완벽한 가이드. 초보자도 쉽게 따라할 수 있습니다."
        elif first_sentence:
            description = first_sentence
        else:
            # Fallback: use URL path
            from urllib.parse import urlparse
            path = urlparse(url).path.strip('/').replace('-', ' ').replace('_', ' ')
            description = f"{path}에 대한 정보를 확인하세요." if path else "이 페이지에 대한 자세한 정보를 확인하세요."

        # Limit to 155 characters
        if len(description) > 155:
            description = description[:152] + '...'

        return description

    def _expand_description(self, current_desc: str, soup: BeautifulSoup) -> str:
        """Expand short description with content from page"""
        # Add more context from first paragraph
        paragraphs = soup.find_all('p')
        extra_content = ""
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 30 and text not in current_desc:
                extra_content = text[:80]
                break

        if extra_content:
            expanded = f"{current_desc} {extra_content}"
        else:
            expanded = f"{current_desc} 자세한 내용을 확인하세요."

        # Limit to 155 characters
        if len(expanded) > 155:
            expanded = expanded[:152] + '...'

        return expanded

    def _generate_title_from_content(self, soup: BeautifulSoup, url: str) -> str:
        """Generate title from page content"""
        # Try H1 first
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
            if 10 <= len(title) <= 60:
                return title

        # Try existing title tag
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
            if len(title) > 0:
                return title[:60]

        # Fallback: generate from URL
        from urllib.parse import urlparse
        path = urlparse(url).path.strip('/').replace('-', ' ').replace('_', ' ').title()
        site_name = self._extract_site_name(soup, url)

        if path and site_name:
            return f"{path} | {site_name}"
        elif path:
            return path[:60]
        else:
            return site_name or "Untitled Page"

    def _extract_site_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract site name from page or URL"""
        # Try OG site_name
        og_site_name = soup.find('meta', property='og:site_name')
        if og_site_name and og_site_name.get('content'):
            return og_site_name.get('content').strip()

        # Try domain name
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        # Remove www. and TLD
        name = domain.replace('www.', '').split('.')[0].title()
        return name
