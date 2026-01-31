/**
 * Progress Modal Component
 * Shows scan progress with status updates
 */
import React from 'react';
import './ProgressModal.css';

const ProgressModal = ({ isOpen, progress, onClose, onComplete }) => {
  if (!isOpen) return null;

  const { state, percent, status, current, total, error } = progress;

  const isComplete = state === 'SUCCESS';
  const isFailed = state === 'FAILURE';
  const isRunning = state === 'PROGRESS' || state === 'PENDING';

  return (
    <div className="modal-overlay">
      <div className="progress-modal">
        <div className="modal-header">
          <h3>
            {isComplete && '✅ Scan Complete'}
            {isFailed && '❌ Scan Failed'}
            {isRunning && '🔄 Scanning...'}
          </h3>
          {isComplete && (
            <button onClick={onClose} className="close-button">×</button>
          )}
        </div>

        <div className="modal-body">
          {isRunning && (
            <>
              <div className="progress-bar-container">
                <div className="progress-bar" style={{ width: `${percent || 0}%` }}>
                  <span className="progress-text">{percent || 0}%</span>
                </div>
              </div>

              <div className="progress-status">
                <p>{status || 'Starting scan...'}</p>
                {current !== undefined && total !== undefined && (
                  <p className="progress-count">{current} / {total}</p>
                )}
              </div>

              <div className="loading-spinner-large"></div>
            </>
          )}

          {isComplete && (
            <div className="completion-message">
              <p>✓ All pages have been scanned successfully!</p>
              <button onClick={onComplete} className="btn btn-primary">
                View Results
              </button>
            </div>
          )}

          {isFailed && (
            <div className="error-message">
              <p>⚠️ Scan failed: {error || 'Unknown error'}</p>
              <button onClick={onClose} className="btn btn-secondary">
                Close
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProgressModal;
