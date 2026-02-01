"""
Custom Exceptions for SEO Analyzer Services

Provides a consistent exception hierarchy for error handling across services.
"""


class SEOAnalyzerException(Exception):
    """Base exception for all SEO Analyzer errors"""
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code or 'SEO_ERROR'
        self.details = details or {}


# Domain related exceptions
class DomainException(SEOAnalyzerException):
    """Base exception for domain-related errors"""
    pass


class DomainNotFoundError(DomainException):
    """Raised when a domain is not found"""
    def __init__(self, domain_id: int = None, domain_name: str = None):
        message = f"Domain not found"
        if domain_id:
            message += f" (id={domain_id})"
        if domain_name:
            message += f" (name={domain_name})"
        super().__init__(message, 'DOMAIN_NOT_FOUND', {'domain_id': domain_id, 'domain_name': domain_name})


class DomainRefreshError(DomainException):
    """Raised when domain refresh fails"""
    def __init__(self, message: str, domain_id: int = None):
        super().__init__(message, 'DOMAIN_REFRESH_ERROR', {'domain_id': domain_id})


# Page related exceptions
class PageException(SEOAnalyzerException):
    """Base exception for page-related errors"""
    pass


class PageNotFoundError(PageException):
    """Raised when a page is not found"""
    def __init__(self, page_id: int = None, url: str = None):
        message = f"Page not found"
        if page_id:
            message += f" (id={page_id})"
        if url:
            message += f" (url={url})"
        super().__init__(message, 'PAGE_NOT_FOUND', {'page_id': page_id, 'url': url})


class PageNotAccessibleError(PageException):
    """Raised when a page cannot be accessed (HTTP error)"""
    def __init__(self, url: str, status_code: int = None, reason: str = None):
        message = f"Page not accessible: {url}"
        if status_code:
            message += f" (HTTP {status_code})"
        if reason:
            message += f" - {reason}"
        super().__init__(message, 'PAGE_NOT_ACCESSIBLE', {
            'url': url,
            'status_code': status_code,
            'reason': reason
        })


class PageAnalysisError(PageException):
    """Raised when page analysis fails"""
    def __init__(self, message: str, page_id: int = None, url: str = None):
        super().__init__(message, 'PAGE_ANALYSIS_ERROR', {'page_id': page_id, 'url': url})


# API related exceptions
class APIException(SEOAnalyzerException):
    """Base exception for external API errors"""
    pass


class APIQuotaExceededError(APIException):
    """Raised when an API quota is exceeded"""
    def __init__(self, api_name: str, message: str = None):
        msg = message or f"{api_name} API quota exceeded"
        super().__init__(msg, 'API_QUOTA_EXCEEDED', {'api_name': api_name})


class APIConnectionError(APIException):
    """Raised when connection to an API fails"""
    def __init__(self, api_name: str, reason: str = None):
        message = f"Failed to connect to {api_name} API"
        if reason:
            message += f": {reason}"
        super().__init__(message, 'API_CONNECTION_ERROR', {'api_name': api_name, 'reason': reason})


class APIResponseError(APIException):
    """Raised when an API returns an unexpected response"""
    def __init__(self, api_name: str, status_code: int = None, response_body: str = None):
        message = f"Unexpected response from {api_name} API"
        if status_code:
            message += f" (HTTP {status_code})"
        super().__init__(message, 'API_RESPONSE_ERROR', {
            'api_name': api_name,
            'status_code': status_code,
            'response_body': response_body
        })


# Git related exceptions
class GitException(SEOAnalyzerException):
    """Base exception for Git-related errors"""
    pass


class GitNotConfiguredError(GitException):
    """Raised when Git is not configured for a domain"""
    def __init__(self, domain_name: str):
        super().__init__(
            f"Git not configured for domain: {domain_name}",
            'GIT_NOT_CONFIGURED',
            {'domain_name': domain_name}
        )


class GitDeploymentError(GitException):
    """Raised when Git deployment fails"""
    def __init__(self, message: str, domain_name: str = None, commit_hash: str = None):
        super().__init__(message, 'GIT_DEPLOYMENT_ERROR', {
            'domain_name': domain_name,
            'commit_hash': commit_hash
        })


class GitCloneError(GitException):
    """Raised when Git clone fails"""
    def __init__(self, repo_url: str, reason: str = None):
        message = f"Failed to clone repository: {repo_url}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, 'GIT_CLONE_ERROR', {'repo_url': repo_url, 'reason': reason})


class GitPushError(GitException):
    """Raised when Git push fails"""
    def __init__(self, branch: str, reason: str = None):
        message = f"Failed to push to branch: {branch}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, 'GIT_PUSH_ERROR', {'branch': branch, 'reason': reason})


# SEO Issue related exceptions
class SEOIssueException(SEOAnalyzerException):
    """Base exception for SEO issue-related errors"""
    pass


class IssueNotFixableError(SEOIssueException):
    """Raised when an issue cannot be auto-fixed"""
    def __init__(self, issue_id: int, reason: str = None):
        message = f"Issue {issue_id} is not auto-fixable"
        if reason:
            message += f": {reason}"
        super().__init__(message, 'ISSUE_NOT_FIXABLE', {'issue_id': issue_id, 'reason': reason})


class FixGenerationError(SEOIssueException):
    """Raised when generating a fix fails"""
    def __init__(self, issue_id: int, issue_type: str, reason: str = None):
        message = f"Failed to generate fix for issue {issue_id} ({issue_type})"
        if reason:
            message += f": {reason}"
        super().__init__(message, 'FIX_GENERATION_ERROR', {
            'issue_id': issue_id,
            'issue_type': issue_type,
            'reason': reason
        })


# Sitemap related exceptions
class SitemapException(SEOAnalyzerException):
    """Base exception for sitemap-related errors"""
    pass


class SitemapGenerationError(SitemapException):
    """Raised when sitemap generation fails"""
    def __init__(self, message: str, domain_name: str = None):
        super().__init__(message, 'SITEMAP_GENERATION_ERROR', {'domain_name': domain_name})


class SitemapDeploymentError(SitemapException):
    """Raised when sitemap deployment fails"""
    def __init__(self, message: str, method: str = None):
        super().__init__(message, 'SITEMAP_DEPLOYMENT_ERROR', {'method': method})


# Validation exceptions
class ValidationException(SEOAnalyzerException):
    """Base exception for validation errors"""
    pass


class InvalidURLError(ValidationException):
    """Raised when a URL is invalid"""
    def __init__(self, url: str, reason: str = None):
        message = f"Invalid URL: {url}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, 'INVALID_URL', {'url': url, 'reason': reason})


class CircularReferenceError(ValidationException):
    """Raised when a circular reference is detected"""
    def __init__(self, message: str = "Circular reference detected"):
        super().__init__(message, 'CIRCULAR_REFERENCE')
