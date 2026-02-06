/**
 * Verification Prompt Component
 * Prompts user to re-analyze after deployment
 */
import React from 'react';
import './VerificationPrompt.css';

const VerificationPrompt = ({ onVerify, onDismiss, analyzing }) => {
  return (
    <div className="verification-prompt">
      <div className="verification-icon">
        <span role="img" aria-label="search">🔍</span>
      </div>
      <div className="verification-content">
        <div className="verification-title">배포 완료! SEO 개선사항을 검증하세요</div>
        <div className="verification-text">
          변경사항이 웹사이트에 배포되었습니다.
          <br />
          SEO 재분석으로 개선사항을 확인하세요.
        </div>
        <div className="verification-actions">
          <button
            className="btn-verify"
            onClick={onVerify}
            disabled={analyzing}
          >
            {analyzing ? '분석 중...' : '🔍 SEO 재분석'}
          </button>
          <button className="btn-dismiss" onClick={onDismiss}>
            나중에
          </button>
        </div>
      </div>
    </div>
  );
};

export default VerificationPrompt;
