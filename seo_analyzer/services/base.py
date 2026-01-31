"""
Base Service Interface
Base classes for all services
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """
    Base class for all services
    Provides common functionality
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def log_info(self, message: str):
        """Info log"""
        self.logger.info(f"[{self.__class__.__name__}] {message}")

    def log_error(self, message: str, exc_info: bool = False):
        """Error log"""
        self.logger.error(f"[{self.__class__.__name__}] {message}", exc_info=exc_info)

    def log_warning(self, message: str):
        """Warning log"""
        self.logger.warning(f"[{self.__class__.__name__}] {message}")

    def log_debug(self, message: str):
        """Debug log"""
        self.logger.debug(f"[{self.__class__.__name__}] {message}")


class AnalyzerService(BaseService):
    """
    Analyzer Service Interface
    For services that perform analysis
    """

    @abstractmethod
    def analyze(self, target, **kwargs) -> Dict:
        """
        Perform analysis

        Args:
            target: Analysis target (URL, Page object, etc.)
            **kwargs: Additional options

        Returns:
            Analysis result dictionary
        """
        pass

    def validate(self, result: Dict) -> bool:
        """
        Validate result

        Args:
            result: Analysis result

        Returns:
            Validity
        """
        # Default implementation: check for 'error' key
        return not result.get('error', False)


class OptimizerService(BaseService):
    """
    Optimizer Service Interface
    For services that perform optimization
    """

    @abstractmethod
    def optimize(self, target, **kwargs) -> Dict:
        """
        Perform optimization

        Args:
            target: Optimization target
            **kwargs: Additional options

        Returns:
            Optimization result
        """
        pass

    def measure_improvement(self, before: Dict, after: Dict) -> Dict:
        """
        Measure improvement effect

        Args:
            before: State before optimization
            after: State after optimization

        Returns:
            Measurement result
        """
        return {
            'before': before,
            'after': after,
            'improvement': {},  # To be implemented by subclass
        }


class ManagerService(BaseService):
    """
    Manager Service Interface
    For services that manage resources (e.g., sitemaps)
    """

    @abstractmethod
    def generate(self, **kwargs) -> Dict:
        """Generate resource"""
        pass

    @abstractmethod
    def validate(self, target, **kwargs) -> Dict:
        """Validate resource"""
        pass

    @abstractmethod
    def deploy(self, target, **kwargs) -> Dict:
        """Deploy resource"""
        pass
