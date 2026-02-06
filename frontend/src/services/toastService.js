/**
 * Toast Service - Global Toast Management
 * 전역 Toast 알림 서비스 (Context 없이 사용 가능)
 */

// Event bus for toast notifications
const listeners = [];
let toastId = 0;

/**
 * Toast 서비스 - 어디서든 import하여 사용 가능
 */
const toastService = {
  // Subscribe to toast events (used by Toast component)
  subscribe: (callback) => {
    listeners.push(callback);
    return () => {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    };
  },

  // Emit toast event
  _emit: (toast) => {
    listeners.forEach(callback => callback(toast));
  },

  // Show success toast
  success: (message, options = {}) => {
    const toast = {
      id: ++toastId,
      type: 'success',
      message,
      duration: options.duration ?? 5000,
      title: options.title,
    };
    toastService._emit(toast);
    return toast.id;
  },

  // Show error toast
  error: (message, options = {}) => {
    const toast = {
      id: ++toastId,
      type: 'error',
      message,
      duration: options.duration ?? 8000,
      title: options.title,
    };
    toastService._emit(toast);
    return toast.id;
  },

  // Show warning toast
  warning: (message, options = {}) => {
    const toast = {
      id: ++toastId,
      type: 'warning',
      message,
      duration: options.duration ?? 6000,
      title: options.title,
    };
    toastService._emit(toast);
    return toast.id;
  },

  // Show info toast
  info: (message, options = {}) => {
    const toast = {
      id: ++toastId,
      type: 'info',
      message,
      duration: options.duration ?? 5000,
      title: options.title,
    };
    toastService._emit(toast);
    return toast.id;
  },
};

export default toastService;
