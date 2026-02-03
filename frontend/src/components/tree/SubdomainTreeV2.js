/**
 * Subdomain Tree V2 Component
 * Advanced tree editor with auto-connect, undo/redo, and extensive customization
 */
import React, { useCallback, useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
} from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';
import CustomNode from './CustomNode';
import LoadingOverlay from './LoadingOverlay';
import NodeDetailPanel from './NodeDetailPanel';
import SEOIssuesPanel from '../seo/SEOIssuesPanel';
import useDomainStore from '../../store/domainStore';
import useTreePreferencesStore from '../../store/treePreferencesStore';
import useTreeHistoryStore from '../../store/treeHistoryStore';
import useTreeFiltering from '../../hooks/useTreeFiltering';
import useNodeStyling from '../../hooks/useNodeStyling';
import useEdgeStyling from '../../hooks/useEdgeStyling';
import useTreeLayout from '../../hooks/useTreeLayout';
import useTreeAPI from '../../hooks/useTreeAPI';
import useTreeDragDrop from '../../hooks/useTreeDragDrop';
import useViewportPreservation from '../../hooks/useViewportPreservation';
import { NODE_LAYOUT, INTERACTION, VIEWPORT, DEFAULT_DIRECTION } from '../../constants/treeConfig';
import './SubdomainTree.css';

// Define nodeTypes outside component to prevent recreation on each render
const nodeTypes = {
  custom: CustomNode,
};

// Dagre layout configuration
const getLayoutedElements = (nodes, edges, direction = DEFAULT_DIRECTION) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const nodeWidth = NODE_LAYOUT.WIDTH;
  const nodeHeight = NODE_LAYOUT.HEIGHT;

  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: NODE_LAYOUT.NODE_SEPARATION,
    ranksep: NODE_LAYOUT.RANK_SEPARATION,
    marginx: NODE_LAYOUT.MARGIN_X,
    marginy: NODE_LAYOUT.MARGIN_Y,
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };
  });

  return { nodes, edges };
};

