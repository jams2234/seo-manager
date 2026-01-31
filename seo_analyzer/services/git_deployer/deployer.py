"""
Git Deployer Service for SEO Auto-Fix
Automatically pushes SEO fixes to Git repositories, triggering Vercel deployments

Refactored with Strategy Pattern for extensibility
"""
import os
import shutil
import logging
import tempfile
from typing import Dict
from datetime import datetime
from pathlib import Path
import git
from django.utils import timezone

from .registry import get_registry
from .html import StaticHTMLMetadataUpdater
from .exceptions import (
    GitConfigurationError,
    GitAuthenticationError,
    GitCloneError,
    GitPushError,
    ProjectDetectionError,
)

logger = logging.getLogger(__name__)


class GitDeployer:
    """
    Service for deploying SEO fixes to Git repositories

    Workflow:
    1. Clone Git repository to temporary directory
    2. Detect project type (Next.js, Static HTML, etc.)
    3. Update metadata with appropriate handler
    4. Commit and push changes
    5. Vercel automatically detects Git push and deploys
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
            error = GitConfigurationError('Git repository or token not configured')
            return {
                'success': False,
                'message': str(error),
                'error': error.__class__.__name__
            }

        try:
            # Step 1: Clone repository
            logger.info(f"Cloning repository: {self.domain.git_repository}")
            self._clone_repository()

            # Step 2: Detect project type and apply fixes
            logger.info(f"Applying {len(fixes)} fixes")
            changes_count = self._apply_fixes(fixes)

            if changes_count == 0:
                self._cleanup()
                return {
                    'success': False,
                    'message': 'No changes were made to files',
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

        except GitAuthenticationError as e:
            logger.error(f"Git authentication failed: {e}", exc_info=True)
            self.domain.deployment_status = 'failed'
            self.domain.last_deployment_error = f"Authentication error: {str(e)}"
            self.domain.save(update_fields=['deployment_status', 'last_deployment_error'])
            self._cleanup()
            return {
                'success': False,
                'message': f'Git authentication failed: {str(e)}',
                'error': e.__class__.__name__,
                'error_type': 'authentication'
            }

        except (GitCloneError, GitPushError) as e:
            logger.error(f"Git operation failed: {e}", exc_info=True)
            self.domain.deployment_status = 'failed'
            self.domain.last_deployment_error = str(e)
            self.domain.save(update_fields=['deployment_status', 'last_deployment_error'])
            self._cleanup()
            return {
                'success': False,
                'message': f'Git operation failed: {str(e)}',
                'error': e.__class__.__name__,
                'error_type': 'git_operation'
            }

        except ProjectDetectionError as e:
            logger.error(f"Project detection failed: {e}", exc_info=True)
            self.domain.deployment_status = 'failed'
            self.domain.last_deployment_error = str(e)
            self.domain.save(update_fields=['deployment_status', 'last_deployment_error'])
            self._cleanup()
            return {
                'success': False,
                'message': f'Could not detect project type: {str(e)}',
                'error': e.__class__.__name__,
                'error_type': 'project_detection'
            }

        except Exception as e:
            logger.error(f"Unexpected deployment error: {e}", exc_info=True)
            self.domain.deployment_status = 'failed'
            self.domain.last_deployment_error = f"Unexpected error: {str(e)}"
            self.domain.save(update_fields=['deployment_status', 'last_deployment_error'])
            self._cleanup()
            return {
                'success': False,
                'message': f'Deployment failed: {str(e)}',
                'error': e.__class__.__name__,
                'error_type': 'unexpected'
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
            # Detect authentication errors
            error_msg = str(e).lower()
            if 'authentication' in error_msg or 'permission denied' in error_msg or '403' in error_msg:
                raise GitAuthenticationError(f"Git authentication failed. Check your token and permissions: {str(e)}")
            else:
                raise GitCloneError(f"Failed to clone repository: {str(e)}")

    def _apply_fixes(self, fixes: list) -> int:
        """
        Apply fixes using appropriate project type handler

        Args:
            fixes: List of fix dictionaries

        Returns:
            Number of files changed
        """
        repo_path = Path(self.temp_dir)

        # Get handler from registry
        registry = get_registry()
        detector, updater = registry.get_handler(repo_path)

        if not updater:
            raise ProjectDetectionError("No suitable project handler found for this repository")

        logger.info(f"Using {detector.get_name()} handler")

        # If using StaticHTML handler, pass target_path
        if isinstance(updater, StaticHTMLMetadataUpdater):
            updater.target_path = self.domain.git_target_path

        # Apply fixes using the selected handler
        return updater.update_metadata(repo_path, fixes)

    def _commit_changes(self, fixes: list) -> str:
        """
        Commit changes to Git

        Args:
            fixes: List of fix dictionaries

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
            # Detect authentication errors
            error_msg = str(e).lower()
            if 'authentication' in error_msg or 'permission denied' in error_msg or '403' in error_msg:
                raise GitAuthenticationError(f"Git push authentication failed. Check your token and permissions: {str(e)}")
            else:
                raise GitPushError(f"Failed to push to remote repository: {str(e)}")

    def _cleanup(self):
        """Clean up temporary directory"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory: {e}")
