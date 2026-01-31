/**
 * Domain Card Component
 * Displays domain summary with SEO scores
 */
import React from 'react';
import './DomainCard.css';

const DomainCard = ({ domain, onClick }) => {
  const getScoreClass = (score) => {
    if (!score) return 'score-unknown';
    if (score >= 90) return 'score-good';
    if (score >= 70) return 'score-medium';
    return 'score-poor';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      active: { label: 'Active', class: 'status-active' },
      paused: { label: 'Paused', class: 'status-paused' },
      error: { label: 'Error', class: 'status-error' }
    };

    return statusConfig[status] || { label: status, class: 'status-unknown' };
  };

  const statusInfo = getStatusBadge(domain.status);

  return (
    <div className="domain-card card" onClick={onClick}>
      <div className="card-header">
        <div className="domain-info">
          <h3 className="domain-name">
            {domain.protocol}://{domain.domain_name}
          </h3>
          <span className={`status-badge ${statusInfo.class}`}>
            {statusInfo.label}
          </span>
        </div>
      </div>

      <div className="card-body">
        <div className="score-grid">
          <div className="score-item">
            <span className="score-label">Overall SEO</span>
            <span className={`score-value ${getScoreClass(domain.avg_seo_score)}`}>
              {domain.avg_seo_score ? domain.avg_seo_score.toFixed(1) : 'N/A'}
            </span>
          </div>

          <div className="score-item">
            <span className="score-label">Performance</span>
            <span className={`score-value ${getScoreClass(domain.avg_performance_score)}`}>
              {domain.avg_performance_score ? domain.avg_performance_score.toFixed(1) : 'N/A'}
            </span>
          </div>

          <div className="score-item">
            <span className="score-label">Accessibility</span>
            <span className={`score-value ${getScoreClass(domain.avg_accessibility_score)}`}>
              {domain.avg_accessibility_score ? domain.avg_accessibility_score.toFixed(1) : 'N/A'}
            </span>
          </div>

          <div className="score-item">
            <span className="score-label">PWA</span>
            <span className={`score-value ${getScoreClass(domain.avg_pwa_score)}`}>
              {domain.avg_pwa_score ? domain.avg_pwa_score.toFixed(1) : 'N/A'}
            </span>
          </div>
        </div>

        <div className="card-stats">
          <div className="stat-item">
            <span className="stat-icon">📄</span>
            <span className="stat-value">{domain.total_pages || 0}</span>
            <span className="stat-label">Pages</span>
          </div>

          <div className="stat-item">
            <span className="stat-icon">🌐</span>
            <span className="stat-value">{domain.total_subdomains || 0}</span>
            <span className="stat-label">Subdomains</span>
          </div>

          <div className="stat-item">
            <span className="stat-icon">🔍</span>
            <span className="stat-value">
              {domain.search_console_connected ? '✓' : '✗'}
            </span>
            <span className="stat-label">Console</span>
          </div>

          <div className="stat-item">
            <span className="stat-icon">📊</span>
            <span className="stat-value">
              {domain.analytics_connected ? '✓' : '✗'}
            </span>
            <span className="stat-label">Analytics</span>
          </div>
        </div>
      </div>

      <div className="card-footer">
        <span className="last-scan">
          Last scan: {formatDate(domain.last_scanned_at)}
        </span>
        <span className="view-link">View Details →</span>
      </div>
    </div>
  );
};

export default DomainCard;
