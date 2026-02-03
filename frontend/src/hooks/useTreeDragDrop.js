/**
 * useTreeDragDrop Hook
 * Handles all drag and drop operations for tree nodes
 */
import { useCallback, useRef } from 'react';
import { pageService } from '../services/domainService';
import useDragStateStore from '../store/dragStateStore';

/**
 * Helper function to find nearest node with depth-level awareness
 *
 * @param {Object} position - Current drag position {x, y}
 * @param {Array} nodes - All nodes in tree
 * @param {string} excludeId - ID of dragged node to exclude
 * @param {number} snapDistance - Maximum snap distance
 * @param {boolean} useDepthPriority - Whether to prioritize depth-level changes
 * @returns {Object|null} Nearest node or null
 */
const findNearestNode = (position, nodes, excludeId, snapDistance, useDepthPriority = true) => {
  const draggedNode = nodes.find(n => n.id === excludeId);
  if (!draggedNode) return null;

  const draggedDepth = draggedNode.data?.depthLevel || 0;

  let nearestSameDepth = null;
  let minDistanceSameDepth = snapDistance;

  let nearestDifferentDepth = null;
  let minDistanceDifferentDepth = snapDistance;

  nodes.forEach((node) => {
    if (node.id === excludeId) return;

    const dx = position.x - node.position.x;
    const dy = position.y - node.position.y;
    const distance = Math.sqrt(dx * dx + dy * dy);

    if (distance > snapDistance) return; // Skip if too far

    const nodeDepth = node.data?.depthLevel || 0;
    const isDifferentDepth = nodeDepth !== draggedDepth;

    if (isDifferentDepth) {
      if (distance < minDistanceDifferentDepth) {
        minDistanceDifferentDepth = distance;
        nearestDifferentDepth = node;
      }
    } else {
      if (distance < minDistanceSameDepth) {
        minDistanceSameDepth = distance;
        nearestSameDepth = node;
      }
    }
  });

  // Priority logic: Prioritize depth-change connections
  if (useDepthPriority && nearestDifferentDepth) {
    return nearestDifferentDepth;
  }

  // Otherwise, return nearest node regardless of depth
  return nearestDifferentDepth || nearestSameDepth;
};

/**
 * Hook for managing tree node drag and drop
 *
 * @param {Object} options - Configuration options
 * @returns {Object} Drag handlers and state
 */
const useTreeDragDrop = ({
  editMode,
  autoConnectEnabled,
  snapDistance,
  nodes,
  edges,
  setNodes,
  setEdges,
  setDraggedPositions,
  setHasUnsavedChanges,
  setHighlightedNode,
  saveToHistory,
  refreshTreeData,
}) => {
  const dragNodeRef = useRef(null);
  const dragStartPosRef = useRef(null);
  const { setIsDragging, resetDragState } = useDragStateStore();

  // Handle node drag start
  const onNodeDragStart = useCallback(
    (event, node) => {
      if (!editMode) return;

      setIsDragging(true, node.id);
      dragNodeRef.current = node;
      dragStartPosRef.current = { ...node.position };
    },
    [editMode, setIsDragging]
  );

  // Handle node drag (show snap preview)
  const onNodeDrag = useCallback(
    (event, node) => {
      if (!editMode || !autoConnectEnabled) return;

      const nearest = findNearestNode(
        node.position,
        nodes,
        node.id,
        snapDistance,
        autoConnectEnabled // Use depth priority when auto-connect enabled
      );

      if (nearest) {
        setHighlightedNode(nearest.id);
      } else {
        setHighlightedNode(null);
      }
    },
    [editMode, autoConnectEnabled, nodes, snapDistance, setHighlightedNode]
  );

  // Handle node drag stop (auto-connect if near another node)
  const onNodeDragStop = useCallback(
    async (event, node) => {
      if (!editMode) return;

      setHighlightedNode(null);
      resetDragState(); // Reset drag state BEFORE auto-connect prompt

      // Update position
      setDraggedPositions((prev) => ({
        ...prev,
        [node.id]: { x: node.position.x, y: node.position.y },
      }));
      setHasUnsavedChanges(true);

      // Update local state immediately (optimistic UI)
      setNodes((nds) =>
        nds.map((n) => (n.id === node.id ? { ...n, position: node.position } : n))
      );

      // Auto-connect if enabled and near another node
      if (autoConnectEnabled) {
        const nearest = findNearestNode(
          node.position,
          nodes,
          node.id,
          snapDistance,
          autoConnectEnabled // Use depth priority when auto-connect enabled
        );

        if (nearest) {
          try {
            // Find old parent from current edges
            const oldParentEdge = edges.find((e) => e.target === node.id);
            const oldParentId = oldParentEdge
              ? Number(oldParentEdge.source)
              : null;

            // Skip if trying to connect to same parent
            if (oldParentId === Number(nearest.id)) {
              return;
            }

            // Update backend first
            await pageService.changeParent(
              Number(node.id),
              Number(nearest.id)
            );

            // Save to history
            saveToHistory({
              type: 'reparent',
              pageId: Number(node.id),
              oldParentId: oldParentId,
              newParentId: Number(nearest.id),
            });

            // Refresh tree to get proper layout with new hierarchy
            await refreshTreeData();
          } catch (error) {
            console.error('Failed to auto-connect:', error);
            alert(
              '이동 실패: ' +
                (error.response?.data?.error || error.message)
            );
            // On error, refresh to get correct state from backend
            await refreshTreeData();
          }
        }
      }
    },
    [
      editMode,
      autoConnectEnabled,
      nodes,
      edges,
      snapDistance,
      setNodes,
      setEdges,
      setDraggedPositions,
      setHasUnsavedChanges,
      setHighlightedNode,
      saveToHistory,
      refreshTreeData,
      resetDragState,
    ]
  );

  return {
    onNodeDragStart,
    onNodeDrag,
    onNodeDragStop,
    dragNodeRef,
    dragStartPosRef,
  };
};

export default useTreeDragDrop;
