/**
 * Canvas Tab Bar
 * Tab bar for managing multiple canvas views of the same domain tree
 * Only shown when edit mode is OFF
 * Main tab shows lock icon and is read-only
 */
import React, { useState, useRef, useEffect } from 'react';
import './CanvasTabBar.css';

const CanvasTabBar = ({
  tabs,
  activeTabId,
  onTabClick,
  onTabAdd,
  onTabClose,
  onTabRename,
}) => {
  const [editingTabId, setEditingTabId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const inputRef = useRef(null);

  // Focus input when editing
  useEffect(() => {
    if (editingTabId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingTabId]);

  const handleDoubleClick = (tab) => {
    // Don't allow editing main tab name
    if (tab.is_main) return;
    setEditingTabId(tab.id);
    setEditingName(tab.name);
  };

  const handleRenameSubmit = (tabId) => {
    if (editingName.trim()) {
      onTabRename(tabId, editingName.trim());
    }
    setEditingTabId(null);
    setEditingName('');
  };

  const handleKeyDown = (e, tabId) => {
    if (e.key === 'Enter') {
      handleRenameSubmit(tabId);
    } else if (e.key === 'Escape') {
      setEditingTabId(null);
      setEditingName('');
    }
  };

  // Add new canvas tab for current domain
  const handleAddTab = () => {
    onTabAdd();
  };

  return (
    <div className="canvas-tab-bar">
      <div className="canvas-tabs">
        {tabs.map((tab) => (
          <div
            key={tab.id}
            className={`canvas-tab ${activeTabId === tab.id ? 'active' : ''} ${tab.is_main ? 'main-tab' : ''}`}
            onClick={() => onTabClick(tab.id)}
            onDoubleClick={() => handleDoubleClick(tab)}
            title={tab.is_main ? '읽기 전용 (배포된 트리)' : '더블클릭하여 이름 변경'}
          >
            {editingTabId === tab.id ? (
              <input
                ref={inputRef}
                type="text"
                className="tab-name-input"
                value={editingName}
                onChange={(e) => setEditingName(e.target.value)}
                onBlur={() => handleRenameSubmit(tab.id)}
                onKeyDown={(e) => handleKeyDown(e, tab.id)}
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <>
                {tab.is_main && <span className="tab-lock-icon">🔒</span>}
                <span className="tab-name">{tab.name}</span>
                {!tab.is_main && (
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
                )}
              </>
            )}
          </div>
        ))}

        {/* Add Tab Button - directly adds new canvas */}
        <button
          className="add-tab-btn"
          onClick={handleAddTab}
          title="새 캔버스 추가 (편집 가능)"
        >
          +
        </button>
      </div>
    </div>
  );
};

export default CanvasTabBar;
