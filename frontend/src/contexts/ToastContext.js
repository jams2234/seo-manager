/**
 * Toast Notification Context
 * Provides global toast notifications across the application
 */
import React, { createContext, useContext, useState, useCallback } from 'react';

const ToastContext = createContext(null);

export const ToastType = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
};

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback((message, type = ToastType.INFO, options = {}) => {
    const id = Date.now() + Math.random();
    const toast = {
      id,
      message,
      type,
      duration: options.duration !== undefined ? options.duration : 5000,
      title: options.title,
    };

    setToasts((prev) => [...prev, toast]);

    if (toast.duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, toast.duration);
    }

    return id;
  }, [removeToast]);

  const success = useCallback((message, options) =>
    addToast(message, ToastType.SUCCESS, options), [addToast]);

  const error = useCallback((message, options) =>
    addToast(message, ToastType.ERROR, { duration: 8000, ...options }), [addToast]);

  const warning = useCallback((message, options) =>
    addToast(message, ToastType.WARNING, options), [addToast]);

  const info = useCallback((message, options) =>
    addToast(message, ToastType.INFO, options), [addToast]);

  const value = {
    toasts,
    addToast,
    removeToast,
    success,
    error,
    warning,
    info,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
};

export default ToastContext;