const SubdomainTreeV2 = ({
  treeData,
  onNodeClick,
  selectedPageId,
  domainId,
  // Optional props from wrapper component
  setHasUnsavedChanges: setHasUnsavedChangesExternal,
  draggedPositions: draggedPositionsExternal,
  setDraggedPositions: setDraggedPositionsExternal,
  refreshTreeData: refreshTreeDataExternal,
  dataRefreshKey = 0,
  activeGroupFilter = null,
}) => {
  // Get fetchDomainWithTree from store for refreshing
  const { fetchDomainWithTree } = useDomainStore();

  // Tree preferences from Zustand store (auto-persisted to localStorage)
  const {
    editMode,
    setEditMode,
    useAutoLayout,
    setUseAutoLayout,
    layoutDirection,
    setLayoutDirection,
    filterMode,
    setFilterMode,
    showHiddenNodes,
    setShowHiddenNodes,
    autoConnectEnabled,
    setAutoConnectEnabled,
    edgeStyle,
    setEdgeStyle,
  } = useTreePreferencesStore();

  // Tree history from Zustand store (auto-persisted to sessionStorage)
  const {
    getHistory,
    addToHistory,
    undo,
    redo,
    canUndo,
    canRedo,
    getUndoCount,
    getRedoCount,
  } = useTreeHistoryStore();

  // Get history for current domain
  const historyState = getHistory(domainId);

  // Local state (not persisted) - Use external if provided, otherwise internal
  const [hasUnsavedChangesInternal, setHasUnsavedChangesInternal] = useState(false);
  const [draggedPositionsInternal, setDraggedPositionsInternal] = useState({});
  const [highlightedNode, setHighlightedNode] = useState(null);

  // SEO Panel state - Single panel for entire tree
  const [showSEOPanel, setShowSEOPanel] = useState(false);
  const [selectedPageForSEO, setSelectedPageForSEO] = useState(null);

  // Node detail panel state - Shows clicked node info in left panel
  const [selectedNodeData, setSelectedNodeData] = useState(null);

  // Use external state if provided, otherwise use internal
  const hasUnsavedChanges = hasUnsavedChangesInternal;
  const setHasUnsavedChanges = setHasUnsavedChangesExternal || setHasUnsavedChangesInternal;
  const draggedPositions = draggedPositionsExternal || draggedPositionsInternal;
  const setDraggedPositions = setDraggedPositionsExternal || setDraggedPositionsInternal;

  // Snap distance (constant)
  const snapDistance = INTERACTION.SNAP_DISTANCE;

  // Save action to history (wrapper for store method)
  const saveToHistory = useCallback((action) => {
    addToHistory(domainId, action);
    console.log('✅ Saved to history:', action);
  }, [domainId, addToHistory]);

  // Handle SEO panel opening - Close any existing panel and open new one
  const handleOpenSEOPanel = useCallback((pageId) => {
    setSelectedPageForSEO(pageId);
    setShowSEOPanel(true);
  }, []);

  // Handle node click - Show details in left panel
  const handleNodeSelect = useCallback((nodeData) => {
    setSelectedNodeData(nodeData);
  }, []);

  // API operations hook
  const {
    refreshTreeData: refreshTreeDataInternal,
    savePositions,
    cancelChanges,
    changeParent: apiChangeParent,
    bulkReparent: apiBulkReparent,
    executeUndo,
    executeRedo,
    isRefreshing,
  } = useTreeAPI({
    domainId,
    fetchDomainWithTree,
    setDraggedPositions,
    setHasUnsavedChanges,
  });

  // Use external refreshTreeData if provided, otherwise use internal
  const refreshTreeData = refreshTreeDataExternal || refreshTreeDataInternal;

  // Transform tree data to React Flow format using custom hooks
  // Step 1: Filter nodes
  const filteredNodes = useTreeFiltering(
    treeData?.nodes || [],
    filterMode,
    showHiddenNodes,
    activeGroupFilter
  );

  // Step 2: Style nodes
  const styledNodes = useNodeStyling(
    filteredNodes,
    draggedPositions,
    selectedPageId,
    highlightedNode,
    editMode,
    refreshTreeData,
    domainId,
    handleOpenSEOPanel,
    handleNodeSelect,
    dataRefreshKey
  );

  // Step 3: Style edges
  const styledEdges = useEdgeStyling(
    treeData?.edges || [],
    styledNodes,
    treeData?.nodes || [],
    edgeStyle
  );

  // Step 4: Apply layout
  const { nodes: initialNodes, edges: initialEdges } = useTreeLayout(
    styledNodes,
    styledEdges,
    useAutoLayout,
    layoutDirection,
    getLayoutedElements,
    treeData?.nodes || []
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Viewport preservation hook - preserves position during data refreshes
  const { onInit, onMoveEnd } = useViewportPreservation(initialNodes);

  // Sync nodes state when initialNodes changes (e.g., after data refresh)
  useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  // Sync edges state when initialEdges changes
  useEffect(() => {
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);

  const onNodeClickHandler = useCallback(
    (event, node) => {
      if (onNodeClick) {
        onNodeClick(Number(node.id));
      }
    },
    [onNodeClick]
  );

  // Drag and drop handlers from hook
  const {
    onNodeDragStart,
    onNodeDrag,
    onNodeDragStop,
  } = useTreeDragDrop({
    editMode,
    autoConnectEnabled,
    snapDistance,
    nodes,
    edges,
    setNodes,
    setDraggedPositions,
    setHasUnsavedChanges,
    setHighlightedNode,
    saveToHistory,
    refreshTreeData,
  });

  // Handle save positions
  const handleSavePositions = useCallback(async () => {
    try {
      await savePositions(draggedPositions);
    } catch (error) {
      alert(error.message);
    }
  }, [savePositions, draggedPositions]);

  // Handle cancel changes
  const handleCancelChanges = useCallback(async () => {
    if (window.confirm('변경사항을 취소하시겠습니까?')) {
      await cancelChanges();
    }
  }, [cancelChanges]);

  // Handle new connection (manual connection)
  const onConnect = useCallback(async (connection) => {
    if (!editMode) return;

    const sourceId = Number(connection.source);
    const targetId = Number(connection.target);

    const confirmed = window.confirm(
      '부모-자식 관계를 변경하시겠습니까?\n트리 구조가 업데이트됩니다.'
    );

    if (!confirmed) return;

    // Find old parent from current edges before optimistic update
    const oldParentEdge = edges.find(e => e.target === String(targetId));
    const oldParentId = oldParentEdge ? Number(oldParentEdge.source) : null;

    // Optimistic update
    setEdges((eds) => addEdge({
      ...connection,
      type: 'smoothstep',
      animated: true,
    }, eds));

    try {
      await apiChangeParent(targetId, sourceId, oldParentId);

      // Save to history
      saveToHistory({
        type: 'reparent',
        pageId: targetId,
        oldParentId: oldParentId,
        newParentId: sourceId,
      });

      alert('부모 관계가 성공적으로 변경되었습니다!');
    } catch (error) {
      alert(error.message);
      // Revert optimistic update
      await refreshTreeData();
    }
  }, [editMode, edges, setEdges, apiChangeParent, saveToHistory, refreshTreeData]);

  // Handle edge deletion (BULK)
  const onEdgesDelete = useCallback(async (edgesToDelete) => {
    if (!editMode) return;

    const confirmed = window.confirm(
      `${edgesToDelete.length}개의 연결을 삭제하시겠습니까?\n해당 노드가 루트 노드가 됩니다.`
    );

    if (!confirmed) return;

    // Optimistic update
    const edgeIds = new Set(edgesToDelete.map(e => e.id));
    setEdges((eds) => eds.filter(e => !edgeIds.has(e.id)));

    try {
      // Use bulk API - preserve old parent info for undo
      const changes = edgesToDelete.map(edge => ({
        page_id: Number(edge.target),
        parent_id: null,
        old_parent_id: Number(edge.source), // Save old parent for undo
      }));

      const response = await apiBulkReparent(changes);

      // Save to history with old parent info
      saveToHistory({
        type: 'bulk_reparent',
        changes: changes,
      });

      if (response.results.failed.length > 0) {
        alert(`일부 연결 삭제 실패:\n${response.results.failed.map(f => f.error).join('\n')}`);
      } else {
        alert('연결이 성공적으로 삭제되었습니다!');
      }
    } catch (error) {
      alert(error.message);
      // Revert optimistic update
      await refreshTreeData();
    }
  }, [editMode, setEdges, apiBulkReparent, saveToHistory, refreshTreeData]);

  // Undo last action
  const handleUndo = useCallback(async () => {
    console.log('handleUndo called');

    if (!canUndo(domainId)) {
      console.log('Cannot undo: no history');
      return;
    }

    const action = undo(domainId);
    if (!action) return;

    console.log('Undoing action:', action);

    try {
      await executeUndo(action);
    } catch (error) {
      alert(error.message);
    }
  }, [domainId, canUndo, undo, executeUndo]);

  // Redo last undone action
  const handleRedo = useCallback(async () => {
    console.log('handleRedo called');

    if (!canRedo(domainId)) {
      console.log('Cannot redo: at end of history');
      return;
    }

    const action = redo(domainId);
    if (!action) return;

    console.log('Redoing action:', action);

    try {
      await executeRedo(action);
    } catch (error) {
      alert(error.message);
    }
  }, [domainId, canRedo, redo, executeRedo]);

  // Update nodes when selected page changes
  useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => ({
        ...node,
        data: {
          ...node.data,
          selected: Number(node.id) === selectedPageId,
        },
      }))
    );
  }, [selectedPageId, setNodes]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!editMode) return;

      // Ctrl/Cmd + Z = Undo
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        handleUndo();
      }
      // Ctrl/Cmd + Shift + Z = Redo
      else if ((e.ctrlKey || e.metaKey) && e.key === 'z' && e.shiftKey) {
        e.preventDefault();
        handleRedo();
      }
      // Ctrl/Cmd + S = Save
      else if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (hasUnsavedChanges) {
          handleSavePositions();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [editMode, hasUnsavedChanges, handleUndo, handleRedo, handleSavePositions]);

  // Debug: Log history state on every render
  // Check if there's no original data at all
  const hasNoData = !treeData || !treeData.nodes || treeData.nodes.length === 0;

  // Check if filtered results are empty (but original data exists)
  const hasNoFilteredResults = !hasNoData && initialNodes.length === 0;

  // Show empty state only when there's truly no data
  if (hasNoData) {
    return (
      <div className="tree-empty">
        <div className="empty-icon">🌳</div>
        <h3>No tree data available</h3>
        <p>Start a scan to discover pages and subdomains</p>
      </div>
    );
  }

  return (
    <div className="subdomain-tree">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClickHandler}
        onNodeDragStart={onNodeDragStart}
        onNodeDrag={onNodeDrag}
        onNodeDragStop={onNodeDragStop}
        onConnect={onConnect}
        onEdgesDelete={onEdgesDelete}
        onInit={onInit}
        onMoveEnd={onMoveEnd}
        nodeTypes={nodeTypes}
        nodesDraggable={editMode && !useAutoLayout}
        edgesUpdatable={editMode}
        edgesFocusable={editMode}
        connectionMode="loose"
        fitView={false}
        minZoom={VIEWPORT.MIN_ZOOM}
        maxZoom={VIEWPORT.MAX_ZOOM}
        defaultViewport={{ x: VIEWPORT.DEFAULT_X, y: VIEWPORT.DEFAULT_Y, zoom: VIEWPORT.DEFAULT_ZOOM }}
        attributionPosition="bottom-left"
      >
        <Background color="#E2E8F0" gap={20} size={2} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={(node) => {
            const score = node.data.seoScore;
            if (!score) return '#9CA3AF';
            if (score >= 90) return '#10B981';
            if (score >= 70) return '#F59E0B';
            return '#EF4444';
          }}
          maskColor="rgba(0, 0, 0, 0.1)"
          style={{ height: 120 }}
          position="bottom-left"
        />
      </ReactFlow>

      {/* Node Detail Panel - Shows clicked node info */}
      <NodeDetailPanel nodeData={selectedNodeData} />

      {/* No Filter Results Message */}
      {hasNoFilteredResults && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          background: 'rgba(255, 255, 255, 0.98)',
          padding: '32px 48px',
          borderRadius: '16px',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
          textAlign: 'center',
          zIndex: 5,
          border: '2px solid #F59E0B',
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔍</div>
          <h3 style={{ margin: '0 0 8px 0', color: '#1F2937', fontSize: '20px' }}>
            필터 결과가 없습니다
          </h3>
          <p style={{ margin: '0', color: '#6B7280', fontSize: '14px' }}>
            {filterMode === 'subdomains' && '서브도메인이 없습니다. 다른 필터를 선택하세요.'}
            {filterMode === 'good' && 'SEO 점수 90점 이상인 페이지가 없습니다.'}
            {filterMode === 'needs-improvement' && 'SEO 점수 70점 미만인 페이지가 없습니다.'}
            {activeGroupFilter && '해당 그룹에 속한 페이지가 없습니다.'}
          </p>
          <p style={{ margin: '12px 0 0 0', color: '#9CA3AF', fontSize: '12px' }}>
            💡 상단의 필터 버튼으로 다른 필터를 선택할 수 있습니다
          </p>
        </div>
      )}

      {/* Loading Overlay */}
      <LoadingOverlay isLoading={isRefreshing} />

      {/* SEO Analysis Panel - Single panel for entire tree */}
      {showSEOPanel && selectedPageForSEO && createPortal(
        <SEOIssuesPanel
          pageId={selectedPageForSEO}
          domainId={domainId}
          onClose={() => {
            setShowSEOPanel(false);
            setSelectedPageForSEO(null);
          }}
        />,
        document.body
      )}
    </div>
  );
};

export default SubdomainTreeV2;
