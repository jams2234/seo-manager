"""
Base classes for Git Deployer Strategy Pattern
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ProjectDetector(ABC):
    """
    Abstract base class for project type detection
    """

    @abstractmethod
    def can_handle(self, repo_path: Path) -> bool:
        """
        Check if this detector can handle the given repository

        Args:
            repo_path: Path to the cloned repository

        Returns:
            True if this detector can handle the project
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of the project type

        Returns:
            Project type name (e.g., "Next.js", "Static HTML")
        """
        pass

    @abstractmethod
    def get_priority(self) -> int:
        """
        Get the priority of this detector
        Higher values are checked first

        Returns:
            Priority value (0-100)
        """
        pass


class MetadataUpdater(ABC):
    """
    Abstract base class for metadata updating strategies
    """

    @abstractmethod
    def update_metadata(self, repo_path: Path, fixes: list) -> int:
        """
        Update metadata in the repository

        Args:
            repo_path: Path to the cloned repository
            fixes: List of fix dictionaries with:
                - page_url: URL of the page
                - field: Field to update (title/description)
                - old_value: Previous value
                - new_value: New value

        Returns:
            Number of files changed
        """
        pass

    def _group_fixes_by_field(self, fixes: list) -> dict:
        """
        Helper method to group fixes by field type

        Args:
            fixes: List of fix dictionaries

        Returns:
            Dictionary with 'title' and 'description' fixes
        """
        result = {
            'title': None,
            'description': None,
        }

        for fix in fixes:
            field = fix.get('field', '')
            if field == 'title' and not result['title']:
                result['title'] = fix
            elif field == 'description' and not result['description']:
                result['description'] = fix

        return result
