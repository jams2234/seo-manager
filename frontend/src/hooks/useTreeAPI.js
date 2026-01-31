/**
 * useTreeAPI Hook
 * Consolidates all API operations for tree management with unified error handling
 */
import { useCallback, useState } from 'react';
import { pageService } from '../services/domainService';

/**
 * Hook for managing tree API operations
 *
 * @param {Object} options - Configuration options
 * @returns {Object} API methods and loading state
 */
const useTreeAPI = ({
  domainId,
  fetchDomainWithTree,
  setDraggedPositions,
  setHasUnsavedChanges,
}) => {
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Refresh tree data from backend
  const refreshTreeData = useCallback(async () => {
    if (!domainId || isRefreshing) return;

    try {
      setIsRefreshing(true);
      await fetchDomainWithTree(domainId);
    } catch (error) {
      console.error('Failed to refresh tree:', error);
      throw new Error('트리 새로고침 실패: ' + error.message);
    } finally {
      setIsRefreshing(false);
    }
  }, [domainId, isRefreshing, fetchDomainWithTree]);

  // Save positions to backend
  const savePositions = useCallback(async (draggedPositions) => {
    const updates = Object.entries(draggedPositions).map(([id, pos]) => ({
      id: Number(id),
      x: pos.x,
      y: pos.y,
    }));

    try {
      await pageService.bulkUpdatePositions(updates);
      setHasUnsavedChanges(false);
      setDraggedPositions({});
      alert('위치가 성공적으로 저장되었습니다!');
    } catch (error) {
      console.error('Failed to save positions:', error);
      throw new Error('위치 저장에 실패했습니다: ' + error.message);
    }
  }, [setDraggedPositions, setHasUnsavedChanges]);

  // Cancel changes and refresh
  const cancelChanges = useCallback(async () => {
    setDraggedPositions({});
    setHasUnsavedChanges(false);
    await refreshTreeData();
  }, [setDraggedPositions, setHasUnsavedChanges, refreshTreeData]);

  // Change parent for a single page
  const changeParent = useCallback(async (pageId, newParentId, oldParentId = null) => {
    try {
      await pageService.changeParent(pageId, newParentId);
      await refreshTreeData();
      return { success: true, oldParentId };
    } catch (error) {
      console.error('Failed to change parent:', error);
      throw new Error(
        '부모 변경 실패: ' + (error.response?.data?.error || error.message)
      );
    }
  }, [refreshTreeData]);

  // Bulk reparent (for edge deletion or bulk operations)
  const bulkReparent = useCallback(async (changes) => {
    try {
      const response = await pageService.bulkReparent(changes);
      await refreshTreeData();
      return response.data;
    } catch (error) {
      console.error('Failed to bulk reparent:', error);
      throw new Error(
        '일괄 부모 변경 실패: ' + (error.response?.data?.error || error.message)
      );
    }
  }, [refreshTreeData]);

  // Execute undo action
  const executeUndo = useCallback(async (action, setEdgesCallback = null) => {
    try {
      if (action.type === 'reparent') {
        // Update backend
        await pageService.changeParent(action.pageId, action.oldParentId);

        // Optimistically update local edges if callback provided
        if (setEdgesCallback) {
          setEdgesCallback((eds) => {
            // Remove current parent edge
            const filteredEdges = eds.filter((e) => e.target !== String(action.pageId));
            // Add old parent edge back (if oldParentId exists)
            if (action.oldParentId) {
              const newEdge = {
                id: `e${action.oldParentId}-${action.pageId}`,
                source: String(action.oldParentId),
                target: String(action.pageId),
                type: 'smoothstep',
              };
              return [...filteredEdges, newEdge];
            }
            return filteredEdges;
          });
          console.log('✅ Undo successful - UI updated without refresh');
        } else {
          // No callback provided, use refresh
          await refreshTreeData();
        }
      } else if (action.type === 'bulk_reparent') {
        const undoChanges = action.changes.map((change) => ({
          page_id: change.page_id,
          parent_id: change.old_parent_id || null,
        }));
        await pageService.bulkReparent(undoChanges);
        // For bulk operations, always refresh to ensure consistency
        await refreshTreeData();
      }
    } catch (error) {
      console.error('Undo failed:', error);
      throw new Error('실행 취소 실패: ' + error.message);
    }
  }, [refreshTreeData]);

  // Execute redo action
  const executeRedo = useCallback(async (action, setEdgesCallback = null) => {
    try {
      if (action.type === 'reparent') {
        // Update backend
        await pageService.changeParent(action.pageId, action.newParentId);

        // Optimistically update local edges if callback provided
        if (setEdgesCallback) {
          setEdgesCallback((eds) => {
            // Remove current parent edge
            const filteredEdges = eds.filter((e) => e.target !== String(action.pageId));
            // Add new parent edge
            const newEdge = {
              id: `e${action.newParentId}-${action.pageId}`,
              source: String(action.newParentId),
              target: String(action.pageId),
              type: 'smoothstep',
            };
            return [...filteredEdges, newEdge];
          });
          console.log('✅ Redo successful - UI updated without refresh');
        } else {
          // No callback provided, use refresh
          await refreshTreeData();
        }
      } else if (action.type === 'bulk_reparent') {
        await pageService.bulkReparent(action.changes);
        // For bulk operations, always refresh to ensure consistency
        await refreshTreeData();
      }
    } catch (error) {
      console.error('Redo failed:', error);
      throw new Error('다시 실행 실패: ' + error.message);
    }
  }, [refreshTreeData]);

  return {
    refreshTreeData,
    savePositions,
    cancelChanges,
    changeParent,
    bulkReparent,
    executeUndo,
    executeRedo,
    isRefreshing,
  };
};

export default useTreeAPI;
