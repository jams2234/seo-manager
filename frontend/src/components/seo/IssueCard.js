/**
 * Issue Card Component
 * Displays individual SEO issue with severity and action buttons
 */
import React from 'react';
import './IssueCard.css';

const IssueCard = ({
  issue,
  onAutoFix,
  variant = 'open', // 'open' | 'fixed'
  onViewDetails,
}) => {
  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return '#ef4444';
      case 'warning': return '#f59e0b';
      case 'info': return '#3b82f6';
      default: return '#6b7280';
    }
  };

  const getVerificationBadge = () => {
    if (variant !== 'fixed') return null;

    if (issue.verification_status === 'verified') {
      return (
        <span
          className="deployment-badge verified"
          title={`Verified: ${issue.verified_at ? new Date(issue.verified_at).toLocaleString('ko-KR') : 'N/A'}`}
        >
          Verified
        </span>
      );
    }
    if (issue.verification_status === 'needs_attention') {
      return (
        <span
          className="deployment-badge needs-attention"
          title="Issue still detected. May be CDN cache or deployment delay."
        >
          Needs Attention
        </span>
      );
    }
    if (issue.deployed_to_git) {
      return (
        <span
          className="deployment-badge pending-verification"
          title={`Deployed to Git. Verify with SEO re-analysis.\nCommit: ${issue.deployment_commit_hash || 'N/A'}`}
        >
          Pending Verification
        </span>
      );
    }
    return (
      <span
        className="deployment-badge db-only"
        title="Modified in database only. Not yet deployed to website."
      >
        DB Only
      </span>
    );
  };

  return (
    <div className={`issue-card ${variant === 'fixed' ? 'fixed-issue' : ''}`}>
      <div className="issue-header">
        <span
          className="issue-severity"
          style={{
            backgroundColor: variant === 'fixed' ? '#10b981' : getSeverityColor(issue.severity)
          }}
        >
          {variant === 'fixed'
            ? (issue.status === 'auto_fixed' ? 'AUTO-FIXED' : 'FIXED')
            : issue.severity
          }
        </span>
        {variant === 'open' && issue.auto_fix_available && (
          <span className="auto-fix-badge">Auto-fixable</span>
        )}
        {variant === 'fixed' && getVerificationBadge()}
      </div>

      <div className="issue-title">{issue.title}</div>
      <div className="issue-message">{issue.message}</div>

      {issue.fix_suggestion && variant === 'open' && (
        <div className="issue-suggestion">
          <strong>Suggestion:</strong> {issue.fix_suggestion}
        </div>
      )}

      {issue.current_value && (
        <div className="issue-values">
          <div className="value-item">
            <span className="value-label">{variant === 'fixed' ? 'Before:' : 'Current:'}</span>
            <span className="value-text">{issue.current_value}</span>
          </div>
          {issue.suggested_value && (
            <div className="value-item">
              <span className="value-label">{variant === 'fixed' ? 'After:' : 'Suggested:'}</span>
              <span className="value-text suggested">{issue.suggested_value}</span>
            </div>
          )}
        </div>
      )}

      {variant === 'fixed' && issue.deployed_to_git && issue.deployment_commit_hash && (
        <div className="deployment-meta">
          <strong>Commit:</strong> {issue.deployment_commit_hash.substring(0, 7)}
          {' | '}
          <strong>Deployed:</strong> {new Date(issue.deployed_at).toLocaleString('ko-KR')}
        </div>
      )}

      {variant === 'open' && issue.auto_fix_available && (
        <button
          className="btn-auto-fix"
          onClick={() => onAutoFix(issue.id)}
          title="Automatically fix this issue (saves to DB, Git deployment is separate)"
        >
          Auto-fix
        </button>
      )}

      {variant === 'fixed' && onViewDetails && (
        <button
          className="btn-view-details"
          onClick={() => onViewDetails(issue)}
        >
          Details & Revert
        </button>
      )}
    </div>
  );
};

export default IssueCard;
