/**
 * Dashboard Component
 * Overview of domain SEO metrics
 */
import React from 'react';
import MetricCard from './MetricCard';
import './Dashboard.css';

const Dashboard = ({ domain }) => {
  if (!domain) {
    return (
      <div className="dashboard-empty">
        <p>No domain data available</p>
      </div>
    );
  }

  const metrics = [
    {
      title: 'SEO Score',
      value: domain.avg_seo_score,
      icon: '🎯',
      description: 'Overall SEO performance',
    },
    {
      title: 'Performance',
      value: domain.avg_performance_score,
      icon: '⚡',
      description: 'Page load speed and optimization',
    },
    {
      title: 'Accessibility',
      value: domain.avg_accessibility_score,
      icon: '♿',
      description: 'Accessibility standards compliance',
    },
    {
      title: 'PWA',
      value: domain.avg_pwa_score,
      icon: '📱',
      description: 'Progressive Web App readiness',
    },
  ];

  const stats = [
    {
      label: 'Total Pages',
      value: domain.total_pages || 0,
      icon: '📄',
    },
    {
      label: 'Subdomains',
      value: domain.total_subdomains || 0,
      icon: '🌐',
    },
    {
      label: 'Search Console',
      value: domain.search_console_connected ? 'Connected' : 'Not Connected',
      icon: '🔍',
      status: domain.search_console_connected ? 'success' : 'warning',
    },
    {
      label: 'Analytics',
      value: domain.analytics_connected ? 'Connected' : 'Not Connected',
      icon: '📊',
      status: domain.analytics_connected ? 'success' : 'warning',
    },
  ];

  return (
    <div className="dashboard">
      <div className="dashboard-section">
        <h2 className="section-title">SEO Metrics Overview</h2>
        <div className="metrics-grid">
          {metrics.map((metric, index) => (
            <MetricCard key={index} {...metric} />
          ))}
        </div>
      </div>

      <div className="dashboard-section">
        <h2 className="section-title">Domain Statistics</h2>
        <div className="stats-grid">
          {stats.map((stat, index) => (
            <div key={index} className={`stat-card ${stat.status || ''}`}>
              <div className="stat-icon">{stat.icon}</div>
              <div className="stat-content">
                <div className="stat-label">{stat.label}</div>
                <div className="stat-value">{stat.value}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {domain.last_scanned_at && (
        <div className="dashboard-section">
          <div className="info-card">
            <div className="info-icon">ℹ️</div>
            <div className="info-content">
              <h3>Last Scanned</h3>
              <p>
                {new Date(domain.last_scanned_at).toLocaleString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="dashboard-section">
        <h2 className="section-title">Quick Actions</h2>
        <div className="actions-grid">
          <button className="action-button">
            <span className="action-icon">🔄</span>
            <span className="action-label">Refresh Data</span>
            <span className="action-desc">Update metrics in real-time</span>
          </button>
          <button className="action-button">
            <span className="action-icon">🔍</span>
            <span className="action-label">Full Scan</span>
            <span className="action-desc">Discover new pages</span>
          </button>
          <button className="action-button">
            <span className="action-icon">📊</span>
            <span className="action-label">View History</span>
            <span className="action-desc">Analyze trends over time</span>
          </button>
          <button className="action-button">
            <span className="action-icon">⚙️</span>
            <span className="action-label">Settings</span>
            <span className="action-desc">Configure domain options</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
