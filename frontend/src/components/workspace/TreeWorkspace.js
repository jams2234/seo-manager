/**
 * Tree Workspace Component
 * Main workspace container with tab management
 */
import React, { useEffect, useState, useCallback } from 'react';
import useWorkspaceStore from '../../store/workspaceStore';
import useDomainStore from '../../store/domainStore';
import WorkspaceTabBar from './WorkspaceTabBar';
import AddTabModal from './AddTabModal';
import SubdomainTreeWithControls from '../tree/SubdomainTreeWithControls';
import './TreeWorkspace.css';

const TreeWorkspace = ({ initialWorkspaceId, initialDomainId }) => {
  const {
    workspace,
    workspaceLoading,
    workspaceError,
    activeTabTreeData,
    treeDataLoading,
    tabLocalStates,
    loadWorkspace,
    loadDefaultWorkspace,
    addTab,
    removeTab,
    activateTab,
    reorderTabs,
    updateTabName,
    setTabViewport,
    setTabDraggedPositions,
    saveTabPositions,
    refreshActiveTabTreeData,
    getActiveTab,
    getActiveTabLocalState,
  } = useWorkspaceStore();

  const { domains, fetchDomains } = useDomainStore();

  const [showAddTabModal, setShowAddTabModal] = useState(false);
  const [selectedPageId, setSelectedPageId] = useState(null);

  // Load workspace on mount
  useEffect(() => {
    if (initialWorkspaceId) {
      loadWorkspace(initialWorkspaceId);
    } else {
      loadDefaultWorkspace();
    }
    fetchDomains();
  }, [initialWorkspaceId, loadWorkspace, loadDefaultWorkspace, fetchDomains]);

  // If initialDomainId is provided and workspace has no tabs, add it
  useEffect(() => {
    if (workspace && initialDomainId && workspace.tabs.length === 0) {
      addTab(initialDomainId);
    }
  }, [workspace, initialDomainId, addTab]);

  // Get current active tab
  const activeTab = getActiveTab();
  const activeTabLocalState = getActiveTabLocalState();

  // Handle tab click
  const handleTabClick = useCallback(
    (tabId) => {
      if (activeTab?.id !== tabId) {
        activateTab(tabId);
      }
    },
    [activeTab, activateTab]
  );

  // Handle tab close
  const handleTabClose = useCallback(
    (tabId) => {
      const tabState = tabLocalStates[tabId];
      if (tabState?.hasUnsavedChanges) {
        if (!window.confirm('저장하지 않은 변경사항이 있습니다. 탭을 닫으시겠습니까?')) {
          return;
        }
      }
      removeTab(tabId);
    },
    [tabLocalStates, removeTab]
  );

  // Handle add tab
  const handleAddTab = useCallback(
    async (domainId) => {
      await addTab(domainId);
      setShowAddTabModal(false);
    },
    [addTab]
  );

  // Handle node click in tree
  const handleNodeClick = useCallback((pageId) => {
    setSelectedPageId(pageId);
  }, []);

  // Handle viewport change from tree
  const handleViewportChange = useCallback(
    (viewport) => {
      if (activeTab) {
        setTabViewport(activeTab.id, viewport);
      }
    },
    [activeTab, setTabViewport]
  );

  // Handle dragged positions change
  const handleDraggedPositionsChange = useCallback(
    (positions) => {
      if (activeTab) {
        setTabDraggedPositions(activeTab.id, positions);
      }
    },
    [activeTab, setTabDraggedPositions]
  );

  // Handle save positions
  const handleSavePositions = useCallback(async () => {
    if (activeTab) {
      await saveTabPositions(activeTab.id);
    }
  }, [activeTab, saveTabPositions]);

  // Loading state
  if (workspaceLoading) {
    return (
      <div className="tree-workspace-loading">
        <div className="loading-spinner"></div>
        <p>워크스페이스 로딩 중...</p>
      </div>
    );
  }

  // Error state
  if (workspaceError) {
    return (
      <div className="tree-workspace-error">
        <p>오류: {workspaceError}</p>
        <button onClick={() => loadDefaultWorkspace()}>다시 시도</button>
      </div>
    );
  }

  // No workspace
  if (!workspace) {
    return (
      <div className="tree-workspace-empty">
        <p>워크스페이스를 불러올 수 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="tree-workspace">
      {/* Tab Bar */}
      <WorkspaceTabBar
        tabs={workspace.tabs}
        activeTabId={activeTab?.id}
        onTabClick={handleTabClick}
        onTabClose={handleTabClose}
        onTabReorder={reorderTabs}
        onTabRename={updateTabName}
        onAddTab={() => setShowAddTabModal(true)}
        tabLocalStates={tabLocalStates}
      />

      {/* Tree Content */}
      <div className="tree-workspace-content">
        {activeTab && activeTabTreeData ? (
          <SubdomainTreeWithControls
            key={activeTab.id}
            treeData={activeTabTreeData}
            onNodeClick={handleNodeClick}
            selectedPageId={selectedPageId}
            domainId={activeTab.domain}
            // External state management for viewport preservation
            hasUnsavedChanges={activeTabLocalState?.hasUnsavedChanges || false}
            setHasUnsavedChanges={(val) =>
              setTabDraggedPositions(activeTab.id, val ? activeTabLocalState?.draggedPositions || {} : {})
            }
            draggedPositions={activeTabLocalState?.draggedPositions || {}}
            setDraggedPositions={(positions) => handleDraggedPositionsChange(positions)}
            onRefresh={refreshActiveTabTreeData}
          />
        ) : treeDataLoading ? (
          <div className="tree-workspace-loading">
            <div className="loading-spinner"></div>
            <p>트리 데이터 로딩 중...</p>
          </div>
        ) : workspace.tabs.length === 0 ? (
          <div className="tree-workspace-empty-tabs">
            <div className="empty-icon">🌳</div>
            <h3>탭이 없습니다</h3>
            <p>도메인을 추가하여 트리를 표시하세요</p>
            <button
              className="add-tab-btn primary"
              onClick={() => setShowAddTabModal(true)}
            >
              + 탭 추가
            </button>
          </div>
        ) : (
          <div className="tree-workspace-select-tab">
            <p>탭을 선택하세요</p>
          </div>
        )}
      </div>

      {/* Add Tab Modal */}
      {showAddTabModal && (
        <AddTabModal
          domains={domains}
          existingDomainIds={workspace.tabs.map((t) => t.domain)}
          onAdd={handleAddTab}
          onClose={() => setShowAddTabModal(false)}
        />
      )}
    </div>
  );
};

export default TreeWorkspace;
