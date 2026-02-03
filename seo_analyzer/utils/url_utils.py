"""
URL Utilities for SEO Analyzer
Common URL normalization and comparison functions.
"""
from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    """
    Normalize URL for comparison.

    - Removes trailing slash
    - Lowercases scheme and netloc
    - Removes www. prefix

    Args:
        url: URL string to normalize

    Returns:
        Normalized URL string
    """
    if not url:
        return url

    try:
        parsed = urlparse(url)

        # Lowercase scheme and netloc
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Remove www. prefix
        if netloc.startswith('www.'):
            netloc = netloc[4:]

        # Remove trailing slash from path
        path = parsed.path.rstrip('/')

        # Reconstruct normalized URL (without query string for comparison)
        normalized = f"{scheme}://{netloc}{path}"
        return normalized

    except Exception:
        # If parsing fails, just strip trailing slash
        return url.rstrip('/')


def urls_match(url1: str, url2: str) -> bool:
    """
    Check if two URLs match after normalization.

    Args:
        url1: First URL
        url2: Second URL

    Returns:
        True if URLs match, False otherwise
    """
    return normalize_url(url1) == normalize_url(url2)


def get_url_path(url: str) -> str:
    """
    Extract path from URL.

    Args:
        url: Full URL string

    Returns:
        Path component of URL (e.g., '/about/team')
    """
    if not url:
        return ''

    try:
        parsed = urlparse(url)
        return parsed.path or '/'
    except Exception:
        return url


def get_url_domain(url: str) -> str:
    """
    Extract domain from URL.

    Args:
        url: Full URL string

    Returns:
        Domain (netloc) component of URL
    """
    if not url:
        return ''

    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        # Remove www. prefix
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ''
