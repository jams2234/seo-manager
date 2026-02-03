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
        <div className="verification-title">Deployment Complete! Verify SEO Improvements</div>
        <div className="verification-text">
          Changes have been deployed to the website.
          <br />
          Run SEO re-analysis to confirm improvements.
        </div>
        <div className="verification-actions">
          <button
            className="btn-verify"
            onClick={onVerify}
            disabled={analyzing}
          >
            {analyzing ? 'Analyzing...' : 'Re-analyze SEO'}
          </button>
          <button className="btn-dismiss" onClick={onDismiss}>
            Later
          </button>
        </div>
      </div>
    </div>
  );
};

export default VerificationPrompt;
