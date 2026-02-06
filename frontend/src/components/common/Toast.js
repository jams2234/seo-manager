/**
 * Toast Notification Component
 * Displays toast messages with auto-dismiss
 * Supports both Context API and toastService
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from '../../contexts/ToastContext';
import toastService from '../../services/toastService';
import './Toast.css';

const Toast = () => {
  const { toasts: contextToasts, removeToast } = useToast();
  const [serviceToasts, setServiceToasts] = useState([]);

  // Subscribe to toastService
  useEffect(() => {
    const unsubscribe = toastService.subscribe((newToast) => {
      setServiceToasts(prev => [...prev, newToast]);

      // Auto-remove after duration
      if (newToast.duration > 0) {
        setTimeout(() => {
          setServiceToasts(prev => prev.filter(t => t.id !== newToast.id));
        }, newToast.duration);
      }
    });

    return unsubscribe;
  }, []);

  const removeServiceToast = useCallback((id) => {
    setServiceToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  // Combine both toast sources
  const toasts = [...contextToasts, ...serviceToasts];

  const getIcon = (type) => {
    const icons = {
      success: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️',
    };
    return icons[type] || icons.info;
  };

  if (toasts.length === 0) return null;

  // Handle toast removal for both sources
  const handleRemove = (toast) => {
    if (contextToasts.some(t => t.id === toast.id)) {
      removeToast(toast.id);
    } else {
      removeServiceToast(toast.id);
    }
  };

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`toast toast-${toast.type}`}
          onClick={() => handleRemove(toast)}
        >
          <span className="toast-icon">{getIcon(toast.type)}</span>
          <div className="toast-content">
            {toast.title && <div className="toast-title">{toast.title}</div>}
            <div className="toast-message">{toast.message}</div>
          </div>
          <button
            className="toast-close"
            onClick={(e) => {
              e.stopPropagation();
              handleRemove(toast);
            }}
          >
            &times;
          </button>
        </div>
      ))}
    </div>
  );
};

export default Toast;
