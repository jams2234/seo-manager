/**
 * Subdomain Tree with Controls Wrapper
 * Separates control panel from canvas for better UX
 */
import React, { useState, useCallback } from 'react';
import SubdomainTreeV2 from './SubdomainTreeV2';
import TreeControlPanel from './TreeControlPanel';
import useTreePreferencesStore from '../../store/treePreferencesStore';
import useTreeHistoryStore from '../../store/treeHistoryStore';
import useDomainStore from '../../store/domainStore';
import { pageService } from '../../services/domainService';
import './SubdomainTreeWithControls.css';

const SubdomainTreeWithControls = ({ treeData, onNodeClick, selectedPageId, domainId }) => {
  const { fetchDomainWithTree } = useDomainStore();

  // Get all preferences from store
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

  // Get history methods
  const {
    undo,
    redo,
    canUndo,
    canRedo,
    getUndoCount,
    getRedoCount,
  } = useTreeHistoryStore();

  // Local state for edit controls
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [draggedPositions, setDraggedPositions] = useState({});
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [dataRefreshKey, setDataRefreshKey] = useState(0);
  const [activeGroupFilter, setActiveGroupFilter] = useState(null);

  // Refresh tree data
  const refreshTreeData = useCallback(async () => {
    if (!domainId) return;
    setIsRefreshing(true);
    try {
      await fetchDomainWithTree(domainId);
      setDataRefreshKey(prev => prev + 1); // Increment to trigger node updates
    } finally {
      setIsRefreshing(false);
    }
  }, [domainId, fetchDomainWithTree]);

  // Save positions
  const handleSavePositions = useCallback(async () => {
    if (!Object.keys(draggedPositions).length) return;

    const updates = Object.entries(draggedPositions).map(([id, pos]) => ({
      id: Number(id),
      x: pos.x,
      y: pos.y,
    }));

    try {
      await pageService.bulkUpdatePositions(updates);
      setHasUnsavedChanges(false);
      setDraggedPositions({});
      await refreshTreeData();
    } catch (error) {
      console.error('Failed to save positions:', error);
      alert('위치 저장 실패: ' + (error.response?.data?.error || error.message));
    }
  }, [draggedPositions, refreshTreeData]);

  // Cancel changes
  const handleCancelChanges = useCallback(() => {
    setDraggedPositions({});
    setHasUnsavedChanges(false);
    refreshTreeData();
  }, [refreshTreeData]);

  // Handle undo
  const handleUndo = useCallback(async () => {
    try {
      await undo(domainId);
      await refreshTreeData();
    } catch (error) {
      console.error('Undo failed:', error);
    }
  }, [domainId, undo, refreshTreeData]);

  // Handle redo
  const handleRedo = useCallback(async () => {
    try {
      await redo(domainId);
      await refreshTreeData();
    } catch (error) {
      console.error('Redo failed:', error);
    }
  }, [domainId, redo, refreshTreeData]);

  return (
    <div className="tree-with-controls">
      {/* Control Panel - Outside canvas */}
      <TreeControlPanel
        editMode={editMode}
        setEditMode={setEditMode}
        hasUnsavedChanges={hasUnsavedChanges}
        handleSavePositions={handleSavePositions}
        handleCancelChanges={handleCancelChanges}
        autoConnectEnabled={autoConnectEnabled}
        setAutoConnectEnabled={setAutoConnectEnabled}
        canUndo={() => canUndo(domainId)}
        canRedo={() => canRedo(domainId)}
        handleUndo={handleUndo}
        handleRedo={handleRedo}
        getUndoCount={() => getUndoCount(domainId)}
        getRedoCount={() => getRedoCount(domainId)}
        domainId={domainId}
        useAutoLayout={useAutoLayout}
        setUseAutoLayout={setUseAutoLayout}
        layoutDirection={layoutDirection}
        setLayoutDirection={setLayoutDirection}
        filterMode={filterMode}
        setFilterMode={setFilterMode}
        showHiddenNodes={showHiddenNodes}
        setShowHiddenNodes={setShowHiddenNodes}
        edgeStyle={edgeStyle}
        setEdgeStyle={setEdgeStyle}
        refreshTreeData={refreshTreeData}
        activeGroupFilter={activeGroupFilter}
        onGroupFilter={setActiveGroupFilter}
      />

      {/* Tree Canvas */}
      <div className="tree-canvas-container">
        <SubdomainTreeV2
          treeData={treeData}
          onNodeClick={onNodeClick}
          selectedPageId={selectedPageId}
          domainId={domainId}
          // Pass down state setters for tree to update
          setHasUnsavedChanges={setHasUnsavedChanges}
          draggedPositions={draggedPositions}
          setDraggedPositions={setDraggedPositions}
          refreshTreeData={refreshTreeData}
          dataRefreshKey={dataRefreshKey}
          activeGroupFilter={activeGroupFilter}
        />
      </div>
    </div>
  );
};

export default SubdomainTreeWithControls;
