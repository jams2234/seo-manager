"""
Utilities for managing display order of model instances.
"""

from typing import List, Any
from django.db.models import QuerySet


def update_display_order(
    queryset: QuerySet,
    order_field: str = 'order',
    increment: int = 10,
    batch_size: int = 100
) -> int:
    """
    Update display order for a queryset of objects.

    Assigns sequential order values (10, 20, 30, ...) to objects in the queryset.
    Only updates objects whose current order differs from the calculated value.

    Args:
        queryset: QuerySet of objects to reorder. Should already be ordered
                 as desired (e.g., .order_by('-page_count', 'name'))
        order_field: Name of the field to update (default: 'order')
        increment: Increment between order values (default: 10)
                  This allows inserting items between existing ones later
        batch_size: Batch size for bulk_update (default: 100)

    Returns:
        Number of objects updated

    Usage:
        # Reorder categories by page count
        categories = PageGroupCategory.objects.filter(
            domain_id=domain_id
        ).annotate(
            page_count=Count('groups__pages')
        ).order_by('-page_count', 'name')

        updated = update_display_order(categories)
    """
    if not queryset:
        return 0

    items_to_update = []

    for idx, item in enumerate(queryset):
        new_order = (idx + 1) * increment

        # Get current order value
        current_order = getattr(item, order_field)

        # Only update if different
        if current_order != new_order:
            setattr(item, order_field, new_order)
            items_to_update.append(item)

    # Bulk update if any changes
    if items_to_update:
        model_class = queryset.model
        model_class.objects.bulk_update(
            items_to_update,
            [order_field],
            batch_size=batch_size
        )

    return len(items_to_update)


def reorder_by_field(
    queryset: QuerySet,
    sort_fields: List[str],
    order_field: str = 'order',
    increment: int = 10
) -> int:
    """
    Reorder objects by specified sort fields and update order field.

    Convenience function that combines ordering and update in one call.

    Args:
        queryset: QuerySet to reorder
        sort_fields: Fields to sort by (e.g., ['-page_count', 'name'])
        order_field: Field to update with new order
        increment: Increment between order values

    Returns:
        Number of objects updated

    Usage:
        # Reorder groups by page count descending, then name ascending
        groups = PageGroup.objects.filter(category_id=category_id)
        updated = reorder_by_field(
            groups,
            sort_fields=['-page_count', 'name']
        )
    """
    # Apply sorting
    ordered_queryset = queryset.order_by(*sort_fields)

    # Update order
    return update_display_order(
        ordered_queryset,
        order_field=order_field,
        increment=increment
    )


def insert_at_position(
    instance: Any,
    position: int,
    queryset: QuerySet,
    order_field: str = 'order',
    increment: int = 10
) -> None:
    """
    Insert an instance at a specific position and reorder others.

    Args:
        instance: Object to insert
        position: Desired position (0-indexed)
        queryset: QuerySet of sibling objects
        order_field: Field name for ordering
        increment: Increment between order values

    Usage:
        # Insert category at position 2
        insert_at_position(
            new_category,
            position=2,
            queryset=PageGroupCategory.objects.filter(domain=domain)
        )
    """
    # Get all items in order
    items = list(queryset.order_by(order_field))

    # Insert at position
    items.insert(position, instance)

    # Update all order values
    for idx, item in enumerate(items):
        new_order = (idx + 1) * increment
        setattr(item, order_field, new_order)

    # Bulk update
    model_class = queryset.model
    model_class.objects.bulk_update(
        items,
        [order_field],
        batch_size=100
    )


def swap_order(
    instance1: Any,
    instance2: Any,
    order_field: str = 'order'
) -> None:
    """
    Swap the order of two instances.

    Args:
        instance1: First object
        instance2: Second object
        order_field: Field name for ordering

    Usage:
        swap_order(category_a, category_b)
    """
    order1 = getattr(instance1, order_field)
    order2 = getattr(instance2, order_field)

    setattr(instance1, order_field, order2)
    setattr(instance2, order_field, order1)

    # Save both
    instance1.save(update_fields=[order_field])
    instance2.save(update_fields=[order_field])


def get_next_order(
    queryset: QuerySet,
    order_field: str = 'order',
    increment: int = 10
) -> int:
    """
    Get the next order value for a new item.

    Args:
        queryset: QuerySet of existing items
        order_field: Field name for ordering
        increment: Increment to add

    Returns:
        Next available order value

    Usage:
        new_category.order = get_next_order(
            PageGroupCategory.objects.filter(domain=domain)
        )
    """
    max_order = queryset.aggregate(
        max_value=models.Max(order_field)
    )['max_value']

    if max_order is None:
        return increment

    return max_order + increment


# Import models for type hints
from django.db import models
