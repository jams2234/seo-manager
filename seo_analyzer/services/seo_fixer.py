"""
SEO Fixer Service
Automatically fixes SEO issues by modifying HTML content
"""
import os
import logging
import requests
from datetime import datetime
from typing import Dict, Optional
from bs4 import BeautifulSoup
from django.utils import timezone

from .base import ManagerService

logger = logging.getLogger(__name__)


class SEOFixer(ManagerService):
    """
    Service for automatically fixing SEO issues
    """

    def __init__(self):
        super().__init__()
        self.backup_dir = '/tmp/seo_backups'
        os.makedirs(self.backup_dir, exist_ok=True)

    def fix_issue(self, issue) -> Dict:
        """
        Fix an SEO issue based on its type

        Args:
            issue: SEOIssue model instance

        Returns:
            Result dictionary with success status and details
        """
        try:
            self.log_info(f"Attempting to fix issue: {issue.issue_type} for {issue.page.url}")

            # Get the fix method based on issue type
            fix_method_map = {
                'missing_title': self.fix_missing_title,
                'title_too_short': self.fix_title_too_short,
                'title_too_long': self.fix_title_too_long,
                'missing_meta_description': self.fix_missing_meta_description,
                'meta_description_too_short': self.fix_meta_description_too_short,
                'meta_description_too_long': self.fix_meta_description_too_long,
                'missing_h1': self.fix_missing_h1,
                'multiple_h1': self.fix_multiple_h1,
                'missing_alt_text': self.fix_missing_alt_text,
                'missing_viewport': self.fix_missing_viewport,
                'external_links_no_rel': self.fix_external_links_no_rel,
            }

            fix_method = fix_method_map.get(issue.issue_type)

            if not fix_method:
                return {
                    'success': False,
                    'error': f"No fix method available for issue type: {issue.issue_type}"
                }

            # Fetch the page HTML
            html_content = self._fetch_page_html(issue.page.url)

            if not html_content:
                return {
                    'success': False,
                    'error': 'Failed to fetch page HTML'
                }

            # Create backup
            backup_path = self._create_backup(issue.page.url, html_content)

            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')

            # Apply the fix
            result = fix_method(soup, issue)

            if not result.get('success'):
                return result

            # Get modified HTML
            modified_html = str(soup)

            # TODO: Deploy the modified HTML to the actual website
            # This would require FTP/SFTP/Git integration or direct file write
            # For now, we'll simulate the fix

            self.log_info(f"Successfully fixed issue {issue.id}: {issue.issue_type}")

            return {
                'success': True,
                'issue_type': issue.issue_type,
                'backup_path': backup_path,
                'changes': result.get('changes', {}),
                'fixed_at': timezone.now().isoformat(),
                'note': 'Fix simulated - deployment to actual website not yet implemented'
            }

        except Exception as e:
            self.log_error(f"Failed to fix issue {issue.id}: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"Fix failed: {str(e)}"
            }

    def _fetch_page_html(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.log_error(f"Failed to fetch HTML from {url}: {e}")
            return None

    def _create_backup(self, url: str, html_content: str) -> str:
        """Create backup of original HTML"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{url.replace('://', '_').replace('/', '_')}_{timestamp}.html"
        backup_path = os.path.join(self.backup_dir, filename)

        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        self.log_info(f"Backup created: {backup_path}")
        return backup_path

    def fix_missing_title(self, soup: BeautifulSoup, issue) -> Dict:
        """Fix missing <title> tag"""
        try:
            head = soup.find('head')
            if not head:
                # Create head if it doesn't exist
                head = soup.new_tag('head')
                if soup.html:
                    soup.html.insert(0, head)
                else:
                    soup.insert(0, head)

            # Create title tag
            title_tag = soup.new_tag('title')
            title_text = issue.suggested_value or issue.extra_data.get('suggested_title', 'Untitled Page')
            title_tag.string = title_text

            # Insert title
            head.insert(0, title_tag)

            return {
                'success': True,
                'changes': {
                    'added': f'<title>{title_text}</title>'
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def fix_title_too_short(self, soup: BeautifulSoup, issue) -> Dict:
        """Fix title that's too short"""
        try:
            title_tag = soup.find('title')
            if title_tag:
                old_title = title_tag.string or ''
                new_title = issue.suggested_value or old_title
                title_tag.string = new_title

                return {
                    'success': True,
                    'changes': {
                        'old': old_title,
                        'new': new_title
                    }
                }
            return {'success': False, 'error': 'Title tag not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def fix_title_too_long(self, soup: BeautifulSoup, issue) -> Dict:
        """Fix title that's too long"""
        try:
            title_tag = soup.find('title')
            if title_tag:
                old_title = title_tag.string or ''
                new_title = issue.suggested_value or old_title[:60]
                title_tag.string = new_title

                return {
                    'success': True,
                    'changes': {
                        'old': old_title,
                        'new': new_title
                    }
                }
            return {'success': False, 'error': 'Title tag not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def fix_missing_meta_description(self, soup: BeautifulSoup, issue) -> Dict:
        """Fix missing meta description"""
        try:
            head = soup.find('head')
            if not head:
                return {'success': False, 'error': 'Head tag not found'}

            # Create meta description tag
            meta_tag = soup.new_tag('meta')
            meta_tag['name'] = 'description'
            description_text = issue.suggested_value or issue.extra_data.get('suggested_description', '')
            meta_tag['content'] = description_text

            # Insert meta tag
            head.append(meta_tag)

            return {
                'success': True,
                'changes': {
                    'added': f'<meta name="description" content="{description_text}">'
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def fix_meta_description_too_short(self, soup: BeautifulSoup, issue) -> Dict:
        """Fix meta description that's too short"""
        try:
            meta_tag = soup.find('meta', attrs={'name': 'description'})
            if meta_tag:
                old_content = meta_tag.get('content', '')
                new_content = issue.suggested_value or old_content
                meta_tag['content'] = new_content

                return {
                    'success': True,
                    'changes': {
                        'old': old_content,
                        'new': new_content
                    }
                }
            return {'success': False, 'error': 'Meta description tag not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def fix_meta_description_too_long(self, soup: BeautifulSoup, issue) -> Dict:
        """Fix meta description that's too long"""
        try:
            meta_tag = soup.find('meta', attrs={'name': 'description'})
            if meta_tag:
                old_content = meta_tag.get('content', '')
                new_content = issue.suggested_value or old_content[:160]
                meta_tag['content'] = new_content

                return {
                    'success': True,
                    'changes': {
                        'old': old_content,
                        'new': new_content
                    }
                }
            return {'success': False, 'error': 'Meta description tag not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def fix_missing_h1(self, soup: BeautifulSoup, issue) -> Dict:
        """Fix missing H1 tag"""
        try:
            body = soup.find('body')
            if not body:
                return {'success': False, 'error': 'Body tag not found'}

            # Create H1 tag
            h1_tag = soup.new_tag('h1')
            h1_text = issue.suggested_value or issue.extra_data.get('suggested_h1', 'Main Heading')
            h1_tag.string = h1_text

            # Insert H1 at the beginning of body
            if body.contents:
                body.insert(0, h1_tag)
            else:
                body.append(h1_tag)

            return {
                'success': True,
                'changes': {
                    'added': f'<h1>{h1_text}</h1>'
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def fix_multiple_h1(self, soup: BeautifulSoup, issue) -> Dict:
        """Fix multiple H1 tags (keep only the first one)"""
        try:
            h1_tags = soup.find_all('h1')
            if len(h1_tags) <= 1:
                return {'success': False, 'error': 'No multiple H1 tags found'}

            # Keep the first H1, convert others to H2
            removed_count = 0
            for h1_tag in h1_tags[1:]:
                h2_tag = soup.new_tag('h2')
                h2_tag.string = h1_tag.string
                h1_tag.replace_with(h2_tag)
                removed_count += 1

            return {
                'success': True,
                'changes': {
                    'converted': f'{removed_count} H1 tags converted to H2'
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def fix_missing_alt_text(self, soup: BeautifulSoup, issue) -> Dict:
        """Fix missing alt text on images"""
        try:
            # Get the specific image from extra_data if available
            image_src = issue.extra_data.get('image_src')

            if image_src:
                # Fix specific image
                img_tag = soup.find('img', attrs={'src': image_src})
                if img_tag and not img_tag.get('alt'):
                    alt_text = issue.suggested_value or 'Image'
                    img_tag['alt'] = alt_text

                    return {
                        'success': True,
                        'changes': {
                            'image': image_src,
                            'added_alt': alt_text
                        }
                    }
            else:
                # Fix all images without alt text
                fixed_count = 0
                img_tags = soup.find_all('img')

                for img_tag in img_tags:
                    if not img_tag.get('alt'):
                        # Generate alt text from src or use generic
                        src = img_tag.get('src', '')
                        alt_text = src.split('/')[-1].split('.')[0].replace('-', ' ').replace('_', ' ').title()
                        img_tag['alt'] = alt_text
                        fixed_count += 1

                return {
                    'success': True,
                    'changes': {
                        'fixed_images': fixed_count
                    }
                }

            return {'success': False, 'error': 'Image not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def fix_missing_viewport(self, soup: BeautifulSoup, issue) -> Dict:
        """Fix missing viewport meta tag"""
        try:
            head = soup.find('head')
            if not head:
                return {'success': False, 'error': 'Head tag not found'}

            # Create viewport meta tag
            meta_tag = soup.new_tag('meta')
            meta_tag['name'] = 'viewport'
            meta_tag['content'] = 'width=device-width, initial-scale=1.0'

            # Insert meta tag
            head.append(meta_tag)

            return {
                'success': True,
                'changes': {
                    'added': '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def fix_external_links_no_rel(self, soup: BeautifulSoup, issue) -> Dict:
        """Fix external links missing rel attribute"""
        try:
            # Get the specific link from extra_data if available
            link_href = issue.extra_data.get('link_href')

            if link_href:
                # Fix specific link
                link_tag = soup.find('a', attrs={'href': link_href})
                if link_tag:
                    link_tag['rel'] = 'noopener noreferrer'

                    return {
                        'success': True,
                        'changes': {
                            'link': link_href,
                            'added_rel': 'noopener noreferrer'
                        }
                    }
            else:
                # Fix all external links without rel
                fixed_count = 0
                link_tags = soup.find_all('a', href=True)

                for link_tag in link_tags:
                    href = link_tag['href']
                    # Check if it's an external link
                    if href.startswith('http') and not link_tag.get('rel'):
                        link_tag['rel'] = 'noopener noreferrer'
                        fixed_count += 1

                return {
                    'success': True,
                    'changes': {
                        'fixed_links': fixed_count
                    }
                }

            return {'success': False, 'error': 'Link not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def rollback(self, backup_path: str, target_url: str) -> Dict:
        """
        Rollback changes using a backup file

        Args:
            backup_path: Path to backup HTML file
            target_url: URL to restore to

        Returns:
            Result dictionary
        """
        try:
            if not os.path.exists(backup_path):
                return {
                    'success': False,
                    'error': 'Backup file not found'
                }

            with open(backup_path, 'r', encoding='utf-8') as f:
                original_html = f.read()

            # TODO: Deploy the original HTML back to the website
            # This would require the same deployment mechanism as fix_issue

            self.log_info(f"Rollback successful for {target_url}")

            return {
                'success': True,
                'restored_from': backup_path,
                'target_url': target_url,
                'note': 'Rollback simulated - deployment to actual website not yet implemented'
            }

        except Exception as e:
            self.log_error(f"Rollback failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"Rollback failed: {str(e)}"
            }
