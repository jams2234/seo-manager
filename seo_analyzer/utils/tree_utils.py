"""
Tree Structure Utilities
Helper functions for tree-based operations
"""


def is_descendant(ancestor, potential_descendant):
    """
    Check if potential_descendant is in ancestor's subtree.
    Prevents circular references in tree structures.

    Args:
        ancestor: The potential ancestor node (Page object)
        potential_descendant: The node to check (Page object)

    Returns:
        bool: True if potential_descendant is a descendant of ancestor

    Example:
        >>> root = Page.objects.get(path='/')
        >>> child = Page.objects.get(path='/about')
        >>> is_descendant(root, child)
        True
    """
    current = potential_descendant
    visited = set()  # Prevent infinite loops in case of data corruption

    while current:
        # Detect circular reference
        if current.id in visited:
            return False

        # Found the ancestor
        if current.id == ancestor.id:
            return True

        # Track visited nodes
        visited.add(current.id)

        # Move up the tree
        current = current.parent_page

    return False
