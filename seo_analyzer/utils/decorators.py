"""
Utility decorators for views and services.
"""

import logging
import functools
from rest_framework.response import Response
from rest_framework import status
from .error_handlers import handle_api_error


def handle_viewset_errors(operation_name=None):
    """
    Decorator to handle errors consistently in ViewSet methods.

    Catches exceptions and returns standardized error responses using
    the handle_api_error utility function.

    Args:
        operation_name: Optional name of the operation for logging.
                       If not provided, uses the function name.

    Usage:
        @action(detail=True, methods=['post'])
        @handle_viewset_errors('scan')
        def scan(self, request, pk=None):
            # Your code here
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Get logger from viewset or create new one
            logger_instance = getattr(self, 'logger', logging.getLogger(__name__))

            # Use provided operation name or function name
            op_name = operation_name or func.__name__

            try:
                return func(self, request, *args, **kwargs)

            except Exception as e:
                # Build context for error handler
                context = {
                    'operation': op_name,
                    'viewset': self.__class__.__name__,
                    'method': request.method if hasattr(request, 'method') else None,
                }

                # Add request data if available (for debugging)
                if hasattr(request, 'data') and request.data:
                    context['request_data_keys'] = list(request.data.keys())

                # Add query params if available
                if hasattr(request, 'query_params') and request.query_params:
                    context['query_params'] = dict(request.query_params)

                return handle_api_error(logger_instance, op_name, e, **context)

        return wrapper
    return decorator


def transaction_atomic(func):
    """
    Decorator to wrap function in Django transaction.

    This is a convenience wrapper around Django's transaction.atomic
    that can be used as a decorator.

    Usage:
        @action(detail=False, methods=['post'])
        @transaction_atomic
        def bulk_update(self, request):
            # Your code here - will be wrapped in transaction
            pass
    """
    from django.db import transaction

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with transaction.atomic():
            return func(*args, **kwargs)
    return wrapper


def require_parameters(*param_names, source='data'):
    """
    Decorator to validate required parameters in request.

    Args:
        *param_names: Names of required parameters
        source: Where to look for parameters ('data', 'query_params', or 'both')

    Returns:
        400 Bad Request if any required parameter is missing

    Usage:
        @action(detail=False, methods=['post'])
        @require_parameters('domain', 'category')
        def some_action(self, request):
            # domain and category are guaranteed to exist in request.data
            pass

        @action(detail=False, methods=['get'])
        @require_parameters('page_id', source='query_params')
        def another_action(self, request):
            # page_id is guaranteed to exist in request.query_params
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, request, *args, **kwargs):
            missing = []

            if source in ('data', 'both'):
                if hasattr(request, 'data'):
                    for param in param_names:
                        if param not in request.data or request.data[param] is None:
                            missing.append(f"{param} (in body)")

            if source in ('query_params', 'both'):
                if hasattr(request, 'query_params'):
                    for param in param_names:
                        if param not in request.query_params or request.query_params[param] is None:
                            missing.append(f"{param} (in query params)")

            if missing:
                return Response(
                    {
                        'error': 'Missing required parameters',
                        'missing': missing
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            return func(self, request, *args, **kwargs)

        return wrapper
    return decorator


def rate_limit(max_calls=60, period_seconds=60):
    """
    Simple rate limiting decorator.

    Note: This is a placeholder. For production, use Django rate limiting
    packages like django-ratelimit or DRF throttling.

    Args:
        max_calls: Maximum number of calls allowed
        period_seconds: Time period in seconds

    Usage:
        @action(detail=True, methods=['post'])
        @rate_limit(max_calls=10, period_seconds=60)
        def expensive_operation(self, request, pk=None):
            pass
    """
    import time
    from collections import defaultdict, deque

    call_history = defaultdict(deque)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Get user identifier (IP or user ID)
            user_id = request.user.id if request.user.is_authenticated else request.META.get('REMOTE_ADDR')

            now = time.time()
            history = call_history[user_id]

            # Remove old calls outside the time window
            while history and history[0] < now - period_seconds:
                history.popleft()

            # Check if limit exceeded
            if len(history) >= max_calls:
                return Response(
                    {
                        'error': 'Rate limit exceeded',
                        'max_calls': max_calls,
                        'period_seconds': period_seconds,
                        'retry_after': int(history[0] + period_seconds - now)
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

            # Record this call
            history.append(now)

            return func(self, request, *args, **kwargs)

        return wrapper
    return decorator
