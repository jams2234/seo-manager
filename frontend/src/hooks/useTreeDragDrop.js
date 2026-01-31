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
    console.log('🎯 Depth-based auto-connect:', {
      draggedDepth,
      targetDepth: nearestDifferentDepth.data?.depthLevel,
      targetNode: nearestDifferentDepth.data?.label,
      distanceDifferent: minDistanceDifferentDepth,
      distanceSame: minDistanceSameDepth
    });
    return nearestDifferentDepth;
  }

  // Otherwise, return nearest node regardless of depth
  const result = nearestDifferentDepth || nearestSameDepth;
  if (result) {
    console.log('🎯 Distance-based auto-connect:', {
      draggedDepth,
      targetDepth: result.data?.depthLevel,
      targetNode: result.data?.label
    });
  }
  return result;
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
          const draggedDepth = node.data?.depthLevel || 0;
          const targetDepth = nearest.data?.depthLevel || 0;
          const depthChange = draggedDepth !== targetDepth;

          const message = depthChange
            ? `${node.data.label}을(를) ${nearest.data.label}의 하위로 연결하시겠습니까?\n(심도: L${draggedDepth} → L${targetDepth + 1})`
            : `${node.data.label}을(를) ${nearest.data.label}의 하위로 연결하시겠습니까?`;

          const confirmed = window.confirm(message);

          if (confirmed) {
            try {
              // Find old parent from current edges
              const oldParentEdge = edges.find((e) => e.target === node.id);
              const oldParentId = oldParentEdge
                ? Number(oldParentEdge.source)
                : null;

              // Update backend
              await pageService.changeParent(
                Number(node.id),
                Number(nearest.id)
              );

              // Optimistically update local edges (remove old edge, add new edge)
              setEdges((eds) => {
                // Remove old parent edge
                const filteredEdges = eds.filter((e) => e.target !== node.id);
                // Add new parent edge
                const newEdge = {
                  id: `e${nearest.id}-${node.id}`,
                  source: nearest.id,
                  target: node.id,
                  type: 'smoothstep',
                };
                return [...filteredEdges, newEdge];
              });

              // Update node depth level optimistically
              setNodes((nds) =>
                nds.map((n) => {
                  if (n.id === node.id) {
                    return {
                      ...n,
                      data: {
                        ...n.data,
                        depthLevel: (nearest.data?.depthLevel || 0) + 1,
                      },
                    };
                  }
                  return n;
                })
              );

              // Save to history
              const historyAction = {
                type: 'reparent',
                pageId: Number(node.id),
                oldParentId: oldParentId,
                newParentId: Number(nearest.id),
              };
              console.log('💾 Saving to history:', historyAction);
              saveToHistory(historyAction);

              console.log('✅ Auto-connect successful - UI updated without refresh');
            } catch (error) {
              console.error('Failed to auto-connect:', error);
              alert(
                '자동 연결 실패: ' +
                  (error.response?.data?.error || error.message)
              );
              // On error, refresh to get correct state from backend
              await refreshTreeData();
            }
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
