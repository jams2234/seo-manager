/**
 * Deployment Result Card Component
 * Shows Git deployment success/failure status
 */
import React from 'react';
import './DeploymentResultCard.css';

const DeploymentResultCard = ({ result, onDismiss }) => {
  if (!result) return null;

  return (
    <div className={`deployment-result ${result.success ? 'success' : 'error'}`}>
      <button className="deployment-dismiss" onClick={onDismiss}>
        &times;
      </button>
      {result.success ? (
        <>
          <div className="deployment-icon">
            <span role="img" aria-label="celebration">🎉</span>
          </div>
          <div className="deployment-info">
            <div className="deployment-title">Git Deployment Complete!</div>
            <div className="deployment-details">
              {result.commit_hash && (
                <div>
                  Commit: <code>{result.commit_hash.substring(0, 7)}</code>
                </div>
              )}
              <div>{result.changes_count} changes deployed to website.</div>
            </div>
          </div>
        </>
      ) : (
        <>
          <div className="deployment-icon">
            <span role="img" aria-label="error">❌</span>
          </div>
          <div className="deployment-info">
            <div className="deployment-title">Git Deployment Failed</div>
            <div className="deployment-details">{result.error}</div>
          </div>
        </>
      )}
    </div>
  );
};

export default DeploymentResultCard;
