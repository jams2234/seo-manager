"""
Code Preview Service for SEO Auto-Fix
Shows before/after code changes without applying them
"""
import os
import re
import shutil
import tempfile
import logging
from typing import Dict, Optional, Tuple
from pathlib import Path
import git

logger = logging.getLogger(__name__)


class CodePreviewService:
    """
    Service for previewing code changes before applying SEO fixes
    """

    def __init__(self):
        self.temp_dir = None

    def get_preview(self, issue) -> Dict:
        """
        Get preview of code changes for an issue

        Args:
            issue: SEOIssue model instance

        Returns:
            {
                'file_path': 'src/app/layout.tsx',
                'project_type': 'Next.js',
                'before_code': '...',
                'after_code': '...',
                'old_value': 'current title',
                'new_value': 'suggested title'
            }
        """
        domain = issue.page.domain

        # Check if Git is configured
        if not domain.git_enabled or not domain.git_repository:
            return self._get_db_only_preview(issue)

        try:
            # Clone repository
            self._clone_repository(domain)

            # Detect project type and get file
            project_type, file_path, file_content = self._detect_and_read_file()

            if not file_content:
                return self._get_db_only_preview(issue)

            # Determine field type
            field = 'title' if 'title' in issue.issue_type else 'description'

            # Extract current value from the actual code file
            old_value = self._extract_value_from_code(file_content, field, project_type)

            # Generate suggested value
            new_value = self._generate_suggested_value(issue)

            # Generate before/after code snippets
            before_code, after_code = self._generate_code_diff(
                file_content, field, new_value, project_type
            )

            return {
                'file_path': file_path,
                'project_type': project_type,
                'before_code': before_code,
                'after_code': after_code,
                'old_value': old_value if old_value else '(없음)',
                'new_value': new_value,
            }

        except Exception as e:
            logger.error(f"Preview generation failed: {e}", exc_info=True)
            return self._get_db_only_preview(issue)

        finally:
            self._cleanup()

    def _extract_value_from_code(self, content: str, field: str, project_type: str) -> str:
        """
        Extract the current value from code content
        """
        if project_type == 'Next.js':
            # Pattern to match title: 'value' or title: "value"
            if field == 'title':
                patterns = [
                    r"title:\s*['\"]([^'\"]+)['\"]",
                    r"title:\s*`([^`]+)`",
                ]
            else:
                patterns = [
                    r"description:\s*['\"]([^'\"]+)['\"]",
                    r"description:\s*`([^`]+)`",
                ]

            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    return match.group(1)

        elif project_type == 'Static HTML':
            if field == 'title':
                match = re.search(r'<title>([^<]+)</title>', content, re.IGNORECASE)
                if match:
                    return match.group(1)
            else:
                match = re.search(
                    r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']',
                    content, re.IGNORECASE
                )
                if match:
                    return match.group(1)

        return ''

    def _get_db_only_preview(self, issue) -> Dict:
        """
        Return preview for DB-only changes (no Git configured)
        """
        field = 'title' if 'title' in issue.issue_type else 'description'
        old_value = issue.current_value or '(없음)'
        new_value = self._generate_suggested_value(issue)

        # Generate simple before/after representation
        before_code = f'# Page Model (Database)\n{field} = "{old_value}"'
        after_code = f'# Page Model (Database)\n{field} = "{new_value}"'

        return {
            'file_path': 'Database (Page Model)',
            'project_type': 'Database',
            'before_code': before_code,
            'after_code': after_code,
            'old_value': old_value,
            'new_value': new_value,
        }

    def _generate_suggested_value(self, issue) -> str:
        """Generate suggested value for the issue"""
        # Use AutoFixService logic to generate value
        from .auto_fix_service import AutoFixService
        service = AutoFixService()

        page = issue.page
        fix_method = issue.auto_fix_method

        # For expand/shorten methods, always generate fresh value
        # For generate methods, use saved value if available
        methods_needing_fresh_generation = [
            'expand_title', 'shorten_title',
            'expand_meta_description', 'shorten_meta_description'
        ]

        if fix_method not in methods_needing_fresh_generation and issue.suggested_value:
            return issue.suggested_value

        html = service._fetch_html(page.url)

        if not html:
            return issue.suggested_value or '(생성 실패)'

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Route based on auto_fix_method for more accurate suggestions
        if fix_method == 'expand_title':
            # Expand short title
            current_title = page.title or service._generate_title_from_content(soup, page.url)
            site_name = service._extract_site_name(soup, page.url)
            expanded = f"{current_title} | {site_name}" if site_name else f"{current_title} - 완전 가이드"
            return expanded[:60] if len(expanded) > 60 else expanded

        elif fix_method == 'shorten_title':
            # Shorten long title
            current_title = page.title or ''
            return current_title[:54] + '...' if len(current_title) > 57 else current_title

        elif fix_method == 'expand_meta_description':
            # Expand short description
            current_desc = page.description or ''
            extra = service._generate_meta_description_from_content(soup, page.url)
            if current_desc and extra and current_desc not in extra:
                expanded = f"{current_desc} {extra[:80]}"
            else:
                expanded = extra or f"{current_desc} 자세한 내용을 확인하세요."
            return expanded[:155] if len(expanded) > 155 else expanded

        elif fix_method == 'shorten_meta_description':
            # Shorten long description
            current_desc = page.description or ''
            return current_desc[:152] + '...' if len(current_desc) > 155 else current_desc

        elif 'title' in issue.issue_type:
            return service._generate_title_from_content(soup, page.url)

        elif 'description' in issue.issue_type:
            return service._generate_meta_description_from_content(soup, page.url)

        return '(알 수 없음)'

    def _clone_repository(self, domain):
        """Clone Git repository to temporary directory"""
        self.temp_dir = tempfile.mkdtemp(prefix='seo_preview_')

        repo_url = domain.git_repository
        if domain.git_token and 'github.com' in repo_url:
            repo_url = repo_url.replace('https://', f'https://{domain.git_token}@')

        git.Repo.clone_from(
            repo_url,
            self.temp_dir,
            branch=domain.git_branch,
            depth=1
        )
        logger.info(f"Cloned repository to {self.temp_dir}")

    def _detect_and_read_file(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Detect project type and read the metadata file

        Returns:
            (project_type, file_path, file_content)
        """
        repo_path = Path(self.temp_dir)

        # Check for Next.js
        nextjs_files = [
            'src/app/layout.tsx',
            'src/app/layout.js',
            'app/layout.tsx',
            'app/layout.js',
        ]

        for layout_file in nextjs_files:
            full_path = repo_path / layout_file
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return ('Next.js', layout_file, content)

        # Check for HTML files
        html_paths = ['public/index.html', 'index.html', 'dist/index.html']
        for html_file in html_paths:
            full_path = repo_path / html_file
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return ('Static HTML', html_file, content)

        return (None, None, None)

    def _generate_code_diff(
        self,
        content: str,
        field: str,
        new_value: str,
        project_type: str
    ) -> Tuple[str, str]:
        """
        Generate before/after code snippets

        Returns:
            (before_code, after_code)
        """
        if project_type == 'Next.js':
            return self._generate_nextjs_diff(content, field, new_value)
        elif project_type == 'Static HTML':
            return self._generate_html_diff(content, field, new_value)
        else:
            return (content[:500], content[:500])

    def _generate_nextjs_diff(
        self,
        content: str,
        field: str,
        new_value: str
    ) -> Tuple[str, str]:
        """Generate diff for Next.js metadata"""

        # Find the metadata export block with more flexible pattern
        # This matches: export const metadata = { ... } or export const metadata: Metadata = { ... }
        metadata_start_pattern = r'export\s+const\s+metadata[\s\S]*?=\s*\{'

        match = re.search(metadata_start_pattern, content)
        if not match:
            return (content[:300], content[:300])

        # Find the start of metadata block
        start_idx = match.start()

        # Find the end of the metadata block (matching closing brace)
        brace_count = 0
        end_idx = match.end() - 1  # Start from the opening brace

        for i, char in enumerate(content[match.end()-1:], start=match.end()-1):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break

        # Get some context before and after
        context_start = max(0, start_idx - 30)
        context_end = min(len(content), end_idx + 30)

        before_snippet = content[context_start:context_end]

        # Check if field exists in the snippet
        field_pattern = rf"{field}:\s*['\"`]"
        field_exists = re.search(field_pattern, before_snippet)

        if field_exists:
            # Field exists - replace value
            if field == 'title':
                after_snippet = re.sub(
                    r"(title:\s*)(['\"`])([^'\"`]*?)(\2)",
                    rf"\g<1>\g<2>{self._escape_for_regex(new_value)}\g<4>",
                    before_snippet
                )
            else:
                after_snippet = re.sub(
                    r"(description:\s*)(['\"`])([^'\"`]*?)(\2)",
                    rf"\g<1>\g<2>{self._escape_for_regex(new_value)}\g<4>",
                    before_snippet
                )
        else:
            # Field doesn't exist - show it will be added
            # Find the closing brace of metadata and insert before it
            after_snippet = re.sub(
                r'(\s*)(};)',
                rf"\g<1>  {field}: '{self._escape_for_regex(new_value)}',\n\g<1>\g<2>",
                before_snippet
            )

        return (before_snippet, after_snippet)

    def _generate_html_diff(
        self,
        content: str,
        field: str,
        new_value: str
    ) -> Tuple[str, str]:
        """Generate diff for HTML files"""

        if field == 'title':
            # Find <title> tag
            match = re.search(r'<title>[^<]*</title>', content, re.IGNORECASE)
            if match:
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)

                before_snippet = content[start:end]
                after_snippet = re.sub(
                    r'(<title>)[^<]*(</title>)',
                    rf'\g<1>{new_value}\g<2>',
                    before_snippet,
                    flags=re.IGNORECASE
                )
                return (before_snippet, after_snippet)

        elif field == 'description':
            # Find meta description
            match = re.search(
                r'<meta\s+name=["\']description["\']\s+content=["\'][^"\']*["\'][^>]*>',
                content, re.IGNORECASE
            )
            if match:
                start = max(0, match.start() - 30)
                end = min(len(content), match.end() + 30)

                before_snippet = content[start:end]
                after_snippet = re.sub(
                    r'(<meta\s+name=["\']description["\']\s+content=["\'])[^"\']*(["\'][^>]*>)',
                    rf'\g<1>{new_value}\g<2>',
                    before_snippet,
                    flags=re.IGNORECASE
                )
                return (before_snippet, after_snippet)

        return (content[:300], content[:300])

    def _escape_for_regex(self, text: str) -> str:
        """Escape special regex characters in replacement text"""
        # Only escape backslash for the replacement string
        return text.replace('\\', '\\\\')

    def _cleanup(self):
        """Clean up temporary directory"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temp directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup: {e}")
