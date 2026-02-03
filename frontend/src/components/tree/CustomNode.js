/**
 * Custom Node Component for React Flow
 * Displays page/subdomain with SEO scores and full URL
 * Hover triggers onHover callback to show details in side panel
 */
import React, { useState, useRef, useEffect } from 'react';
import { Handle, Position } from 'reactflow';
import { pageService, groupService } from '../../services/domainService';
import { getDepthColor, getScoreColor } from '../../constants/themeColors';
import { getContrastTextColor } from '../../utils/colorUtils';
import useNodeActions from '../../hooks/useNodeActions';
import './CustomNode.css';

const CustomNode = ({ data }) => {
  const [isHovered, setIsHovered] = useState(false);
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

  // Fetch available groups when in edit mode or when data is refreshed
  useEffect(() => {
    if (data.editMode && isMountedRef.current) {
      fetchGroups();
    }
  }, [data.editMode, data.dataRefreshKey]);

  const fetchGroups = async () => {
    try {
      setLoadingGroups(true);
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

  // Handle mouse enter - just visual effect
  const handleMouseEnter = () => {
    setIsHovered(true);
  };

  // Handle mouse leave
  const handleMouseLeave = () => {
    setIsHovered(false);
  };

  // Handle click - show details in left panel
  // Don't stopPropagation so ReactFlow's onNodeClick also fires (for right panel)
  const handleNodeClick = () => {
    if (data.onNodeSelect) {
      data.onNodeSelect(data);
    }
  };

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

  // Get short coverage reason for display (translated to Korean)
  const getShortCoverageReason = (coverageState) => {
    const reasons = {
      'Redirect error': '리다이렉트 오류',
      'Page with redirect': '리다이렉트',
      'Discovered - currently not indexed': '발견됨, 미색인',
      'Crawled - currently not indexed': '크롤됨, 미색인',
      'Not found (404)': '404 오류',
      'Server error (5xx)': '서버 오류',
      'Blocked by robots.txt': 'robots.txt 차단',
      'Blocked due to unauthorized request (401)': '인증 필요',
      'Soft 404': 'Soft 404',
      'Duplicate without user-selected canonical': '중복 페이지',
      'Duplicate, Google chose different canonical than user': '중복 (다른 canonical)',
      'Duplicate, submitted URL not selected as canonical': '중복 URL',
      'URL is unknown to Google': '미발견',
      'Excluded by noindex tag': 'noindex 태그',
    };
    return reasons[coverageState] || '미색인';
  };

  // Get search ranking info
  const getSearchRankingInfo = () => {
    if (data.avg_position && data.avg_position > 0) {
      const page = Math.ceil(data.avg_position / 10);
      const position = Math.round(data.avg_position * 10) / 10;
      let color, bgColor;

      if (data.avg_position <= 3) {
        color = '#10B981'; bgColor = '#D1FAE5';
      } else if (data.avg_position <= 10) {
        color = '#3B82F6'; bgColor = '#DBEAFE';
      } else if (data.avg_position <= 20) {
        color = '#F59E0B'; bgColor = '#FEF3C7';
      } else {
        color = '#6B7280'; bgColor = '#F3F4F6';
      }

      return { page, position, color, bgColor };
    }
    return null;
  };

  const searchRankingInfo = getSearchRankingInfo();
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
    <div
      ref={nodeRef}
      className={`custom-node ${scoreColor} ${data.selected ? 'selected' : ''} ${isHovered ? 'hovered' : ''} ${data.isDropTarget ? 'drop-target' : ''} ${data.isFilteredOut ? 'filtered-out' : ''} depth-${data.depthLevel || 0}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleNodeClick}
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
          >
            {indexStatusInfo.icon} {data.is_indexed === false && data.coverage_state
              ? getShortCoverageReason(data.coverage_state)
              : indexStatusInfo.text}
          </span>
        )}
        {searchRankingInfo && (
          <span
            className="node-badge node-ranking-badge"
            style={{
              backgroundColor: searchRankingInfo.bgColor,
              color: searchRankingInfo.color,
              borderColor: searchRankingInfo.color
            }}
          >
            🔍 {searchRankingInfo.page}페이지
          </span>
        )}
        {data.has_sitemap_mismatch && (
          <span
            className="node-badge node-mismatch-badge"
            style={{
              backgroundColor: '#FEF3C7',
              color: '#D97706',
              borderColor: '#F59E0B'
            }}
          >
            ⚠️ URL 불일치
          </span>
        )}
        {data.isSubdomain && <span className="node-badge">Subdomain</span>}
        {data.group && (
          <span
            className="node-badge node-group-badge"
            style={{
              backgroundColor: data.group.color,
              color: getContrastTextColor(data.group.color)
            }}
          >
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
  );
};

export default CustomNode;
