/**
 * Metric Card Component
 * Displays individual SEO metric with score
 */
import React from 'react';
import './MetricCard.css';

const MetricCard = ({ title, value, icon, description }) => {
  const getScoreClass = (score) => {
    if (score === null || score === undefined) return 'unknown';
    if (score >= 90) return 'good';
    if (score >= 70) return 'medium';
    return 'poor';
  };

  const getScoreLabel = (score) => {
    if (score === null || score === undefined) return 'No Data';
    if (score >= 90) return 'Excellent';
    if (score >= 70) return 'Good';
    if (score >= 50) return 'Needs Work';
    return 'Poor';
  };

  const scoreClass = getScoreClass(value);
  const scoreLabel = getScoreLabel(value);

  return (
    <div className={`metric-card ${scoreClass}`}>
      <div className="metric-header">
        <span className="metric-icon">{icon}</span>
        <span className="metric-title">{title}</span>
      </div>

      <div className="metric-score">
        <div className="score-display">
          <span className="score-number">
            {value !== null && value !== undefined ? value.toFixed(1) : 'N/A'}
          </span>
          <span className="score-max">/100</span>
        </div>
        <span className={`score-label ${scoreClass}`}>{scoreLabel}</span>
      </div>

      {description && (
        <div className="metric-description">{description}</div>
      )}

      <div className="metric-bar">
        <div
          className={`metric-progress ${scoreClass}`}
          style={{ width: `${value || 0}%` }}
        ></div>
      </div>
    </div>
  );
};

export default MetricCard;
