/**
 * useViewportPreservation Hook
 * Preserves ReactFlow viewport position during data refreshes
 */
import { useRef, useCallback, useEffect } from 'react';

/**
 * Hook to preserve viewport position during tree data refreshes
 * @param {Array} triggerDependency - Dependency array that triggers viewport restoration (e.g., nodes)
 * @returns {Object} { reactFlowInstance, isInitialLoad, onInit, onMoveEnd }
 */
const useViewportPreservation = (triggerDependency) => {
  const reactFlowInstance = useRef(null);
  const savedViewport = useRef(null);
  const isInitialLoad = useRef(true);

  // Restore viewport after dependency update
  useEffect(() => {
    if (savedViewport.current && reactFlowInstance.current && !isInitialLoad.current) {
      const viewport = savedViewport.current;
      setTimeout(() => {
        if (reactFlowInstance.current) {
          reactFlowInstance.current.setViewport(viewport, { duration: 0 });
        }
      }, 100);
    }
  }, [triggerDependency]);

  // Save viewport on every move/zoom
  const onMoveEnd = useCallback((event, viewport) => {
    if (!isInitialLoad.current) {
      savedViewport.current = viewport;
    }
  }, []);

  // Handle ReactFlow initialization
  const onInit = useCallback((instance) => {
    reactFlowInstance.current = instance;

    // Fit view on initial load only
    if (isInitialLoad.current) {
      instance.fitView({
        padding: 0.2,
        includeHiddenNodes: false,
        minZoom: 0.1,
        maxZoom: 1.0,
      });

      // Mark initial load as complete
      setTimeout(() => {
        isInitialLoad.current = false;
      }, 500);
    }
  }, []);

  return {
    reactFlowInstance,
    isInitialLoad,
    onInit,
    onMoveEnd,
  };
};

export default useViewportPreservation;
