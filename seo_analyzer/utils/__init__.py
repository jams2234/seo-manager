"""
SEO Analyzer Utilities
"""
from .tree_utils import is_descendant
from .error_handlers import (
    handle_api_error,
    handle_validation_error,
    handle_not_found_error,
)
from .url_utils import (
    normalize_url,
    urls_match,
    get_url_path,
    get_url_domain,
)

__all__ = [
    'is_descendant',
    'handle_api_error',
    'handle_validation_error',
    'handle_not_found_error',
    'normalize_url',
    'urls_match',
    'get_url_path',
    'get_url_domain',
]
