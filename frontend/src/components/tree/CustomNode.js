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

  // Get detailed explanation for coverage state (for tooltip)
  const getCoverageReasonExplanation = (coverageState) => {
    const explanations = {
      'Redirect error': '❌ 리다이렉트 오류\n이 페이지는 리다이렉트 설정에 문제가 있습니다.\n• 리다이렉트 체인이 너무 길거나\n• 리다이렉트 대상이 존재하지 않습니다.\n→ 리다이렉트 경로를 확인하세요.',
      'Page with redirect': '↗️ 정상적인 리다이렉트\n이 페이지는 다른 URL로 정상적으로 리다이렉트됩니다.\n• 의도된 동작이라면 문제없습니다.\n• 최종 URL이 색인되어 있는지 확인하세요.',
      'Discovered - currently not indexed': '🔍 발견됨 (미색인)\nGoogle이 이 URL을 발견했지만 아직 크롤링하지 않았습니다.\n• 새 페이지이거나 우선순위가 낮을 수 있습니다.\n→ 내부 링크를 추가하거나 사이트맵에 포함하세요.',
      'Crawled - currently not indexed': '📋 크롤됨 (미색인)\nGoogle이 페이지를 크롤링했지만 색인하지 않기로 결정했습니다.\n• 콘텐츠 품질이 낮거나 중복으로 판단될 수 있습니다.\n→ 콘텐츠를 개선하고 고유한 가치를 추가하세요.',
      'Not found (404)': '⚠️ 404 오류\n페이지를 찾을 수 없습니다.\n• URL이 삭제되었거나 이동되었습니다.\n→ 페이지를 복구하거나 301 리다이렉트를 설정하세요.',
      'Server error (5xx)': '🔴 서버 오류\n서버가 페이지를 제공하지 못했습니다.\n• 서버 과부하 또는 설정 문제일 수 있습니다.\n→ 서버 로그를 확인하고 문제를 해결하세요.',
      'Blocked by robots.txt': '🚫 robots.txt 차단\nrobots.txt에서 크롤링이 차단되었습니다.\n• 의도된 설정이 아니라면 수정이 필요합니다.\n→ robots.txt 파일을 확인하세요.',
      'Blocked due to unauthorized request (401)': '🔒 인증 필요 (401)\n페이지 접근에 로그인이 필요합니다.\n• 공개 페이지여야 한다면 인증 설정을 확인하세요.',
      'Soft 404': '📄 Soft 404\n페이지가 존재하지만 실제로는 오류 페이지처럼 보입니다.\n• "결과 없음" 같은 빈 콘텐츠 페이지일 수 있습니다.\n→ 유용한 콘텐츠를 추가하거나 404로 응답하세요.',
      'Duplicate without user-selected canonical': '📑 중복 페이지\n이 페이지가 다른 페이지와 중복으로 감지되었습니다.\n• canonical 태그가 설정되지 않았습니다.\n→ 대표 URL에 canonical 태그를 설정하세요.',
      'Duplicate, Google chose different canonical than user': '📑 Canonical 불일치\n설정한 canonical URL과 Google이 선택한 URL이 다릅니다.\n→ Google Search Console에서 정확한 URL을 확인하세요.',
      'Duplicate, submitted URL not selected as canonical': '📑 중복 URL\n사이트맵에 제출했지만 Google이 다른 URL을 대표로 선택했습니다.\n→ 중복 콘텐츠를 정리하거나 canonical을 확인하세요.',
      'URL is unknown to Google': '❓ 미발견 URL\nGoogle이 아직 이 URL을 발견하지 못했습니다.\n• 새로운 페이지일 수 있습니다.\n→ 사이트맵에 추가하고 내부 링크를 연결하세요.',
      'Excluded by noindex tag': '🏷️ noindex 태그\nnoindex 메타 태그로 인해 색인이 차단되었습니다.\n• 의도된 설정이라면 문제없습니다.\n→ 색인이 필요하면 noindex 태그를 제거하세요.',
    };
    return explanations[coverageState] || `상태: ${coverageState || '알 수 없음'}\nGoogle Search Console에서 자세한 정보를 확인하세요.`;
  };

  // Get search ranking info
  const getSearchRankingInfo = () => {
    if (data.avg_position && data.avg_position > 0) {
      const page = Math.ceil(data.avg_position / 10);
      const position = Math.round(data.avg_position * 10) / 10;
      let color, bgColor;

      if (data.avg_position <= 3) {
        color = '#10B981'; bgColor = '#D1FAE5'; // Top 3 - green
      } else if (data.avg_position <= 10) {
        color = '#3B82F6'; bgColor = '#DBEAFE'; // Page 1 - blue
      } else if (data.avg_position <= 20) {
        color = '#F59E0B'; bgColor = '#FEF3C7'; // Page 2 - yellow
      } else {
        color = '#6B7280'; bgColor = '#F3F4F6'; // Page 3+ - gray
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
            title={data.is_indexed === false && data.coverage_state
              ? getCoverageReasonExplanation(data.coverage_state)
              : indexStatusInfo.text}
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
            title={`평균 ${searchRankingInfo.position}위 | 노출 ${data.impressions?.toLocaleString() || 0} | 클릭 ${data.clicks?.toLocaleString() || 0}`}
          >
            🔍 {searchRankingInfo.page}페이지
          </span>
        )}
        {/* Sitemap Mismatch Warning Badge */}
        {data.has_sitemap_mismatch && (
          <span
            className="node-badge node-mismatch-badge"
            style={{
              backgroundColor: '#FEF3C7',
              color: '#D97706',
              borderColor: '#F59E0B'
            }}
            title="사이트맵 URL 불일치 - 리다이렉트 발생"
          >
            ⚠️ URL 불일치
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
            <div className="tooltip-depth">
              <span className="depth-badge" style={{ backgroundColor: depthColor }}>
                Level {data.depthLevel || 0}
              </span>
            </div>
            {/* Index Status Explanation */}
            {data.is_indexed === false && data.coverage_state && (
              <>
                <div className="tooltip-divider"></div>
                <div className="tooltip-index-status">
                  <div className="tooltip-section-title">📊 색인 상태</div>
                  <div className="tooltip-index-explanation">
                    {getCoverageReasonExplanation(data.coverage_state).split('\n').map((line, idx) => (
                      <div key={idx} className={idx === 0 ? 'explanation-title' : 'explanation-line'}>
                        {line}
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
            {/* Search Console Analytics */}
            {(data.impressions || data.clicks || data.avg_position) && (
              <>
                <div className="tooltip-divider"></div>
                <div className="tooltip-search-console">
                  <div className="tooltip-section-title">🔍 검색 콘솔</div>
                  <div className="tooltip-analytics-grid">
                    {data.avg_position && (
                      <div className="analytics-item">
                        <span className="analytics-label">평균 순위</span>
                        <span className="analytics-value rank">{data.avg_position.toFixed(1)}위</span>
                      </div>
                    )}
                    {data.impressions !== null && data.impressions !== undefined && (
                      <div className="analytics-item">
                        <span className="analytics-label">노출수</span>
                        <span className="analytics-value">{data.impressions.toLocaleString()}</span>
                      </div>
                    )}
                    {data.clicks !== null && data.clicks !== undefined && (
                      <div className="analytics-item">
                        <span className="analytics-label">클릭수</span>
                        <span className="analytics-value">{data.clicks.toLocaleString()}</span>
                      </div>
                    )}
                    {data.ctr !== null && data.ctr !== undefined && (
                      <div className="analytics-item">
                        <span className="analytics-label">CTR</span>
                        <span className="analytics-value">{data.ctr.toFixed(2)}%</span>
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
            {/* Top Keywords/Queries */}
            {data.top_queries && data.top_queries.length > 0 && (
              <>
                <div className="tooltip-divider"></div>
                <div className="tooltip-keywords">
                  <div className="tooltip-section-title">🔑 노출 키워드 (Top {data.top_queries.length})</div>
                  <div className="tooltip-keywords-list">
                    {data.top_queries.slice(0, 5).map((query, idx) => (
                      <div key={idx} className="keyword-item">
                        <span className="keyword-rank">#{idx + 1}</span>
                        <span className="keyword-text">{query.query}</span>
                        <span className="keyword-stats">
                          {query.position.toFixed(1)}위 | {query.clicks}클릭
                        </span>
                      </div>
                    ))}
                    {data.top_queries.length > 5 && (
                      <div className="keyword-more">
                        +{data.top_queries.length - 5}개 더...
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
            {/* Sitemap Mismatch Warning */}
            {data.has_sitemap_mismatch && data.sitemap_url && (
              <>
                <div className="tooltip-divider"></div>
                <div className="tooltip-sitemap-mismatch">
                  <div className="tooltip-section-title warning">⚠️ 사이트맵 URL 불일치</div>
                  <div className="sitemap-mismatch-content">
                    <div className="mismatch-explanation">
                      사이트맵에 등록된 URL이 리다이렉트되어 실제 URL과 다릅니다.
                      Google은 리다이렉트되는 URL을 색인하지 않으므로 사이트맵을 수정해야 합니다.
                    </div>
                    <div className="mismatch-urls">
                      <div className="mismatch-url-item">
                        <span className="mismatch-url-label error">❌ 사이트맵 URL (미색인):</span>
                        <span className="mismatch-url-value">{data.sitemap_url}</span>
                      </div>
                      <div className="mismatch-url-item">
                        <span className="mismatch-url-label success">✓ 실제 URL (canonical):</span>
                        <span className="mismatch-url-value">{data.url}</span>
                      </div>
                    </div>
                    {data.redirect_chain && data.redirect_chain.length > 0 && (
                      <div className="mismatch-redirect-chain">
                        <div className="redirect-chain-title">리다이렉트 경로:</div>
                        {data.redirect_chain.map((redirect, idx) => (
                          <div key={idx} className="redirect-chain-item">
                            {idx > 0 && <span className="redirect-arrow">→</span>}
                            <span className="redirect-status">[{redirect.status_code}]</span>
                            <span className="redirect-url">{redirect.url}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="mismatch-fix-suggestion">
                      💡 <strong>해결방법:</strong> 사이트맵의 URL을 <code>{data.url}</code>로 수정하세요.
                    </div>
                  </div>
                </div>
              </>
            )}
            {/* Sitemap Entry Preview */}
            {data.sitemap_entry && (
              <>
                <div className="tooltip-divider"></div>
                <div className="tooltip-sitemap-preview">
                  <div className="tooltip-section-title">📋 사이트맵 등록 정보</div>
                  <div className="sitemap-preview-content">
                    <pre className="sitemap-xml-preview">
{`<url>
  <loc>${data.sitemap_entry.loc || data.url}</loc>${data.sitemap_entry.lastmod ? `
  <lastmod>${data.sitemap_entry.lastmod}</lastmod>` : ''}${data.sitemap_entry.changefreq ? `
  <changefreq>${data.sitemap_entry.changefreq}</changefreq>` : ''}${data.sitemap_entry.priority ? `
  <priority>${data.sitemap_entry.priority}</priority>` : ''}
</url>`}
                    </pre>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>,
        document.body
      )}

    </>
  );
};

export default CustomNode;
