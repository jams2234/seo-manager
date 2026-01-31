/**
 * useTreeLayout Hook
 * Applies automatic or manual layout to nodes and edges
 */
import { useMemo } from 'react';

/**
 * Apply layout to nodes and edges
 *
 * @param {Array} nodes - Styled nodes
 * @param {Array} edges - Styled edges
 * @param {boolean} useAutoLayout - Whether to use automatic layout
 * @param {string} layoutDirection - Layout direction ('TB' or 'LR')
 * @param {Function} getLayoutedElements - Dagre layout function
 * @param {Array} rawNodes - Original nodes from backend (to check manual positions)
 * @returns {Object} { nodes, edges } with layout applied
 */
const useTreeLayout = (
  nodes,
  edges,
  useAutoLayout,
  layoutDirection,
  getLayoutedElements,
  rawNodes
) => {
  return useMemo(() => {
    if (!nodes || nodes.length === 0) {
      return { nodes: [], edges: [] };
    }

    // Apply auto-layout if enabled
    if (useAutoLayout) {
      const layouted = getLayoutedElements(nodes, edges, layoutDirection);
      return { nodes: layouted.nodes, edges: layouted.edges };
    }

    // Manual layout mode
    // Check if any node has manual position set
    const hasAnyManualPosition = nodes.some((n) => {
      const originalNode = rawNodes?.find((tn) => String(tn.id) === n.id);
      return (
        originalNode &&
        originalNode.use_manual_position &&
        originalNode.manual_position_x !== null &&
        originalNode.manual_position_y !== null
      );
    });

    // If no manual positions exist, fall back to auto-layout
    if (!hasAnyManualPosition) {
      const layouted = getLayoutedElements(nodes, edges, layoutDirection);
      return { nodes: layouted.nodes, edges: layouted.edges };
    }

    // Filter edges to only include those with both source and target visible
    const nodeIds = new Set(nodes.map((n) => n.id));
    const filteredEdges = edges.filter(
      (edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target)
    );

    return { nodes, edges: filteredEdges };
  }, [nodes, edges, useAutoLayout, layoutDirection, getLayoutedElements, rawNodes]);
};

export default useTreeLayout;
