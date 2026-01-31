/**
 * Page Details Component
 * Sidebar showing detailed metrics for selected page
 */
import React from 'react';
import './PageDetails.css';

const PageDetails = ({ page, onClose }) => {
  if (!page) return null;

  const getScoreClass = (score) => {
    if (!score) return 'unknown';
    if (score >= 90) return 'good';
    if (score >= 70) return 'medium';
    return 'poor';
  };

  const metrics = page.metrics || {};

  const scores = [
    { label: 'SEO 점수', value: metrics.seo_score, icon: '🎯', desc: 'Search Engine Optimization' },
    { label: '성능', value: metrics.performance_score, icon: '⚡', desc: '페이지 로딩 속도 및 성능' },
    { label: '접근성', value: metrics.accessibility_score, icon: '♿', desc: '장애인 및 보조기술 사용자 접근성' },
    { label: '모범 사례', value: metrics.best_practices_score, icon: '✅', desc: '웹 개발 모범 사례 준수' },
    { label: 'PWA', value: metrics.pwa_score, icon: '📱', desc: 'Progressive Web App 기능' },
  ];

  const coreWebVitals = [
    { label: 'LCP', value: metrics.lcp, unit: 'ms', desc: '최대 콘텐츠풀 페인트 (Largest Contentful Paint)' },
    { label: 'FID', value: metrics.fid, unit: 'ms', desc: '최초 입력 지연 (First Input Delay)' },
    { label: 'CLS', value: metrics.cls, unit: '', desc: '누적 레이아웃 이동 (Cumulative Layout Shift)' },
    { label: 'FCP', value: metrics.fcp, unit: 'ms', desc: '최초 콘텐츠풀 페인트 (First Contentful Paint)' },
    { label: 'TTI', value: metrics.tti, unit: 'ms', desc: '상호작용까지의 시간 (Time to Interactive)' },
  ];

  const searchConsoleData = [
    { label: '노출수', value: metrics.impressions, icon: '👁️', desc: '검색 결과에 표시된 횟수' },
    { label: '클릭수', value: metrics.clicks, icon: '🖱️', desc: '사용자가 클릭한 횟수' },
    { label: '클릭률', value: metrics.ctr ? `${metrics.ctr.toFixed(2)}%` : null, icon: '📈', desc: 'Click Through Rate' },
    { label: '평균 순위', value: metrics.avg_position?.toFixed(1), icon: '🎯', desc: '검색 결과 평균 위치' },
  ];

  return (
    <div className="page-details">
      <div className="details-header">
        <h3 className="details-title">페이지 상세정보</h3>
        <button onClick={onClose} className="close-button">×</button>
      </div>

      <div className="details-body">
        {/* Page Info */}
        <div className="details-section">
          <div className="page-url" title={page.url}>
            {page.url}
          </div>
          {page.title && (
            <div className="page-title-info">
              <strong>제목:</strong> {page.title}
            </div>
          )}
          {page.status && (
            <div className="page-status">
              <span className={`status-badge status-${page.status}`}>
                {page.status}
              </span>
            </div>
          )}
        </div>

        {/* Lighthouse Scores */}
        <div className="details-section">
          <h4 className="section-heading">🏆 Lighthouse 점수</h4>
          <div className="scores-list">
            {scores.map((score, index) => (
              <div key={index} className="score-row">
                <span className="score-icon">{score.icon}</span>
                <span className="score-label">{score.label}</span>
                <span className={`score-value ${getScoreClass(score.value)}`}>
                  {score.value !== null && score.value !== undefined
                    ? score.value.toFixed(1)
                    : 'N/A'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Core Web Vitals */}
        <div className="details-section">
          <h4 className="section-heading">⚡ 핵심 웹 지표</h4>
          <div className="vitals-list">
            {coreWebVitals.map((vital, index) => (
              <div key={index} className="vital-item">
                <div className="vital-header">
                  <span className="vital-label">{vital.label}</span>
                  <span className="vital-value">
                    {vital.value !== null && vital.value !== undefined
                      ? `${vital.value.toFixed(vital.unit === 'ms' ? 0 : 3)}${vital.unit}`
                      : 'N/A'}
                  </span>
                </div>
                <div className="vital-desc">{vital.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Search Console */}
        {(metrics.impressions || metrics.clicks) && (
          <div className="details-section">
            <h4 className="section-heading">🔍 검색 콘솔</h4>
            <div className="search-console-grid">
              {searchConsoleData.map((item, index) => (
                <div key={index} className="console-item">
                  <span className="console-icon">{item.icon}</span>
                  <div className="console-content">
                    <div className="console-label">{item.label}</div>
                    <div className="console-value">
                      {item.value !== null && item.value !== undefined
                        ? typeof item.value === 'number'
                          ? item.value.toLocaleString()
                          : item.value
                        : 'N/A'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Indexing Status */}
        {metrics.is_indexed !== undefined && (
          <div className="details-section">
            <h4 className="section-heading">📑 색인 상태</h4>
            <div className="indexing-info">
              <div className={`indexed-badge ${metrics.is_indexed ? 'indexed' : 'not-indexed'}`}>
                {metrics.is_indexed ? '✓ 색인됨' : '✗ 색인 안됨'}
              </div>
              {metrics.index_status && (
                <div className="index-status">{metrics.index_status}</div>
              )}
            </div>
          </div>
        )}

        {/* Mobile Friendly */}
        {metrics.mobile_friendly !== undefined && (
          <div className="details-section">
            <h4 className="section-heading">📱 모바일</h4>
            <div className="mobile-info">
              <div className={`mobile-badge ${metrics.mobile_friendly ? 'friendly' : 'not-friendly'}`}>
                {metrics.mobile_friendly ? '✅ 모바일 친화적' : '❌ 모바일 최적화 필요'}
              </div>
              {metrics.mobile_score && (
                <div className="mobile-scores">
                  <span>모바일: {metrics.mobile_score.toFixed(1)}</span>
                  {metrics.desktop_score && (
                    <span>데스크톱: {metrics.desktop_score.toFixed(1)}</span>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PageDetails;
