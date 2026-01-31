/**
 * Custom Node Component for React Flow
 * Displays page/subdomain with SEO scores and full URL
 */
import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Handle, Position } from 'reactflow';
import { pageService, groupService } from '../../services/domainService';
import { getDepthColor, getScoreColor } from '../../constants/themeColors';
import useNodeActions from '../../hooks/useNodeActions';
import './CustomNode.css';

const CustomNode = ({ data }) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });
  const nodeRef = useRef(null);
  const isMountedRef = useRef(true);

  // Label editing state
  const [isEditingLabel, setIsEditingLabel] = useState(false);
  const [editedLabel, setEditedLabel] = useState(data.customLabel || data.label);
  const inputRef = useRef(null);

  // Group selection state
  const [availableGroups, setAvailableGroups] = useState([]);
  const [loadingGroups, setLoadingGroups] = useState(false);

  // Node actions (subdomain, visibility, group)
  const { handleSubdomainToggle, handleVisibilityToggle, handleGroupChange } = useNodeActions(
    data.pageId,
    data.isSubdomain,
    data.isVisible,
    data.onUpdate
  );

  // Cleanup on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Fetch available groups when in edit mode
  useEffect(() => {
    if (data.editMode && isMountedRef.current) {
      fetchGroups();
    }
  }, [data.editMode]);

  const fetchGroups = async () => {
    try {
      setLoadingGroups(true);
      // Get domainId from data prop
      const domainId = data.domainId;
      if (!domainId) {
        console.warn('No domainId provided to CustomNode');
        if (isMountedRef.current) {
          setAvailableGroups([]);
        }
        return;
      }
      const response = await groupService.listGroups(domainId);
      if (isMountedRef.current) {
        // Handle paginated response (DRF pagination returns {count, results})
        const groups = response.data.results || response.data || [];
        setAvailableGroups(groups);
      }
    } catch (error) {
      console.error('Failed to fetch groups:', error);
      if (isMountedRef.current) {
        setAvailableGroups([]);
      }
    } finally {
      if (isMountedRef.current) {
        setLoadingGroups(false);
      }
    }
  };

  useEffect(() => {
    if (showTooltip && nodeRef.current && isMountedRef.current) {
      const rect = nodeRef.current.getBoundingClientRect();
      setTooltipPosition({
        top: rect.top + window.scrollY,
        left: rect.left + rect.width / 2 + window.scrollX,
      });
    }
  }, [showTooltip]);

  const getStatusIcon = (status) => {
    const icons = {
      active: '✓',
      '404': '⚠️',
      '500': '❌',
      redirected: '↗️',
    };
    return icons[status] || '●';
  };

  // Get index status display info
  const getIndexStatusInfo = () => {
    if (data.is_indexed === true) {
      return { icon: '✓', text: '색인됨', color: '#10B981', bgColor: '#D1FAE5' };
    } else if (data.is_indexed === false) {
      return { icon: '✗', text: '색인 안됨', color: '#EF4444', bgColor: '#FEE2E2' };
    }
    return null;
  };

  const scoreColor = getScoreColor(data.seoScore);
  const statusIcon = getStatusIcon(data.status);
  const depthColor = getDepthColor(data.depthLevel);
  const indexStatusInfo = getIndexStatusInfo();

  // Use group color if available, otherwise use depth color
  const borderColor = data.group?.color || depthColor;
  const backgroundColor = data.group ? `${data.group.color}15` : undefined;

  // Truncate URL for display
  const getTruncatedUrl = (url) => {
    if (!url) return '';
    try {
      const urlObj = new URL(url);
      const path = urlObj.pathname + urlObj.search;
      return path.length > 40 ? path.substring(0, 37) + '...' : path;
    } catch {
      return url.length > 40 ? url.substring(0, 37) + '...' : url;
    }
  };

  // Handle label double click
  const handleLabelDoubleClick = (e) => {
    e.stopPropagation();
    if (data.editMode) {
      setIsEditingLabel(true);
    }
  };

  // Handle label save
  const handleLabelSave = async () => {
    if (!editedLabel.trim()) {
      if (isMountedRef.current) {
        setEditedLabel(data.label);
        setIsEditingLabel(false);
      }
      return;
    }

    try {
      await pageService.updatePage(data.pageId, {
        custom_label: editedLabel
      });
      if (isMountedRef.current) {
        setIsEditingLabel(false);
        if (data.onUpdate) {
          data.onUpdate();
        }
      }
    } catch (error) {
      console.error('Failed to save label:', error);
      if (isMountedRef.current) {
        alert('레이블 저장 실패: ' + (error.response?.data?.error || error.message));
        setEditedLabel(data.customLabel || data.label);
        setIsEditingLabel(false);
      }
    }
  };

  // Handle label edit cancel
  const handleLabelCancel = () => {
    setEditedLabel(data.customLabel || data.label);
    setIsEditingLabel(false);
  };


  // Focus input when entering edit mode
  useEffect(() => {
    if (isEditingLabel && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditingLabel]);

  return (
    <>
      <div
        ref={nodeRef}
        className={`custom-node ${scoreColor} ${data.selected ? 'selected' : ''} depth-${data.depthLevel || 0}`}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        style={{
          borderLeftColor: borderColor,
          backgroundColor: backgroundColor,
        }}
      >
        <Handle type="target" position={Position.Top} />

      {/* Node Header */}
      <div className="node-header">
        <span className="node-status">{statusIcon}</span>
        <span className="node-depth-indicator" style={{ backgroundColor: depthColor }}>
          L{data.depthLevel || 0}
        </span>
        {indexStatusInfo && (
          <span
            className="node-badge node-index-badge"
            style={{
              backgroundColor: indexStatusInfo.bgColor,
              color: indexStatusInfo.color,
              borderColor: indexStatusInfo.color
            }}
            title={data.coverageState || indexStatusInfo.text}
          >
            {indexStatusInfo.icon} {indexStatusInfo.text}
          </span>
        )}
        {data.isSubdomain && <span className="node-badge">Subdomain</span>}
        {data.group && (
          <span className="node-badge node-group-badge" style={{ backgroundColor: data.group.color }}>
            📁 {data.group.name}
          </span>
        )}
      </div>

      {/* Node Label - Editable */}
      {isEditingLabel ? (
        <input
          ref={inputRef}
          type="text"
          className="node-label-input"
          value={editedLabel}
          onChange={(e) => setEditedLabel(e.target.value)}
          onBlur={handleLabelSave}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleLabelSave();
            } else if (e.key === 'Escape') {
              handleLabelCancel();
            }
          }}
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <div
          className="node-label"
          title={data.editMode ? "더블클릭하여 편집" : data.url}
          onDoubleClick={handleLabelDoubleClick}
        >
          {data.customLabel || data.label}
        </div>
      )}

      {/* Full URL Display */}
      <div className="node-url" title={data.url}>
        🔗 {getTruncatedUrl(data.url)}
      </div>

      {/* Edit Mode Controls */}
      {data.editMode && !isEditingLabel && (
        <div className="node-edit-controls">
          <button
            className="node-edit-btn subdomain-toggle"
            onClick={handleSubdomainToggle}
            title={data.isSubdomain ? "일반 페이지로 변경" : "서브도메인으로 변경"}
          >
            {data.isSubdomain ? '🏢' : '📄'}
          </button>
          <button
            className="node-edit-btn visibility-toggle"
            onClick={handleVisibilityToggle}
            title={data.isVisible === false ? "페이지 보이기" : "페이지 숨기기"}
          >
            {data.isVisible === false ? '👁️‍🗨️' : '👁️'}
          </button>
          <button
            className="node-edit-btn seo-analysis-btn"
            onClick={(e) => {
              e.stopPropagation();
              if (data.onOpenSEOPanel) {
                data.onOpenSEOPanel(data.pageId);
              }
            }}
            title="SEO 분석"
          >
            🔍
          </button>
          <select
            className="node-group-select"
            value={data.group?.id || ''}
            onChange={handleGroupChange}
            onClick={(e) => e.stopPropagation()}
            disabled={loadingGroups}
            title="그룹 선택"
          >
            <option value="">📁 그룹 없음</option>
            {availableGroups.map(group => (
              <option key={group.id} value={group.id}>
                📁 {group.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* SEO Score - Main */}
      {data.seoScore !== null && data.seoScore !== undefined && (
        <div className="node-seo-score-section">
          <div className="seo-score-label">SEO Score</div>
          <div className={`seo-score-badge score-${getScoreColor(data.seoScore)}`}>
            {data.seoScore.toFixed(0)}
          </div>
        </div>
      )}

      {/* Page Count */}
      {data.totalPages > 0 && (
        <div className="node-pages">
          📄 {data.totalPages} {data.totalPages === 1 ? 'page' : 'pages'}
        </div>
      )}

      {/* Metrics */}
      <div className="node-metrics">
        {data.performanceScore !== null && (
          <div className="metric-item" title="Performance Score">
            ⚡ {data.performanceScore.toFixed(0)}
          </div>
        )}
        {data.accessibilityScore !== null && (
          <div className="metric-item" title="Accessibility Score">
            ♿ {data.accessibilityScore.toFixed(0)}
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} />
      </div>

      {/* Tooltip rendered via Portal to avoid z-index issues */}
      {showTooltip && createPortal(
        <div
          className="node-tooltip-portal"
          style={{
            position: 'absolute',
            top: `${tooltipPosition.top}px`,
            left: `${tooltipPosition.left}px`,
            transform: 'translateX(-50%) translateY(-100%) translateY(-20px)',
            zIndex: 999999,
          }}
        >
          <div className="node-tooltip">
            <div className="tooltip-header">
              <strong>Full URL:</strong>
            </div>
            <div className="tooltip-url">{data.url}</div>
            {data.path && (
              <div className="tooltip-path">
                <strong>Path:</strong> {data.path}
              </div>
            )}
            <div className="tooltip-divider"></div>
            <div className="tooltip-scores">
              {data.seoScore !== null && (
                <div className="tooltip-score-item">
                  <span className="tooltip-label">SEO:</span>
                  <span className="tooltip-value">{data.seoScore.toFixed(1)}</span>
                </div>
              )}
              {data.performanceScore !== null && (
                <div className="tooltip-score-item">
                  <span className="tooltip-label">Performance:</span>
                  <span className="tooltip-value">{data.performanceScore.toFixed(1)}</span>
                </div>
              )}
              {data.accessibilityScore !== null && (
                <div className="tooltip-score-item">
                  <span className="tooltip-label">Accessibility:</span>
                  <span className="tooltip-value">{data.accessibilityScore.toFixed(1)}</span>
                </div>
              )}
            </div>
            <div className="tooltip-depth">
              <span className="depth-badge" style={{ backgroundColor: depthColor }}>
                Level {data.depthLevel || 0}
              </span>
            </div>
          </div>
        </div>,
        document.body
      )}

    </>
  );
};

export default CustomNode;
