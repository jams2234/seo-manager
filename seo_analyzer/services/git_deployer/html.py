"""
Static HTML Project Handler
"""
import logging
from pathlib import Path
from typing import Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .base import ProjectDetector, MetadataUpdater
from .exceptions import FileNotFoundError as GitFileNotFoundError, MetadataUpdateError

logger = logging.getLogger(__name__)


class StaticHTMLDetector(ProjectDetector):
    """Detector for static HTML projects (fallback)"""

    def can_handle(self, repo_path: Path) -> bool:
        """Always returns True - this is the fallback handler"""
        return True

    def get_name(self) -> str:
        return "Static HTML"

    def get_priority(self) -> int:
        return 0  # Lowest priority (fallback)


class StaticHTMLMetadataUpdater(MetadataUpdater):
    """Update metadata in static HTML files"""

    def __init__(self, target_path: str = 'public'):
        """
        Initialize HTML updater

        Args:
            target_path: Relative path to HTML files (e.g., 'public', 'dist')
        """
        self.target_path = target_path

    def update_metadata(self, repo_path: Path, fixes: list) -> int:
        """Update metadata in HTML files"""

        target_dir = repo_path / self.target_path

        if not target_dir.exists():
            error_msg = f"Target directory not found: {self.target_path}"
            logger.error(error_msg)
            raise GitFileNotFoundError(error_msg)

        # Group fixes by page URL
        fixes_by_page = {}
        for fix in fixes:
            page_url = fix.get('page_url', '')
            if page_url not in fixes_by_page:
                fixes_by_page[page_url] = []
            fixes_by_page[page_url].append(fix)

        changes_count = 0

        # Process each page
        for page_url, page_fixes in fixes_by_page.items():
            html_file = self._find_html_file(target_dir, page_url)

            if not html_file:
                logger.warning(f"Could not find HTML file for URL: {page_url}")
                continue

            try:
                # Read and parse HTML
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                soup = BeautifulSoup(html_content, 'html.parser')
                modified = False

                # Apply fixes
                for fix in page_fixes:
                    field = fix.get('field', '')
                    new_value = fix.get('new_value', '')

                    if field == 'title':
                        if self._update_title(soup, new_value):
                            modified = True
                            logger.info(f"Updated title in {html_file.name}")

                    elif field == 'description':
                        if self._update_description(soup, new_value):
                            modified = True
                            logger.info(f"Updated description in {html_file.name}")

                # Write back if modified
                if modified:
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(str(soup.prettify()))

                    changes_count += 1
                    logger.info(f"Updated HTML file: {html_file.relative_to(repo_path)}")

            except (IOError, OSError) as e:
                logger.error(f"Failed to read/write HTML file {html_file}: {e}", exc_info=True)
                # Continue processing other files even if one fails
                continue
            except Exception as e:
                logger.error(f"Unexpected error updating HTML file {html_file}: {e}", exc_info=True)
                continue

        return changes_count

    def _find_html_file(self, target_dir: Path, page_url: str) -> Optional[Path]:
        """
        Find HTML file corresponding to a URL

        Examples:
            https://example.com/ -> index.html
            https://example.com/about -> about.html or about/index.html
        """
        parsed = urlparse(page_url)
        path = parsed.path.strip('/')

        candidates = []

        if not path:
            # Root URL
            candidates = [
                target_dir / 'index.html',
                target_dir / 'index.htm',
            ]
        else:
            # Sub-path
            candidates = [
                target_dir / f"{path}.html",
                target_dir / path / 'index.html',
                target_dir / f"{path}.htm",
                target_dir / path / 'index.htm',
            ]

        # Return first existing file
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate

        return None

    def _update_title(self, soup: BeautifulSoup, new_value: str) -> bool:
        """Update <title> tag"""
        title_tag = soup.find('title')

        if title_tag:
            title_tag.string = new_value
            return True
        else:
            # Create title tag
            head = soup.find('head')
            if head:
                new_title = soup.new_tag('title')
                new_title.string = new_value
                head.append(new_title)
                return True

        return False

    def _update_description(self, soup: BeautifulSoup, new_value: str) -> bool:
        """Update meta description tag"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})

        if meta_desc:
            meta_desc['content'] = new_value
            return True
        else:
            # Create meta description
            head = soup.find('head')
            if head:
                new_meta = soup.new_tag('meta', attrs={'name': 'description', 'content': new_value})
                head.append(new_meta)
                return True

        return False
