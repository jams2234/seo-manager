/**
 * Node Detail Panel Component
 * Fixed left panel showing hovered node details
 */
import React from 'react';
import { getDepthColor } from '../../constants/themeColors';
import './NodeDetailPanel.css';

const NodeDetailPanel = ({ nodeData, onClose }) => {
  if (!nodeData) {
    return null;
  }

  const depthColor = getDepthColor(nodeData.depthLevel);

  // Get index status display info
  const getIndexStatusInfo = () => {
    if (nodeData.is_indexed === true) {
      return { icon: '✓', text: '색인됨', color: '#10B981', bgColor: '#D1FAE5' };
    } else if (nodeData.is_indexed === false) {
      return { icon: '✗', text: '색인 안됨', color: '#EF4444', bgColor: '#FEE2E2' };
    }
    return null;
  };

  // Get coverage reason explanation
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

  const indexStatusInfo = getIndexStatusInfo();

  return (
    <div className="node-detail-panel">
      <div className="panel-header">
        <h3>노드 상세 정보</h3>
        {onClose && (
          <button className="panel-close-btn" onClick={onClose}>&times;</button>
        )}
      </div>

      <div className="panel-content">
        {/* URL Section */}
        <div className="panel-section">
          <div className="section-title">URL</div>
          <div className="panel-url">{nodeData.url}</div>
          {nodeData.path && (
            <div className="panel-path">Path: {nodeData.path}</div>
          )}
        </div>

        {/* Level Badge */}
        <div className="panel-section">
          <span className="depth-badge" style={{ backgroundColor: depthColor }}>
            Level {nodeData.depthLevel || 0}
          </span>
          {nodeData.group && (
            <span className="group-badge" style={{ backgroundColor: nodeData.group.color }}>
              📁 {nodeData.group.name}
            </span>
          )}
        </div>

        {/* Index Status */}
        {nodeData.is_indexed === false && nodeData.coverage_state && (
          <div className="panel-section">
            <div className="section-title">📊 색인 상태</div>
            <div className="index-explanation">
              {getCoverageReasonExplanation(nodeData.coverage_state).split('\n').map((line, idx) => (
                <div key={idx} className={idx === 0 ? 'explanation-title' : 'explanation-line'}>
                  {line}
                </div>
              ))}
            </div>
          </div>
        )}

        {indexStatusInfo && nodeData.is_indexed === true && (
          <div className="panel-section">
            <div className="section-title">📊 색인 상태</div>
            <span
              className="index-badge"
              style={{
                backgroundColor: indexStatusInfo.bgColor,
                color: indexStatusInfo.color,
              }}
            >
              {indexStatusInfo.icon} {indexStatusInfo.text}
            </span>
          </div>
        )}

        {/* Search Console Analytics */}
        {(nodeData.impressions || nodeData.clicks || nodeData.avg_position) && (
          <div className="panel-section">
            <div className="section-title">🔍 검색 콘솔</div>
            <div className="analytics-grid">
              {nodeData.avg_position && (
                <div className="analytics-item">
                  <span className="analytics-label">평균 순위</span>
                  <span className="analytics-value rank">{nodeData.avg_position.toFixed(1)}위</span>
                </div>
              )}
              {nodeData.impressions !== null && nodeData.impressions !== undefined && (
                <div className="analytics-item">
                  <span className="analytics-label">노출수</span>
                  <span className="analytics-value">{nodeData.impressions.toLocaleString()}</span>
                </div>
              )}
              {nodeData.clicks !== null && nodeData.clicks !== undefined && (
                <div className="analytics-item">
                  <span className="analytics-label">클릭수</span>
                  <span className="analytics-value">{nodeData.clicks.toLocaleString()}</span>
                </div>
              )}
              {nodeData.ctr !== null && nodeData.ctr !== undefined && (
                <div className="analytics-item">
                  <span className="analytics-label">CTR</span>
                  <span className="analytics-value">{nodeData.ctr.toFixed(2)}%</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Top Keywords */}
        {nodeData.top_queries && nodeData.top_queries.length > 0 && (
          <div className="panel-section">
            <div className="section-title">🔑 노출 키워드 (Top {Math.min(nodeData.top_queries.length, 5)})</div>
            <div className="keywords-list">
              {nodeData.top_queries.slice(0, 5).map((query, idx) => (
                <div key={idx} className="keyword-item">
                  <span className="keyword-rank">#{idx + 1}</span>
                  <span className="keyword-text">{query.query}</span>
                  <span className="keyword-stats">
                    {query.position.toFixed(1)}위 | {query.clicks}클릭
                  </span>
                </div>
              ))}
              {nodeData.top_queries.length > 5 && (
                <div className="keyword-more">+{nodeData.top_queries.length - 5}개 더...</div>
              )}
            </div>
          </div>
        )}

        {/* Sitemap Mismatch Warning */}
        {nodeData.has_sitemap_mismatch && nodeData.sitemap_url && (
          <div className="panel-section warning">
            <div className="section-title warning">⚠️ 사이트맵 URL 불일치</div>
            <div className="mismatch-content">
              <p className="mismatch-explanation">
                사이트맵에 등록된 URL이 리다이렉트되어 실제 URL과 다릅니다.
              </p>
              <div className="mismatch-urls">
                <div className="mismatch-url-item">
                  <span className="mismatch-label error">❌ 사이트맵 URL:</span>
                  <span className="mismatch-value">{nodeData.sitemap_url}</span>
                </div>
                <div className="mismatch-url-item">
                  <span className="mismatch-label success">✓ 실제 URL:</span>
                  <span className="mismatch-value">{nodeData.url}</span>
                </div>
              </div>
              {nodeData.redirect_chain && nodeData.redirect_chain.length > 0 && (
                <div className="redirect-chain">
                  <div className="redirect-chain-title">리다이렉트 경로:</div>
                  {nodeData.redirect_chain.map((redirect, idx) => (
                    <div key={idx} className="redirect-chain-item">
                      {idx > 0 && <span className="redirect-arrow">→</span>}
                      <span className="redirect-status">[{redirect.status_code}]</span>
                      <span className="redirect-url">{redirect.url}</span>
                    </div>
                  ))}
                </div>
              )}
              <div className="mismatch-fix">
                💡 <strong>해결방법:</strong> 사이트맵의 URL을 <code>{nodeData.url}</code>로 수정하세요.
              </div>
            </div>
          </div>
        )}

        {/* Sitemap Entry Preview */}
        {nodeData.sitemap_entry && (
          <div className="panel-section">
            <div className="section-title">📋 사이트맵 등록 정보</div>
            <pre className="sitemap-xml-preview">
{`<url>
  <loc>${nodeData.sitemap_entry.loc || nodeData.url}</loc>${nodeData.sitemap_entry.lastmod ? `
  <lastmod>${nodeData.sitemap_entry.lastmod}</lastmod>` : ''}${nodeData.sitemap_entry.changefreq ? `
  <changefreq>${nodeData.sitemap_entry.changefreq}</changefreq>` : ''}${nodeData.sitemap_entry.priority ? `
  <priority>${nodeData.sitemap_entry.priority}</priority>` : ''}
</url>`}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default NodeDetailPanel;
