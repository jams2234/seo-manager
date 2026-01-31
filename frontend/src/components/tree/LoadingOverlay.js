/**
 * LoadingOverlay Component
 * Displays a loading spinner overlay with message
 */
import React from 'react';
import './SubdomainTree.css';

/**
 * LoadingOverlay - Shows loading state with spinner
 *
 * @param {Object} props - Component props
 * @returns {JSX.Element|null} Loading overlay or null
 */
const LoadingOverlay = ({ isLoading, message = '트리 업데이트 중...' }) => {
  if (!isLoading) return null;

  return (
    <div
      style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        background: 'rgba(255, 255, 255, 0.95)',
        padding: '20px 40px',
        borderRadius: '12px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
      }}
    >
      <div className="loading-spinner"></div>
      <span>{message}</span>
    </div>
  );
};

export default LoadingOverlay;
