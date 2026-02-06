/**
 * Health Score Card Component
 * Displays SEO health score with statistics and bulk action button
 */
import React from 'react';
import './HealthScoreCard.css';

const HealthScoreCard = ({
  score,
  previousScore,
  criticalCount,
  warningCount,
  autoFixableCount,
  onBulkAutoFix,
}) => {
  const getHealthScoreColor = (score) => {
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#f59e0b';
    return '#ef4444';
  };

  const scoreChange = previousScore ? score - previousScore : null;
  const hasImproved = scoreChange && scoreChange > 0;

  return (
    <div className="health-score-card">
      <div className="health-score-main">
        <div
          className={`health-score-circle ${hasImproved ? 'score-improved' : ''}`}
          style={{ borderColor: getHealthScoreColor(score) }}
        >
          <span className="health-score-value">{score}</span>
        </div>
        <div className="health-score-info">
          <div className="health-score-label">
            Health Score
            {scoreChange !== null && scoreChange !== 0 && (
              <span className={`score-change ${scoreChange > 0 ? 'positive' : 'negative'}`}>
                {scoreChange > 0 ? '+' : ''}{scoreChange}
              </span>
            )}
          </div>
          <div className="health-score-stats">
            <span className="stat-item critical">{criticalCount} 심각</span>
            <span className="stat-item warning">{warningCount} 경고</span>
          </div>
        </div>
      </div>
      {autoFixableCount > 0 && (
        <button
          className="btn-auto-fix-all"
          onClick={onBulkAutoFix}
          title="모든 이슈를 자동 수정합니다 (DB에 저장, Git 배포는 별도)"
        >
          🔧 {autoFixableCount}개 오토픽스
        </button>
      )}
    </div>
  );
};

export default HealthScoreCard;
