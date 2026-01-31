"""
Error Handling Utilities
Standardized error handling and logging for API endpoints
"""
import logging
from rest_framework import status
from rest_framework.response import Response


def handle_api_error(logger, operation, error, **context):
    """
    Standardized error handling for API endpoints.

    Args:
        logger: Logger instance for this module
        operation: Description of the operation that failed (e.g., "scan domain")
        error: The exception that was raised
        **context: Additional context (domain_id, page_id, etc.)

    Returns:
        Response: DRF Response object with error details

    Example:
        try:
            domain.scan()
        except Exception as e:
            return handle_api_error(
                logger,
                'scan domain',
                e,
                domain_id=domain.id,
                domain_name=domain.domain_name
            )
    """
    error_msg = str(error)

    # Build log message with context
    log_parts = [f"{operation.capitalize()} failed"]

    # Add context information
    context_parts = []
    if 'domain_id' in context:
        context_parts.append(f"domain_id={context['domain_id']}")
    if 'domain_name' in context:
        context_parts.append(f"domain_name={context['domain_name']}")
    if 'page_id' in context:
        context_parts.append(f"page_id={context['page_id']}")
    if 'group_id' in context:
        context_parts.append(f"group_id={context['group_id']}")

    if context_parts:
        log_parts.append(f"({', '.join(context_parts)})")

    log_parts.append(f": {error_msg}")

    # Log with full traceback
    logger.error(' '.join(log_parts), exc_info=True)

    # Return consistent error response
    response_data = {
        'error': True,
        'message': f'Failed to {operation}: {error_msg}',
        'operation': operation,
    }

    # Include relevant context in response (exclude sensitive data)
    if 'domain_id' in context:
        response_data['domain_id'] = context['domain_id']
    if 'page_id' in context:
        response_data['page_id'] = context['page_id']
    if 'group_id' in context:
        response_data['group_id'] = context['group_id']

    return Response(
        response_data,
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def handle_validation_error(logger, operation, error_details, **context):
    """
    Standardized handling for validation errors.

    Args:
        logger: Logger instance
        operation: Description of the operation
        error_details: Dict or string describing validation errors
        **context: Additional context

    Returns:
        Response: DRF Response with 400 status

    Example:
        if not domain_name:
            return handle_validation_error(
                logger,
                'create domain',
                {'domain_name': 'This field is required'}
            )
    """
    # Log validation error (not as severe as exceptions)
    log_msg = f"Validation error in {operation}"
    if context:
        context_str = ', '.join(f"{k}={v}" for k, v in context.items())
        log_msg += f" ({context_str})"
    log_msg += f": {error_details}"

    logger.warning(log_msg)

    # Return validation error response
    return Response(
        {
            'error': True,
            'message': f'Validation error in {operation}',
            'details': error_details,
            'operation': operation,
        },
        status=status.HTTP_400_BAD_REQUEST
    )


def handle_not_found_error(logger, resource_type, resource_id=None, **context):
    """
    Standardized handling for resource not found errors.

    Args:
        logger: Logger instance
        resource_type: Type of resource (e.g., 'domain', 'page', 'group')
        resource_id: ID of the resource (optional)
        **context: Additional context

    Returns:
        Response: DRF Response with 404 status

    Example:
        domain = Domain.objects.filter(id=domain_id).first()
        if not domain:
            return handle_not_found_error(
                logger,
                'domain',
                resource_id=domain_id
            )
    """
    # Log not found
    log_msg = f"{resource_type.capitalize()} not found"
    if resource_id:
        log_msg += f" (id={resource_id})"
    if context:
        context_str = ', '.join(f"{k}={v}" for k, v in context.items())
        log_msg += f" [{context_str}]"

    logger.info(log_msg)

    # Return not found response
    response_data = {
        'error': True,
        'message': f'{resource_type.capitalize()} not found',
        'resource_type': resource_type,
    }

    if resource_id:
        response_data['resource_id'] = resource_id

    return Response(
        response_data,
        status=status.HTTP_404_NOT_FOUND
    )
