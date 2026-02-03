/**
 * Workspace Tab Bar Component
 * Displays and manages workspace tabs
 */
import React, { useState, useRef } from 'react';
import './WorkspaceTabBar.css';

const WorkspaceTabBar = ({
  tabs,
  activeTabId,
  onTabClick,
  onTabClose,
  onTabReorder,
  onTabRename,
  onAddTab,
  tabLocalStates,
}) => {
  const [editingTabId, setEditingTabId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const [draggedTabId, setDraggedTabId] = useState(null);
  const [dragOverTabId, setDragOverTabId] = useState(null);
  const inputRef = useRef(null);

  // Handle double click to edit name
  const handleDoubleClick = (tab) => {
    setEditingTabId(tab.id);
    setEditingName(tab.name || tab.domain_name);
    setTimeout(() => inputRef.current?.select(), 0);
  };

  // Handle name save
  const handleNameSave = (tabId) => {
    if (editingName.trim()) {
      onTabRename(tabId, editingName.trim());
    }
    setEditingTabId(null);
    setEditingName('');
  };

  // Handle key press in edit mode
  const handleKeyDown = (e, tabId) => {
    if (e.key === 'Enter') {
      handleNameSave(tabId);
    } else if (e.key === 'Escape') {
      setEditingTabId(null);
      setEditingName('');
    }
  };

  // Drag handlers
  const handleDragStart = (e, tabId) => {
    setDraggedTabId(tabId);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e, tabId) => {
    e.preventDefault();
    if (draggedTabId && draggedTabId !== tabId) {
      setDragOverTabId(tabId);
    }
  };

  const handleDragLeave = () => {
    setDragOverTabId(null);
  };

  const handleDrop = (e, targetTabId) => {
    e.preventDefault();
    if (draggedTabId && draggedTabId !== targetTabId) {
      // Reorder tabs
      const currentOrder = tabs.map((t) => t.id);
      const draggedIndex = currentOrder.indexOf(draggedTabId);
      const targetIndex = currentOrder.indexOf(targetTabId);

      const newOrder = [...currentOrder];
      newOrder.splice(draggedIndex, 1);
      newOrder.splice(targetIndex, 0, draggedTabId);

      onTabReorder(newOrder);
    }
    setDraggedTabId(null);
    setDragOverTabId(null);
  };

  const handleDragEnd = () => {
    setDraggedTabId(null);
    setDragOverTabId(null);
  };

  return (
    <div className="workspace-tab-bar">
      <div className="tab-list">
        {tabs.map((tab) => {
          const localState = tabLocalStates[tab.id];
          const hasUnsaved = localState?.hasUnsavedChanges;
          const isActive = tab.id === activeTabId;
          const isDragging = tab.id === draggedTabId;
          const isDragOver = tab.id === dragOverTabId;

          return (
            <div
              key={tab.id}
              className={`tab-item ${isActive ? 'active' : ''} ${isDragging ? 'dragging' : ''} ${isDragOver ? 'drag-over' : ''}`}
              onClick={() => onTabClick(tab.id)}
              draggable={editingTabId !== tab.id}
              onDragStart={(e) => handleDragStart(e, tab.id)}
              onDragOver={(e) => handleDragOver(e, tab.id)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, tab.id)}
              onDragEnd={handleDragEnd}
            >
              {/* Unsaved indicator */}
              {hasUnsaved && <span className="unsaved-indicator" title="저장하지 않은 변경사항"></span>}

              {/* Tab name */}
              {editingTabId === tab.id ? (
                <input
                  ref={inputRef}
                  type="text"
                  className="tab-name-input"
                  value={editingName}
                  onChange={(e) => setEditingName(e.target.value)}
                  onBlur={() => handleNameSave(tab.id)}
                  onKeyDown={(e) => handleKeyDown(e, tab.id)}
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <span
                  className="tab-name"
                  onDoubleClick={() => handleDoubleClick(tab)}
                  title={tab.display_name || tab.domain_name}
                >
                  {tab.display_name || tab.domain_name}
                </span>
              )}

              {/* Close button */}
              <button
                className="tab-close-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onTabClose(tab.id);
                }}
                title="탭 닫기"
              >
                ×
              </button>
            </div>
          );
        })}
      </div>

      {/* Add tab button */}
      <button
        className="add-tab-btn"
        onClick={onAddTab}
        title="새 탭 추가"
      >
        +
      </button>
    </div>
  );
};

export default WorkspaceTabBar;
