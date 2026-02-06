"""
SEO Analyzer Services Package
"""
from .google_api_client import GoogleAPIClient
from .pagespeed_insights import PageSpeedInsightsService
from .search_console import SearchConsoleService
from .domain_scanner import DomainScanner
from .domain_refresh_service import DomainRefreshService
from .rate_limiter import RateLimiter, BatchRateLimiter
from .seo_advisor import SEOAdvisor
from .content_analyzer import ContentAnalyzer
from .sitemap_manager import SitemapManager
from .seo_fixer import SEOFixer
from .sitemap_editor import SitemapEditorService
from .claude_client import ClaudeAPIClient, ClaudeAnalyzer
from .sitemap_ai_analyzer import SitemapAIAnalyzerService
from .seo_knowledge_builder import SEOKnowledgeBuilder
from .ai_auto_fixer import AIAutoFixer
from .ai_analysis_engine import AIAnalysisEngine
from .vector_store import SEOVectorStore, get_vector_store

# Custom exceptions
from .exceptions import (
    SEOAnalyzerException,
    DomainException,
    DomainNotFoundError,
    DomainRefreshError,
    PageException,
    PageNotFoundError,
    PageNotAccessibleError,
    PageAnalysisError,
    APIException,
    APIQuotaExceededError,
    APIConnectionError,
    APIResponseError,
    GitException,
    GitNotConfiguredError,
    GitDeploymentError,
    GitCloneError,
    GitPushError,
    SEOIssueException,
    IssueNotFixableError,
    FixGenerationError,
    SitemapException,
    SitemapGenerationError,
    SitemapDeploymentError,
    ValidationException,
    InvalidURLError,
    CircularReferenceError,
)

__all__ = [
    # Services
    'GoogleAPIClient',
    'PageSpeedInsightsService',
    'SearchConsoleService',
    'DomainScanner',
    'DomainRefreshService',
    'RateLimiter',
    'BatchRateLimiter',
    'SEOAdvisor',
    'ContentAnalyzer',
    'SitemapManager',
    'SEOFixer',
    'SitemapEditorService',
    'ClaudeAPIClient',
    'ClaudeAnalyzer',
    'SitemapAIAnalyzerService',
    'SEOKnowledgeBuilder',
    'AIAutoFixer',
    'AIAnalysisEngine',
    'SEOVectorStore',
    'get_vector_store',
    # Exceptions
    'SEOAnalyzerException',
    'DomainException',
    'DomainNotFoundError',
    'DomainRefreshError',
    'PageException',
    'PageNotFoundError',
    'PageNotAccessibleError',
    'PageAnalysisError',
    'APIException',
    'APIQuotaExceededError',
    'APIConnectionError',
    'APIResponseError',
    'GitException',
    'GitNotConfiguredError',
    'GitDeploymentError',
    'GitCloneError',
    'GitPushError',
    'SEOIssueException',
    'IssueNotFixableError',
    'FixGenerationError',
    'SitemapException',
    'SitemapGenerationError',
    'SitemapDeploymentError',
    'ValidationException',
    'InvalidURLError',
    'CircularReferenceError',
]
