"""
Tree Layout Service

Calculates positions for tree structure visualization.
Uses bottom-up approach to position nodes without overlap.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


@dataclass
class LayoutConfig:
    """Configuration for tree layout calculation"""
    node_width: int = 320
    node_height: int = 300
    horizontal_spacing: int = 100
    vertical_spacing: int = 250
    min_x_offset: int = 50


class TreeLayoutService:
    """
    Service for calculating tree layout positions.

    Provides methods to calculate optimal positions for nodes in a tree structure
    with support for manual positioning and automatic centering.
    """

    def __init__(self, config: Optional[LayoutConfig] = None):
        """
        Initialize TreeLayoutService

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or LayoutConfig()

    def calculate_positions(self, pages: List) -> Dict[int, Dict[str, float]]:
        """
        Calculate positions for all pages in the tree.

        Uses a bottom-up approach:
        1. Group pages by depth level
        2. Position siblings at each level
        3. Center parents above their children
        4. Apply manual positions where specified
        5. Center entire tree

        Args:
            pages: List of Page objects with depth_level and parent_page

        Returns:
            Dictionary mapping page_id to {'x': float, 'y': float}
        """
        if not pages:
            return {}

        # Group pages by depth level
        levels = self._group_by_depth(pages)
        page_dict = {page.id: page for page in pages}

        # Initialize positions dict
        positions = {}

        # Apply manual positions first
        self._apply_manual_positions(pages, positions)

        # Calculate automatic positions
        self._calculate_automatic_positions(levels, page_dict, positions)

        # Center the entire tree
        self._center_tree(positions)

        return positions

    def _group_by_depth(self, pages: List) -> Dict[int, List]:
        """
        Group pages by their depth level.

        Args:
            pages: List of Page objects

        Returns:
            Dictionary mapping depth_level to list of pages
        """
        levels = {}
        for page in pages:
            depth = page.depth_level or 0
            if depth not in levels:
                levels[depth] = []
            levels[depth].append(page)
        return levels

    def _apply_manual_positions(self, pages: List, positions: Dict[int, Dict[str, float]]):
        """
        Apply manual positions for pages that have them set.

        Args:
            pages: List of Page objects
            positions: Dictionary to populate with positions (mutated)
        """
        for page in pages:
            if page.use_manual_position and page.manual_position_x is not None:
                positions[page.id] = {
                    'x': page.manual_position_x,
                    'y': page.manual_position_y
                }

    def _calculate_automatic_positions(
        self,
        levels: Dict[int, List],
        page_dict: Dict[int, any],
        positions: Dict[int, Dict[str, float]]
    ):
        """
        Calculate automatic positions for pages without manual positions.

        Processes levels from deepest to shallowest, positioning siblings
        and centering parents above their children.

        Args:
            levels: Pages grouped by depth level
            page_dict: Dictionary mapping page_id to Page object
            positions: Dictionary to populate with positions (mutated)
        """
        level_x_offsets = {}  # Track next available x position for each level

        # Process from deepest to shallowest
        max_depth = max(levels.keys()) if levels else 0

        for depth in range(max_depth, -1, -1):
            level_pages = levels.get(depth, [])

            # Group pages by parent
            parent_groups = self._group_by_parent(level_pages)

            # Position each group
            current_x = level_x_offsets.get(depth, 0)

            for parent_id, siblings in parent_groups.items():
                current_x = self._position_sibling_group(
                    siblings,
                    parent_id,
                    page_dict,
                    depth,
                    current_x,
                    positions
                )

                # Update next available x for this level
                level_x_offsets[depth] = current_x

    def _group_by_parent(self, pages: List) -> Dict[Optional[int], List]:
        """
        Group pages by their parent page ID.

        Args:
            pages: List of Page objects

        Returns:
            Dictionary mapping parent_id to list of children
        """
        parent_groups = {}
        for page in pages:
            parent_id = page.parent_page.id if page.parent_page else None
            if parent_id not in parent_groups:
                parent_groups[parent_id] = []
            parent_groups[parent_id].append(page)
        return parent_groups

    def _position_sibling_group(
        self,
        siblings: List,
        parent_id: Optional[int],
        page_dict: Dict[int, any],
        depth: int,
        start_x: float,
        positions: Dict[int, Dict[str, float]]
    ) -> float:
        """
        Position a group of sibling pages and center their parent.

        Args:
            siblings: List of sibling Page objects
            parent_id: ID of parent page (None for root nodes)
            page_dict: Dictionary mapping page_id to Page object
            depth: Current depth level
            start_x: Starting x position for this group
            positions: Dictionary to populate with positions (mutated)

        Returns:
            Next available x position after this group
        """
        sibling_x = start_x
        sibling_positions = []

        # Position siblings
        for sibling in siblings:
            if sibling.id not in positions:
                # Calculate position for this sibling
                positions[sibling.id] = {
                    'x': sibling_x,
                    'y': depth * self.config.vertical_spacing
                }
                sibling_positions.append(sibling_x)
                sibling_x += self.config.node_width + self.config.horizontal_spacing
            else:
                # Manual position exists, track it for parent centering
                sibling_positions.append(positions[sibling.id]['x'])

        # Center parent above siblings
        if parent_id and parent_id in page_dict and sibling_positions:
            self._center_parent(parent_id, sibling_positions, depth, positions)

        # Add spacing after group
        next_x = sibling_x + self.config.horizontal_spacing

        return next_x

    def _center_parent(
        self,
        parent_id: int,
        sibling_positions: List[float],
        depth: int,
        positions: Dict[int, Dict[str, float]]
    ):
        """
        Center a parent node above its children.

        Args:
            parent_id: ID of parent page
            sibling_positions: List of x positions of children
            depth: Depth of children (parent is at depth-1)
            positions: Dictionary to populate with positions (mutated)
        """
        if parent_id not in positions and sibling_positions:
            # Calculate center of siblings
            min_x = min(sibling_positions)
            max_x = max(sibling_positions)
            parent_x = (min_x + max_x) / 2

            # Set parent position
            positions[parent_id] = {
                'x': parent_x,
                'y': (depth - 1) * self.config.vertical_spacing
            }

    def _center_tree(self, positions: Dict[int, Dict[str, float]]):
        """
        Center the entire tree by shifting all nodes.

        Ensures minimum x position is at least config.min_x_offset.

        Args:
            positions: Dictionary of positions (mutated)
        """
        if not positions:
            return

        # Find minimum x
        min_x = min(pos['x'] for pos in positions.values())

        # Calculate offset needed
        offset_x = self.config.min_x_offset - min_x if min_x < self.config.min_x_offset else 0

        # Apply offset to all positions
        if offset_x > 0:
            for page_id in positions:
                positions[page_id]['x'] += offset_x

    def get_layout_bounds(self, positions: Dict[int, Dict[str, float]]) -> Tuple[float, float, float, float]:
        """
        Calculate bounding box for the tree layout.

        Args:
            positions: Dictionary of positions

        Returns:
            Tuple of (min_x, min_y, max_x, max_y)
        """
        if not positions:
            return (0, 0, 0, 0)

        x_values = [pos['x'] for pos in positions.values()]
        y_values = [pos['y'] for pos in positions.values()]

        return (
            min(x_values),
            min(y_values),
            max(x_values) + self.config.node_width,
            max(y_values) + self.config.node_height
        )
