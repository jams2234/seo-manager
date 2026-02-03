/**
 * TreeControlPanel Component
 * Inline toolbar layout for better canvas visibility
 */
import React from 'react';
import CategoryManager from './CategoryManager';
import useTreePreferencesStore from '../../store/treePreferencesStore';
import './TreeControlPanel.css';

const TreeControlPanel = ({
  editMode,
  setEditMode,
  hasUnsavedChanges,
  handleSavePositions,
  handleCancelChanges,
  autoConnectEnabled,
  setAutoConnectEnabled,
  canUndo,
  canRedo,
  handleUndo,
  handleRedo,
  getUndoCount,
  getRedoCount,
  domainId,
  useAutoLayout,
  setUseAutoLayout,
  layoutDirection,
  setLayoutDirection,
  filterMode,
  setFilterMode,
  showHiddenNodes,
  setShowHiddenNodes,
  edgeStyle,
  setEdgeStyle,
  refreshTreeData,
  activeGroupFilter,
  onGroupFilter,
}) => {
  // Use Zustand store for panel visibility (persisted across refreshes)
  const {
    showEditTools,
    setShowEditTools,
    showFilters,
    setShowFilters,
    showEdgeStyles,
    setShowEdgeStyles,
    showGroupManager,
    setShowGroupManager,
  } = useTreePreferencesStore();

  return (
    <div className="tree-controls-v2">
      {/* Main Toolbar */}
      <div className="controls-toolbar">
        {/* Edit Mode Group */}
        <div className="toolbar-group">
          <button
            className={`control-btn-v2 edit-mode-btn ${editMode ? 'active' : ''}`}
            onClick={() => setEditMode(!editMode)}
            title={editMode ? "편집 완료" : "편집 모드"}
          >
            {editMode ? '🔒 편집 완료' : '✏️ 편집'}
          </button>

          {editMode && hasUnsavedChanges && (
            <>
              <button className="control-btn-v2 save-btn" onClick={handleSavePositions} title="저장 (Ctrl+S)">
                💾 저장
              </button>
              <button className="control-btn-v2 cancel-btn" onClick={handleCancelChanges} title="취소">
                ❌ 취소
              </button>
            </>
          )}
        </div>

        <div className="toolbar-divider" />

        {/* Layout Mode Group */}
        <div className="toolbar-group">
          <span className="section-label">레이아웃</span>
          <div className="btn-group">
            <button
              className={`control-btn-v2 ${useAutoLayout ? 'active' : ''}`}
              onClick={() => setUseAutoLayout(true)}
              title="자동 정렬"
            >
              🤖 자동
            </button>
            <button
              className={`control-btn-v2 ${!useAutoLayout ? 'active' : ''}`}
              onClick={() => setUseAutoLayout(false)}
              title="수동 위치"
            >
              📐 수동
            </button>
          </div>

          {useAutoLayout && (
            <div className="btn-group">
              <button
                className={`control-btn-v2 ${layoutDirection === 'TB' ? 'active' : ''}`}
                onClick={() => setLayoutDirection('TB')}
                title="세로"
              >
                ⬇️
              </button>
              <button
                className={`control-btn-v2 ${layoutDirection === 'LR' ? 'active' : ''}`}
                onClick={() => setLayoutDirection('LR')}
                title="가로"
              >
                ➡️
              </button>
            </div>
          )}
        </div>

        <div className="toolbar-divider" />

        {/* Filter Group */}
        <div className="toolbar-group">
          <span className="section-label">필터</span>
          <div className="btn-group">
            <button
              className={`control-btn-v2 ${filterMode === 'all' ? 'active' : ''}`}
              onClick={() => setFilterMode('all')}
              title="전체"
            >
              🌐
            </button>
            <button
              className={`control-btn-v2 ${filterMode === 'subdomains' ? 'active' : ''}`}
              onClick={() => setFilterMode('subdomains')}
              title="서브도메인"
            >
              🏢
            </button>
            <button
              className={`control-btn-v2 ${filterMode === 'good' ? 'active' : ''}`}
              onClick={() => setFilterMode('good')}
              title="우수 (≥90)"
            >
              ✅
            </button>
            <button
              className={`control-btn-v2 ${filterMode === 'needs-improvement' ? 'active' : ''}`}
              onClick={() => setFilterMode('needs-improvement')}
              title="개선필요 (<70)"
            >
              ⚠️
            </button>
          </div>
        </div>

        {/* Edit Tools Toggle */}
        {editMode && (
          <>
            <div className="toolbar-divider" />
            <div className="toolbar-group">
              <button
                className="control-btn-v2"
                onClick={() => setShowEditTools(!showEditTools)}
                title="편집 도구"
              >
                🛠️ {showEditTools ? '도구 숨김' : '도구 표시'}
              </button>
            </div>
          </>
        )}
      </div>

      {/* Edit Tools Section */}
      {editMode && showEditTools && (
        <div className="expandable-section">
          <div className="section-content">
            <button
              className={`control-btn-v2 ${autoConnectEnabled ? 'active' : ''}`}
              onClick={() => setAutoConnectEnabled(!autoConnectEnabled)}
              title="자동 연결"
            >
              {autoConnectEnabled ? '🧲 자동연결 ON' : '🧲 자동연결 OFF'}
            </button>

            <button
              className="control-btn-v2"
              onClick={handleUndo}
              disabled={!canUndo(domainId)}
              title="실행취소 (Ctrl+Z)"
            >
              ↩️ Undo {canUndo(domainId) && getUndoCount(domainId) > 0 && `(${getUndoCount(domainId)})`}
            </button>

            <button
              className="control-btn-v2"
              onClick={handleRedo}
              disabled={!canRedo(domainId)}
              title="다시실행 (Ctrl+Shift+Z)"
            >
              ↪️ Redo {canRedo(domainId) && getRedoCount(domainId) > 0 && `(${getRedoCount(domainId)})`}
            </button>

            {!hasUnsavedChanges && (
              <div className="help-text">
                {useAutoLayout
                  ? '💡 수동 모드로 전환하여 노드를 드래그할 수 있습니다'
                  : '💡 노드를 드래그하여 위치를 변경하거나 자동 연결하세요'}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Advanced Filters Section */}
      {editMode && (
        <div className="expandable-section">
          <button
            className="section-toggle-btn"
            onClick={() => setShowFilters(!showFilters)}
          >
            <span>고급 필터</span>
            <span>{showFilters ? '▼' : '▶'}</span>
          </button>

          {showFilters && (
            <div className="section-content">
              <button
                className={`control-btn-v2 ${showHiddenNodes ? 'active' : ''}`}
                onClick={() => setShowHiddenNodes(!showHiddenNodes)}
                title="숨김 노드 표시"
              >
                {showHiddenNodes ? '👁️ 숨김 표시' : '👁️‍🗨️ 숨김 숨기기'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Edge Styles Section */}
      {editMode && (
        <div className="expandable-section">
          <button
            className="section-toggle-btn"
            onClick={() => setShowEdgeStyles(!showEdgeStyles)}
          >
            <span>Edge 스타일</span>
            <span>{showEdgeStyles ? '▼' : '▶'}</span>
          </button>

          {showEdgeStyles && (
            <div className="section-content">
              <button
                className={`control-btn-v2 ${edgeStyle.useGroupColors ? 'active' : ''}`}
                onClick={() => setEdgeStyle(prev => ({ ...prev, useGroupColors: !prev.useGroupColors }))}
                title="그룹 색상"
              >
                🎨 그룹 색상
              </button>

              <button
                className={`control-btn-v2 ${edgeStyle.animated ? 'active' : ''}`}
                onClick={() => setEdgeStyle(prev => ({ ...prev, animated: !prev.animated }))}
                title="애니메이션"
              >
                ✨ 애니메이션
              </button>

              <button
                className={`control-btn-v2 ${edgeStyle.showLabels ? 'active' : ''}`}
                onClick={() => setEdgeStyle(prev => ({ ...prev, showLabels: !prev.showLabels }))}
                title="라벨 표시"
              >
                🏷️ 라벨
              </button>
            </div>
          )}
        </div>
      )}

      {/* Group Management Section */}
      {editMode && (
        <div className="expandable-section">
          <button
            className="section-toggle-btn"
            onClick={() => setShowGroupManager(!showGroupManager)}
          >
            <span>그룹 관리</span>
            <span>{showGroupManager ? '▼' : '▶'}</span>
          </button>

          {showGroupManager && domainId && (
            <div className="section-content group-manager-content">
              <CategoryManager
                domainId={domainId}
                onUpdate={refreshTreeData}
                onGroupFilter={onGroupFilter}
                activeGroupFilter={activeGroupFilter}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TreeControlPanel;
