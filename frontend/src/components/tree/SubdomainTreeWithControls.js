/**
 * Subdomain Tree with Controls Wrapper
 * Separates control panel from canvas for better UX
 * Supports multi-tab view when edit mode is OFF
 * Tabs are persisted to backend (main tab is read-only)
 */
import React, { useState, useCallback, useEffect, useMemo } from 'react';
import SubdomainTreeV2 from './SubdomainTreeV2';
import TreeControlPanel from './TreeControlPanel';
import CanvasTabBar from './CanvasTabBar';
import useTreePreferencesStore from '../../store/treePreferencesStore';
import useTreeHistoryStore from '../../store/treeHistoryStore';
import useDomainStore from '../../store/domainStore';
import { pageService } from '../../services/domainService';
import { canvasTabService } from '../../services/canvasTabService';
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

  // Multi-tab state (persisted to backend)
  const [canvasTabs, setCanvasTabs] = useState([]);
  const [activeTabId, setActiveTabId] = useState(null);
  const [tabsLoading, setTabsLoading] = useState(false);

  // Get active tab object
  const activeTab = useMemo(() => {
    return canvasTabs.find(t => t.id === activeTabId);
  }, [canvasTabs, activeTabId]);

  // Check if current tab is editable (not main tab)
  const canEditCurrentTab = useMemo(() => {
    return activeTab && !activeTab.is_main;
  }, [activeTab]);

  // Load tabs from backend
  const loadTabs = useCallback(async () => {
    if (!domainId) return;
    setTabsLoading(true);
    try {
      const response = await canvasTabService.getTabs(domainId);
      const tabs = response.data;
      setCanvasTabs(tabs);
      // Set active tab
      const activeOne = tabs.find(t => t.is_active) || tabs[0];
      if (activeOne) {
        setActiveTabId(activeOne.id);
      }
    } catch (error) {
      console.error('Failed to load canvas tabs:', error);
      // Fallback to local state if backend fails
      if (canvasTabs.length === 0) {
        setCanvasTabs([{ id: 'local-main', name: 'main', is_main: true }]);
        setActiveTabId('local-main');
      }
    } finally {
      setTabsLoading(false);
    }
  }, [domainId]);

  // Load tabs on mount
  useEffect(() => {
    loadTabs();
  }, [loadTabs]);

  // Tab management functions
  const handleTabClick = useCallback(async (tabId) => {
    if (tabId === activeTabId) return;

    setActiveTabId(tabId);

    // Activate tab in backend
    const tab = canvasTabs.find(t => t.id === tabId);
    if (tab && typeof tab.id === 'number') {
      try {
        await canvasTabService.activateTab(tabId);
      } catch (error) {
        console.error('Failed to activate tab:', error);
      }
    }
  }, [activeTabId, canvasTabs]);

  const handleTabAdd = useCallback(async () => {
    if (!domainId) return;

    try {
      const response = await canvasTabService.addTab(domainId);
      const newTab = response.data;
      setCanvasTabs(prev => [...prev, newTab]);
      setActiveTabId(newTab.id);
    } catch (error) {
      console.error('Failed to add tab:', error);
      alert('탭 추가 실패: ' + (error.response?.data?.error || error.message));
    }
  }, [domainId]);

  const handleTabClose = useCallback(async (tabId) => {
    const tab = canvasTabs.find(t => t.id === tabId);
    if (!tab || tab.is_main) return;

    try {
      await canvasTabService.deleteTab(tabId);
      setCanvasTabs(prev => {
        const newTabs = prev.filter(t => t.id !== tabId);
        // If closing active tab, switch to main tab
        if (activeTabId === tabId && newTabs.length > 0) {
          const mainTab = newTabs.find(t => t.is_main) || newTabs[0];
          setActiveTabId(mainTab.id);
        }
        return newTabs;
      });
    } catch (error) {
      console.error('Failed to delete tab:', error);
      alert('탭 삭제 실패: ' + (error.response?.data?.error || error.message));
    }
  }, [activeTabId, canvasTabs]);

  const handleTabRename = useCallback(async (tabId, newName) => {
    const tab = canvasTabs.find(t => t.id === tabId);
    if (!tab || tab.is_main) return;

    try {
      await canvasTabService.updateTab(tabId, { name: newName });
      setCanvasTabs(prev =>
        prev.map(t => t.id === tabId ? { ...t, name: newName } : t)
      );
    } catch (error) {
      console.error('Failed to rename tab:', error);
    }
  }, [canvasTabs]);

  // Refresh tree data
  const refreshTreeData = useCallback(async () => {
    if (!domainId) return;
    setIsRefreshing(true);
    try {
      await fetchDomainWithTree(domainId);
      setDataRefreshKey(prev => prev + 1);
    } finally {
      setIsRefreshing(false);
    }
  }, [domainId, fetchDomainWithTree]);

  // Save positions (only for non-main tabs)
  const handleSavePositions = useCallback(async () => {
    if (!Object.keys(draggedPositions).length) return;

    // For main tab or edit mode, save to page positions (original behavior)
    if (editMode || !activeTab || activeTab.is_main) {
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
    } else {
      // For custom tabs, save to tab's custom_positions
      try {
        await canvasTabService.savePositions(activeTab.id, draggedPositions);
        // Update local state
        setCanvasTabs(prev =>
          prev.map(t => t.id === activeTab.id
            ? { ...t, custom_positions: { ...t.custom_positions, ...draggedPositions } }
            : t
          )
        );
        setHasUnsavedChanges(false);
        setDraggedPositions({});
      } catch (error) {
        console.error('Failed to save tab positions:', error);
        alert('탭 위치 저장 실패: ' + (error.response?.data?.error || error.message));
      }
    }
  }, [draggedPositions, editMode, activeTab, refreshTreeData]);

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

  // Get custom positions for current tab (to apply to tree)
  const tabCustomPositions = useMemo(() => {
    if (!activeTab || activeTab.is_main) return {};
    return activeTab.custom_positions || {};
  }, [activeTab]);

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
        isMainTab={activeTab?.is_main}
      />

      {/* Canvas Tab Bar - Only shown when edit mode is OFF */}
      {!editMode && canvasTabs.length > 0 && (
        <CanvasTabBar
          tabs={canvasTabs}
          activeTabId={activeTabId}
          onTabClick={handleTabClick}
          onTabAdd={handleTabAdd}
          onTabClose={handleTabClose}
          onTabRename={handleTabRename}
        />
      )}

      {/* Tree Canvas */}
      <div className="tree-canvas-container">
        <SubdomainTreeV2
          key={activeTabId}
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
          // Tab-specific props
          tabCustomPositions={tabCustomPositions}
          canEditPositions={editMode || canEditCurrentTab}
        />
      </div>
    </div>
  );
};

export default SubdomainTreeWithControls;
