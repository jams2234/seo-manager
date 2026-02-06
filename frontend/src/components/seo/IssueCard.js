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

  const getSeverityLabel = (severity) => {
    switch (severity) {
      case 'critical': return '심각';
      case 'warning': return '경고';
      case 'info': return '정보';
      default: return severity;
    }
  };

  const getVerificationBadge = () => {
    if (variant !== 'fixed') return null;

    if (issue.verification_status === 'verified') {
      return (
        <span
          className="deployment-badge verified"
          title={`검증됨: ${issue.verified_at ? new Date(issue.verified_at).toLocaleString('ko-KR') : 'N/A'}`}
        >
          검증됨
        </span>
      );
    }
    if (issue.verification_status === 'needs_attention') {
      return (
        <span
          className="deployment-badge needs-attention"
          title="이슈가 아직 감지됩니다. CDN 캐시 또는 배포 지연일 수 있습니다."
        >
          주의 필요
        </span>
      );
    }
    if (issue.deployed_to_git) {
      return (
        <span
          className="deployment-badge pending-verification"
          title={`Git에 배포됨. SEO 재분석으로 검증하세요.\n커밋: ${issue.deployment_commit_hash || 'N/A'}`}
        >
          검증 대기
        </span>
      );
    }
    return (
      <span
        className="deployment-badge db-only"
        title="데이터베이스에만 수정됨. 웹사이트에 아직 배포되지 않음."
      >
        DB만
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
            ? (issue.status === 'auto_fixed' ? '오토픽스' : '수정됨')
            : getSeverityLabel(issue.severity)
          }
        </span>
        {variant === 'open' && issue.auto_fix_available && (
          <span className="auto-fix-badge">자동 수정 가능</span>
        )}
        {variant === 'fixed' && getVerificationBadge()}
      </div>

      <div className="issue-title">{issue.title}</div>
      <div className="issue-message">{issue.message}</div>

      {issue.fix_suggestion && variant === 'open' && (
        <div className="issue-suggestion">
          <strong>제안:</strong> {issue.fix_suggestion}
        </div>
      )}

      {issue.current_value && (
        <div className="issue-values">
          <div className="value-item">
            <span className="value-label">{variant === 'fixed' ? '변경 전:' : '현재 값:'}</span>
            <span className="value-text">{issue.current_value}</span>
          </div>
          {issue.suggested_value && (
            <div className="value-item">
              <span className="value-label">{variant === 'fixed' ? '변경 후:' : '제안 값:'}</span>
              <span className="value-text suggested">{issue.suggested_value}</span>
            </div>
          )}
        </div>
      )}

      {variant === 'fixed' && issue.deployed_to_git && issue.deployment_commit_hash && (
        <div className="deployment-meta">
          <strong>커밋:</strong> {issue.deployment_commit_hash.substring(0, 7)}
          {' | '}
          <strong>배포:</strong> {new Date(issue.deployed_at).toLocaleString('ko-KR')}
        </div>
      )}

      {variant === 'open' && issue.auto_fix_available && (
        <button
          className="btn-auto-fix"
          onClick={() => onAutoFix(issue.id)}
          title="이 이슈를 자동 수정합니다 (DB에 저장, Git 배포는 별도)"
        >
          🔧 오토픽스
        </button>
      )}

      {variant === 'fixed' && onViewDetails && (
        <button
          className="btn-view-details"
          onClick={() => onViewDetails(issue)}
        >
          상세 및 되돌리기
        </button>
      )}
    </div>
  );
};

export default IssueCard;
