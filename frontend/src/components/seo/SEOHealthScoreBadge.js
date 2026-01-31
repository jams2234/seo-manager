/**
 * SEO Health Score Badge Component
 * Displays a compact health score badge with color coding
 */
import React from 'react';
import PropTypes from 'prop-types';
import './SEOHealthScoreBadge.css';

const SEOHealthScoreBadge = ({
  score,
  criticalCount = 0,
  warningCount = 0,
  size = 'medium',
  showDetails = false,
  onClick
}) => {
  // Determine color based on score
  const getScoreColor = (score) => {
    if (score >= 80) return 'excellent';
    if (score >= 60) return 'good';
    if (score >= 40) return 'fair';
    return 'poor';
  };

  const scoreColor = getScoreColor(score);

  // Determine border color for the circle
  const getBorderColor = (scoreColor) => {
    const colors = {
      excellent: '#10B981',
      good: '#84CC16',
      fair: '#F59E0B',
      poor: '#EF4444',
    };
    return colors[scoreColor] || '#9CA3AF';
  };

  return (
    <div
      className={`seo-health-badge ${size} ${scoreColor} ${onClick ? 'clickable' : ''}`}
      onClick={onClick}
      title={`SEO Health Score: ${score}/100`}
    >
      <div className="badge-circle" style={{ borderColor: getBorderColor(scoreColor) }}>
        <span className="badge-score">{Math.round(score)}</span>
      </div>

      {showDetails && (criticalCount > 0 || warningCount > 0) && (
        <div className="badge-details">
          {criticalCount > 0 && (
            <span className="detail-item critical" title="Critical Issues">
              🔴 {criticalCount}
            </span>
          )}
          {warningCount > 0 && (
            <span className="detail-item warning" title="Warning Issues">
              🟡 {warningCount}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

SEOHealthScoreBadge.propTypes = {
  score: PropTypes.number.isRequired,
  criticalCount: PropTypes.number,
  warningCount: PropTypes.number,
  size: PropTypes.oneOf(['small', 'medium', 'large']),
  showDetails: PropTypes.bool,
  onClick: PropTypes.func,
};

export default SEOHealthScoreBadge;
