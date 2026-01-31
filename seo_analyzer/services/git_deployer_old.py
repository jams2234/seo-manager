"""
Git Deployer Service for SEO Auto-Fix
Automatically pushes SEO fixes to Git repositories, triggering Vercel deployments
"""
import os
import shutil
import logging
import tempfile
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import git
from django.utils import timezone

logger = logging.getLogger(__name__)


class GitDeployer:
    """
    Service for deploying SEO fixes to Git repositories

    Workflow:
    1. Clone Git repository to temporary directory
    2. Update HTML meta tags with fixed values
    3. Commit and push changes
    4. Vercel automatically detects Git push and deploys
    """

    def __init__(self, domain):
        """
        Initialize GitDeployer for a domain

        Args:
            domain: Domain model instance with Git configuration
        """
        self.domain = domain
        self.temp_dir = None
        self.repo = None

    def deploy_fixes(self, fixes: list) -> Dict:
        """
        Deploy multiple SEO fixes to Git repository

        Args:
            fixes: List of fix dictionaries with:
                - page_url: URL of the page
                - field: Field that was updated (title/description)
                - old_value: Previous value
                - new_value: Updated value

        Returns:
            {
                'success': True/False,
                'message': 'Deployment message',
                'commit_hash': 'abc123...',
                'changes_count': 5,
                'error': 'Error message if failed'
            }
        """
        if not self.domain.git_enabled:
            return {
                'success': False,
                'message': 'Git deployment is not enabled for this domain',
                'error': 'Git not enabled'
            }

        if not self.domain.git_repository or not self.domain.git_token:
            return {
                'success': False,
                'message': 'Git repository or token not configured',
                'error': 'Missing Git configuration'
            }

        try:
            # Step 1: Clone repository
            logger.info(f"Cloning repository: {self.domain.git_repository}")
            self._clone_repository()

            # Step 2: Apply fixes to HTML files
            logger.info(f"Applying {len(fixes)} fixes to HTML files")
            changes_count = self._apply_fixes_to_html(fixes)

            if changes_count == 0:
                self._cleanup()
                return {
                    'success': False,
                    'message': 'No changes were made to HTML files',
                    'changes_count': 0
                }

            # Step 3: Commit changes
            logger.info("Committing changes")
            commit_hash = self._commit_changes(fixes)

            # Step 4: Push to remote
            logger.info("Pushing to remote repository")
            self._push_to_remote()

            # Step 5: Update domain status
            self.domain.last_deployed_at = timezone.now()
            self.domain.deployment_status = 'success'
            self.domain.last_deployment_error = None
            self.domain.save(update_fields=['last_deployed_at', 'deployment_status', 'last_deployment_error'])

            # Cleanup
            self._cleanup()

            return {
                'success': True,
                'message': f'Successfully deployed {changes_count} SEO fixes to Git',
                'commit_hash': commit_hash,
                'changes_count': changes_count,
                'deployed_at': self.domain.last_deployed_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Git deployment failed: {e}", exc_info=True)

            # Update domain status
            self.domain.deployment_status = 'failed'
            self.domain.last_deployment_error = str(e)
            self.domain.save(update_fields=['deployment_status', 'last_deployment_error'])

            # Cleanup
            self._cleanup()

            return {
                'success': False,
                'message': f'Git deployment failed: {str(e)}',
                'error': str(e)
            }

    def _clone_repository(self):
        """Clone Git repository to temporary directory"""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix='seo_git_deploy_')
        logger.info(f"Created temporary directory: {self.temp_dir}")

        # Construct authenticated Git URL
        repo_url = self.domain.git_repository
        if self.domain.git_token:
            # Insert token into URL: https://TOKEN@github.com/user/repo.git
            if 'github.com' in repo_url:
                repo_url = repo_url.replace('https://', f'https://{self.domain.git_token}@')
            elif 'gitlab.com' in repo_url:
                repo_url = repo_url.replace('https://', f'https://oauth2:{self.domain.git_token}@')

        # Clone repository
        try:
            self.repo = git.Repo.clone_from(
                repo_url,
                self.temp_dir,
                branch=self.domain.git_branch,
                depth=1  # Shallow clone for speed
            )
            logger.info(f"Successfully cloned repository to {self.temp_dir}")
        except git.GitCommandError as e:
            logger.error(f"Failed to clone repository: {e}")
            raise Exception(f"Git clone failed: {str(e)}")

    def _apply_fixes_to_html(self, fixes: list) -> int:
        """
        Apply SEO fixes to HTML or Next.js files

        Returns:
            Number of files changed
        """
        changes_count = 0
        target_path = Path(self.temp_dir) / self.domain.git_target_path

        if not target_path.exists():
            raise Exception(f"Target path not found: {self.domain.git_target_path}")

        # Check if this is a Next.js project
        is_nextjs = (Path(self.temp_dir) / 'next.config.ts').exists() or (Path(self.temp_dir) / 'next.config.js').exists()

        if is_nextjs:
            logger.info("Detected Next.js project - will update metadata in TypeScript/JavaScript files")
            return self._apply_fixes_to_nextjs(fixes)

        # Group fixes by page URL to avoid reading same file multiple times
        fixes_by_page = {}
        for fix in fixes:
            page_url = fix.get('page_url', '')
            if page_url not in fixes_by_page:
                fixes_by_page[page_url] = []
            fixes_by_page[page_url].append(fix)

        # Process each page
        for page_url, page_fixes in fixes_by_page.items():
            # Find corresponding HTML file
            html_file = self._find_html_file_for_url(target_path, page_url)

            if not html_file:
                logger.warning(f"Could not find HTML file for URL: {page_url}")
                continue

            # Read and parse HTML
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                soup = BeautifulSoup(html_content, 'html.parser')
                modified = False

                # Apply all fixes for this page
                for fix in page_fixes:
                    field = fix.get('field', '')
                    new_value = fix.get('new_value', '')

                    if field == 'title':
                        # Update <title> tag
                        title_tag = soup.find('title')
                        if title_tag:
                            title_tag.string = new_value
                            modified = True
                        else:
                            # Create title tag in <head>
                            head = soup.find('head')
                            if head:
                                new_title = soup.new_tag('title')
                                new_title.string = new_value
                                head.append(new_title)
                                modified = True

                    elif field == 'description':
                        # Update meta description tag
                        meta_desc = soup.find('meta', attrs={'name': 'description'})
                        if meta_desc:
                            meta_desc['content'] = new_value
                            modified = True
                        else:
                            # Create meta description tag
                            head = soup.find('head')
                            if head:
                                new_meta = soup.new_tag('meta', attrs={'name': 'description', 'content': new_value})
                                head.append(new_meta)
                                modified = True

                # Write back if modified
                if modified:
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(str(soup.prettify()))

                    changes_count += 1
                    logger.info(f"Updated HTML file: {html_file.relative_to(self.temp_dir)}")

            except Exception as e:
                logger.error(f"Failed to update HTML file {html_file}: {e}")
                continue

        return changes_count

    def _apply_fixes_to_nextjs(self, fixes: list) -> int:
        """
        Apply SEO fixes to Next.js TypeScript/JavaScript files

        Returns:
            Number of files changed
        """
        import re
        changes_count = 0

        # Group fixes by field
        title_fix = None
        description_fix = None

        for fix in fixes:
            field = fix.get('field', '')
            if field == 'title' and not title_fix:
                title_fix = fix
            elif field == 'description' and not description_fix:
                description_fix = fix

        if not title_fix and not description_fix:
            return 0

        # Find Next.js layout or page file
        layout_files = [
            Path(self.temp_dir) / 'src' / 'app' / 'layout.tsx',
            Path(self.temp_dir) / 'src' / 'app' / 'layout.js',
            Path(self.temp_dir) / 'app' / 'layout.tsx',
            Path(self.temp_dir) / 'app' / 'layout.js',
            Path(self.temp_dir) / 'src' / 'app' / 'page.tsx',
            Path(self.temp_dir) / 'src' / 'app' / 'page.js',
        ]

        layout_file = None
        for candidate in layout_files:
            if candidate.exists():
                layout_file = candidate
                break

        if not layout_file:
            logger.warning("Could not find Next.js layout or page file")
            return 0

        try:
            # Read file
            with open(layout_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            modified = False

            # Update title
            if title_fix:
                new_title = title_fix.get('new_value', '')
                # Match: title: '...' or title: "..."
                title_pattern = r"(title:\s*['\"])([^'\"]*?)(['\"])"
                if re.search(title_pattern, content):
                    content = re.sub(title_pattern, rf"\1{new_title}\3", content)
                    modified = True
                    logger.info(f"Updated title in {layout_file.name}")

            # Update description
            if description_fix:
                new_desc = description_fix.get('new_value', '')
                # Match: description: '...' or description: "..."
                desc_pattern = r"(description:\s*['\"])([^'\"]*?)(['\"])"
                if re.search(desc_pattern, content):
                    content = re.sub(desc_pattern, rf"\1{new_desc}\3", content)
                    modified = True
                    logger.info(f"Updated description in {layout_file.name}")

            # Write back if modified
            if modified:
                with open(layout_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                changes_count = 1
                logger.info(f"Updated Next.js file: {layout_file.relative_to(self.temp_dir)}")

        except Exception as e:
            logger.error(f"Failed to update Next.js file {layout_file}: {e}")

        return changes_count

    def _find_html_file_for_url(self, target_path: Path, page_url: str) -> Optional[Path]:
        """
        Find HTML file corresponding to a URL

        For example:
        - https://example.com/ -> index.html
        - https://example.com/about -> about.html or about/index.html
        - https://example.com/blog/post -> blog/post.html or blog/post/index.html
        """
        from urllib.parse import urlparse

        parsed = urlparse(page_url)
        path = parsed.path.strip('/')

        # Try different file patterns
        candidates = []

        if not path:
            # Root URL -> index.html
            candidates = [
                target_path / 'index.html',
                target_path / 'index.htm',
            ]
        else:
            # Sub-path
            candidates = [
                target_path / f"{path}.html",
                target_path / path / 'index.html',
                target_path / f"{path}.htm",
                target_path / path / 'index.htm',
            ]

        # Return first existing file
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate

        return None

    def _commit_changes(self, fixes: list) -> str:
        """
        Commit changes to Git

        Returns:
            Commit hash
        """
        # Stage all changes
        self.repo.git.add(A=True)

        # Create commit message
        commit_message = self._generate_commit_message(fixes)

        # Commit
        commit = self.repo.index.commit(commit_message)

        logger.info(f"Created commit: {commit.hexsha[:8]}")

        return commit.hexsha

    def _generate_commit_message(self, fixes: list) -> str:
        """Generate descriptive commit message"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        # Count fixes by type
        title_fixes = sum(1 for f in fixes if f.get('field') == 'title')
        description_fixes = sum(1 for f in fixes if f.get('field') == 'description')

        parts = []
        if title_fixes:
            parts.append(f"{title_fixes} title{'s' if title_fixes > 1 else ''}")
        if description_fixes:
            parts.append(f"{description_fixes} meta description{'s' if description_fixes > 1 else ''}")

        summary = ' and '.join(parts)

        message = f"""SEO: Auto-fix {summary}

Automatically applied SEO improvements:
- {title_fixes} page title updates
- {description_fixes} meta description updates

Generated by SEO Analyzer at {timestamp}
"""

        return message

    def _push_to_remote(self):
        """Push commits to remote repository"""
        try:
            origin = self.repo.remote(name='origin')
            origin.push(self.domain.git_branch)
            logger.info(f"Successfully pushed to {self.domain.git_branch}")
        except git.GitCommandError as e:
            logger.error(f"Failed to push to remote: {e}")
            raise Exception(f"Git push failed: {str(e)}")

    def _cleanup(self):
        """Clean up temporary directory"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory: {e}")
