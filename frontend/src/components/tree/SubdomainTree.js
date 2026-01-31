/**
 * Subdomain Tree Component
 * Visualizes domain hierarchy using React Flow
 */
import React, { useCallback, useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';
import CustomNode from './CustomNode';
import GroupManager from './GroupManager';
import './SubdomainTree.css';

// Define nodeTypes outside component to prevent recreation on each render
const nodeTypes = {
  custom: CustomNode,
};

// Dagre layout configuration
const getLayoutedElements = (nodes, edges, direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const nodeWidth = 280;
  const nodeHeight = 220;

  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 150,  // Horizontal spacing between nodes
    ranksep: 250,  // Vertical spacing between ranks
    marginx: 50,
    marginy: 50,
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
    node.targetPosition = direction === 'TB' ? 'top' : 'left';
    node.sourcePosition = direction === 'TB' ? 'bottom' : 'right';

    // Center the node position
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };

    return node;
  });

  return { nodes, edges };
};

const SubdomainTree = ({ treeData, onNodeClick, selectedPageId, domainId }) => {
  const [useAutoLayout, setUseAutoLayout] = useState(true);
  const [layoutDirection, setLayoutDirection] = useState('TB'); // TB = Top to Bottom, LR = Left to Right
  const [filterMode, setFilterMode] = useState('all'); // 'all', 'subdomains', 'good', 'needs-improvement'

  // Edit mode state
  const [editMode, setEditMode] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [draggedPositions, setDraggedPositions] = useState({});

  // Group manager state
  const [showGroupManager, setShowGroupManager] = useState(false);

  // Visibility control state
  const [showHiddenNodes, setShowHiddenNodes] = useState(false);

  // Transform tree data to React Flow format
  const { initialNodes, initialEdges } = useMemo(() => {
    if (!treeData || !treeData.nodes) {
      return { initialNodes: [], initialEdges: [] };
    }

    // Filter nodes based on filter mode
    let filteredNodes = treeData.nodes;

    // Apply visibility filter first (unless showHiddenNodes is true)
    if (!showHiddenNodes) {
      filteredNodes = filteredNodes.filter(node => node.is_visible !== false);
    }

    if (filterMode === 'subdomains') {
      filteredNodes = filteredNodes.filter(node => node.is_subdomain);
    } else if (filterMode === 'good') {
      filteredNodes = filteredNodes.filter(node => node.seo_score >= 90);
    } else if (filterMode === 'needs-improvement') {
      filteredNodes = filteredNodes.filter(node => node.seo_score < 70);
    }

    const nodes = filteredNodes.map((node) => ({
      id: String(node.id),
      type: 'custom',
      position: node.position || { x: 0, y: 0 },
      data: {
        pageId: node.id,
        label: node.label || node.url,
        customLabel: node.custom_label,
        url: node.url,
        path: node.path,
        seoScore: node.seo_score,
        performanceScore: node.performance_score,
        accessibilityScore: node.accessibility_score,
        totalPages: node.total_pages,
        isSubdomain: node.is_subdomain,
        isVisible: node.is_visible,
        status: node.status,
        selected: node.id === selectedPageId,
        depthLevel: node.depth_level || 0,
        editMode: editMode,
        group: node.group,
        onUpdate: () => window.location.reload(),
      },
    }));

    // Get depth colors for edges
    const getDepthColor = (depthLevel) => {
      const colors = [
        '#4F46E5', // Level 0 (root) - Indigo
        '#7C3AED', // Level 1 - Purple
        '#EC4899', // Level 2 - Pink
        '#F59E0B', // Level 3 - Amber
        '#10B981', // Level 4 - Green
        '#3B82F6', // Level 5+ - Blue
      ];
      return colors[Math.min(depthLevel || 0, colors.length - 1)];
    };

    // Create node lookup for edge styling
    const nodeMap = {};
    nodes.forEach(node => {
      const originalNode = treeData.nodes.find(n => String(n.id) === node.id);
      if (originalNode) {
        nodeMap[node.id] = {
          depthLevel: originalNode.depth_level,
          isSubdomain: originalNode.is_subdomain
        };
      }
    });

    const edges = (treeData.edges || []).map((edge) => {
      const targetNode = nodeMap[String(edge.target)];
      const depthLevel = targetNode?.depthLevel || 0;
      const isSubdomain = targetNode?.isSubdomain || false;
      const edgeColor = getDepthColor(depthLevel);

      return {
        id: `e${edge.source}-${edge.target}`,
        source: String(edge.source),
        target: String(edge.target),
        type: 'smoothstep',
        animated: true,
        style: {
          stroke: edgeColor,
          strokeWidth: isSubdomain ? 3 : 2,
          strokeDasharray: isSubdomain ? '0' : '5, 5',
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: isSubdomain ? 24 : 20,
          height: isSubdomain ? 24 : 20,
          color: edgeColor,
        },
        label: isSubdomain ? '🌐' : '',
        labelStyle: {
          fontSize: 12,
          fill: edgeColor,
        },
        labelBgStyle: {
          fill: 'white',
          fillOpacity: 0.9,
        },
      };
    });

    // Apply auto-layout if enabled
    if (useAutoLayout && nodes.length > 0) {
      const layouted = getLayoutedElements(nodes, edges, layoutDirection);
      return { initialNodes: layouted.nodes, initialEdges: layouted.edges };
    }

    // Filter edges to only include those between filtered nodes
    const nodeIds = new Set(nodes.map(n => n.id));
    const filteredEdges = edges.filter(
      edge => nodeIds.has(edge.source) && nodeIds.has(edge.target)
    );

    return { initialNodes: nodes, initialEdges: filteredEdges };
  }, [treeData, selectedPageId, useAutoLayout, layoutDirection, filterMode]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClickHandler = useCallback(
    (event, node) => {
      if (onNodeClick) {
        onNodeClick(Number(node.id));
      }
    },
    [onNodeClick]
  );

  // Handle node drag stop (only in edit mode)
  const onNodeDragStop = useCallback((event, node) => {
    if (!editMode) return;

    setDraggedPositions(prev => ({
      ...prev,
      [node.id]: { x: node.position.x, y: node.position.y }
    }));
    setHasUnsavedChanges(true);

    // Update local state immediately (optimistic UI)
    setNodes((nds) =>
      nds.map((n) => (n.id === node.id ? { ...n, position: node.position } : n))
    );
  }, [editMode, setNodes]);

  // Handle save positions
  const handleSavePositions = async () => {
    const { pageService } = require('../../services/domainService');

    const updates = Object.entries(draggedPositions).map(([id, pos]) => ({
      id: Number(id),
      x: pos.x,
      y: pos.y
    }));

    try {
      await pageService.bulkUpdatePositions(updates);
      setHasUnsavedChanges(false);
      setDraggedPositions({});
      alert('위치가 성공적으로 저장되었습니다!');
    } catch (error) {
      console.error('Failed to save positions:', error);
      alert('위치 저장에 실패했습니다: ' + error.message);
    }
  };

  // Handle cancel changes
  const handleCancelChanges = () => {
    if (window.confirm('변경사항을 취소하시겠습니까?')) {
      setDraggedPositions({});
      setHasUnsavedChanges(false);
      window.location.reload();
    }
  };

  // Handle new connection (change parent)
  const onConnect = useCallback(async (connection) => {
    if (!editMode) return;

    const sourceId = Number(connection.source);
    const targetId = Number(connection.target);

    const confirmed = window.confirm(
      '부모-자식 관계를 변경하시겠습니까?\n트리 구조가 업데이트됩니다.'
    );

    if (!confirmed) return;

    const { pageService } = require('../../services/domainService');

    try {
      await pageService.changeParent(targetId, sourceId);
      alert('부모 관계가 성공적으로 변경되었습니다!');
      // Reload to refresh tree data
      window.location.reload();
    } catch (error) {
      console.error('Failed to change parent:', error);
      alert('부모 변경 실패: ' + (error.response?.data?.error || error.message));
    }
  }, [editMode]);

  // Handle edge deletion (remove parent)
  const onEdgesDelete = useCallback(async (edgesToDelete) => {
    if (!editMode) return;

    const confirmed = window.confirm(
      `${edgesToDelete.length}개의 연결을 삭제하시겠습니까?\n해당 노드가 루트 노드가 됩니다.`
    );

    if (!confirmed) return;

    const { pageService } = require('../../services/domainService');

    try {
      for (const edge of edgesToDelete) {
        // Delete edge = set parent to null
        await pageService.changeParent(Number(edge.target), null);
      }
      alert('연결이 성공적으로 삭제되었습니다!');
      window.location.reload();
    } catch (error) {
      console.error('Failed to remove parent:', error);
      alert('연결 삭제 실패: ' + (error.response?.data?.error || error.message));
    }
  }, [editMode]);

  // Update nodes when selected page changes
  React.useEffect(() => {
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

  if (!treeData || initialNodes.length === 0) {
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
        onNodeDragStop={onNodeDragStop}
        onConnect={onConnect}
        onEdgesDelete={onEdgesDelete}
        nodeTypes={nodeTypes}
        nodesDraggable={editMode}
        edgesUpdatable={editMode}
        edgesFocusable={editMode}
        connectionMode="loose"
        fitView
        minZoom={0.05}
        maxZoom={1.5}
        defaultViewport={{ x: 0, y: 0, zoom: 0.7 }}
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
        />
      </ReactFlow>

      {/* Layout Controls */}
      <div className="tree-controls">
        {/* Edit Mode Controls */}
        <div className="control-group">
          <button
            className={`control-btn ${editMode ? 'active btn-warning' : 'btn-primary'}`}
            onClick={() => setEditMode(!editMode)}
            title={editMode ? "Exit edit mode" : "Enter edit mode"}
          >
            {editMode ? '🔒 편집 완료' : '✏️ 편집 모드'}
          </button>

          {editMode && hasUnsavedChanges && (
            <>
              <button
                className="control-btn btn-success"
                onClick={handleSavePositions}
                title="Save position changes"
              >
                💾 저장
              </button>
              <button
                className="control-btn btn-danger"
                onClick={handleCancelChanges}
                title="Discard changes"
              >
                ❌ 취소
              </button>
            </>
          )}
        </div>

        {editMode && !hasUnsavedChanges && (
          <div className="edit-info">
            드래그하여 노드 위치를 변경할 수 있습니다
          </div>
        )}

        {/* Group Manager Toggle */}
        {editMode && (
          <>
            <div className="control-divider"></div>
            <div className="control-group">
              <button
                className={`control-btn ${showGroupManager ? 'active btn-primary' : 'btn-primary'}`}
                onClick={() => setShowGroupManager(!showGroupManager)}
                title="Manage page groups"
              >
                📁 {showGroupManager ? '그룹 관리 닫기' : '그룹 관리'}
              </button>
            </div>
          </>
        )}

        <div className="control-divider"></div>

        <div className="control-group">
          <label className="control-label">Layout:</label>
          <button
            className={`control-btn ${useAutoLayout ? 'active' : ''}`}
            onClick={() => setUseAutoLayout(true)}
            title="Auto layout with dagre"
          >
            🤖 Auto
          </button>
          <button
            className={`control-btn ${!useAutoLayout ? 'active' : ''}`}
            onClick={() => setUseAutoLayout(false)}
            title="Custom backend layout"
          >
            📐 Custom
          </button>
        </div>

        {useAutoLayout && (
          <div className="control-group">
            <label className="control-label">Direction:</label>
            <button
              className={`control-btn ${layoutDirection === 'TB' ? 'active' : ''}`}
              onClick={() => setLayoutDirection('TB')}
              title="Top to Bottom"
            >
              ⬇️ TB
            </button>
            <button
              className={`control-btn ${layoutDirection === 'LR' ? 'active' : ''}`}
              onClick={() => setLayoutDirection('LR')}
              title="Left to Right"
            >
              ➡️ LR
            </button>
          </div>
        )}

        <div className="control-divider"></div>

        <div className="control-group">
          <label className="control-label">Filter:</label>
          <button
            className={`control-btn ${filterMode === 'all' ? 'active' : ''}`}
            onClick={() => setFilterMode('all')}
            title="Show all pages"
          >
            🌐 All
          </button>
          <button
            className={`control-btn ${filterMode === 'subdomains' ? 'active' : ''}`}
            onClick={() => setFilterMode('subdomains')}
            title="Show subdomains only"
          >
            🏢 Subdomains
          </button>
          <button
            className={`control-btn ${filterMode === 'good' ? 'active' : ''}`}
            onClick={() => setFilterMode('good')}
            title="Show good pages (≥90)"
          >
            ✅ Good
          </button>
          <button
            className={`control-btn ${filterMode === 'needs-improvement' ? 'active' : ''}`}
            onClick={() => setFilterMode('needs-improvement')}
            title="Show pages needing improvement (<70)"
          >
            ⚠️ Issues
          </button>
        </div>

        {/* Visibility Control */}
        {editMode && (
          <>
            <div className="control-divider"></div>
            <div className="control-group">
              <button
                className={`control-btn ${showHiddenNodes ? 'active' : ''}`}
                onClick={() => setShowHiddenNodes(!showHiddenNodes)}
                title={showHiddenNodes ? "Hide hidden nodes" : "Show hidden nodes"}
              >
                {showHiddenNodes ? '👁️ 숨김 표시' : '👁️‍🗨️ 숨김 숨기기'}
              </button>
            </div>
          </>
        )}
      </div>

      {/* Legend */}
      <div className="tree-legend">
        <div className="legend-title">SEO Score</div>
        <div className="legend-item">
          <div className="legend-color good"></div>
          <span>Good (≥90)</span>
        </div>
        <div className="legend-item">
          <div className="legend-color medium"></div>
          <span>Medium (70-89)</span>
        </div>
        <div className="legend-item">
          <div className="legend-color poor"></div>
          <span>Poor (&lt;70)</span>
        </div>
        <div className="legend-item">
          <div className="legend-color unknown"></div>
          <span>Unknown</span>
        </div>
      </div>

      {/* Group Manager */}
      {editMode && showGroupManager && domainId && (
        <div style={{
          position: 'absolute',
          top: '80px',
          right: '16px',
          width: '350px',
          maxHeight: '600px',
          overflow: 'auto',
          zIndex: 10
        }}>
          <GroupManager
            domainId={domainId}
            onUpdate={() => window.location.reload()}
          />
        </div>
      )}
    </div>
  );
};

export default SubdomainTree;
