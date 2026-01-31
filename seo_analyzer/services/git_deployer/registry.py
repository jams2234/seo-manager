"""
Project Type Registry
Manages available project detectors and updaters
"""
import logging
from pathlib import Path
from typing import Optional, Tuple
from .base import ProjectDetector, MetadataUpdater
from .nextjs import NextJSDetector, NextJSMetadataUpdater
from .html import StaticHTMLDetector, StaticHTMLMetadataUpdater

logger = logging.getLogger(__name__)


class ProjectTypeRegistry:
    """
    Registry for project type handlers
    Maintains detectors and updaters in priority order
    """

    def __init__(self):
        self._handlers = []

    def register(self, detector: ProjectDetector, updater: MetadataUpdater):
        """
        Register a project type handler

        Args:
            detector: Project detector instance
            updater: Metadata updater instance
        """
        self._handlers.append((detector, updater))

        # Sort by priority (highest first)
        self._handlers.sort(key=lambda x: x[0].get_priority(), reverse=True)

        logger.debug(f"Registered {detector.get_name()} handler with priority {detector.get_priority()}")

    def get_handler(self, repo_path: Path) -> Tuple[Optional[ProjectDetector], Optional[MetadataUpdater]]:
        """
        Get the appropriate handler for a repository

        Args:
            repo_path: Path to the cloned repository

        Returns:
            Tuple of (detector, updater) or (None, None) if no handler found
        """
        for detector, updater in self._handlers:
            if detector.can_handle(repo_path):
                logger.info(f"Selected {detector.get_name()} handler for repository")
                return detector, updater

        logger.error("No suitable project handler found")
        return None, None

    def get_registered_types(self) -> list:
        """
        Get list of registered project types

        Returns:
            List of project type names
        """
        return [detector.get_name() for detector, _ in self._handlers]


# Global registry instance
_global_registry = None


def get_registry() -> ProjectTypeRegistry:
    """
    Get or create the global registry instance

    Returns:
        ProjectTypeRegistry instance
    """
    global _global_registry

    if _global_registry is None:
        _global_registry = ProjectTypeRegistry()
        _initialize_default_handlers(_global_registry)

    return _global_registry


def _initialize_default_handlers(registry: ProjectTypeRegistry):
    """
    Initialize registry with default handlers

    Args:
        registry: Registry to initialize
    """
    # Register Next.js handler (high priority)
    registry.register(
        NextJSDetector(),
        NextJSMetadataUpdater()
    )

    # Register Static HTML handler (fallback, low priority)
    registry.register(
        StaticHTMLDetector(),
        StaticHTMLMetadataUpdater()
    )

    logger.info(f"Initialized registry with handlers: {registry.get_registered_types()}")


def register_custom_handler(detector: ProjectDetector, updater: MetadataUpdater):
    """
    Register a custom project type handler

    Args:
        detector: Custom detector instance
        updater: Custom updater instance
    """
    registry = get_registry()
    registry.register(detector, updater)
