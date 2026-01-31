import { create } from 'zustand';

const useDragStateStore = create((set) => ({
  isDragging: false,
  draggedNodeId: null,

  setIsDragging: (isDragging, nodeId = null) => set({
    isDragging,
    draggedNodeId: nodeId
  }),

  resetDragState: () => set({
    isDragging: false,
    draggedNodeId: null
  }),
}));

export default useDragStateStore;
