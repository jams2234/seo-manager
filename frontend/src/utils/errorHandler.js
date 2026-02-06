/**
 * Error Handling Utilities
 * Standardized error handling for API calls and user feedback
 */
import toastService from '../services/toastService';

/**
 * Custom error class for API errors with context
 */
export class APIError extends Error {
  constructor(message, originalError, context = {}) {
    super(message);
    this.name = 'APIError';
    this.originalError = originalError;
    this.context = context;
    this.response = originalError?.response;
    this.status = originalError?.response?.status;
  }

  /**
   * Get user-friendly error message
   * @returns {string} User-friendly error message
   */
  getUserMessage() {
    // Backend API error response
    if (this.response?.data?.message) {
      return this.response.data.message;
    }

    // Backend validation errors
    if (this.response?.data?.details) {
      const details = this.response.data.details;
      if (typeof details === 'object') {
        return Object.entries(details)
          .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`)
          .join('; ');
      }
      return String(details);
    }

    // Network errors
    if (this.originalError?.message?.includes('Network Error')) {
      return '네트워크 연결을 확인해주세요';
    }

    // Timeout errors
    if (this.originalError?.code === 'ECONNABORTED') {
      return '요청 시간이 초과되었습니다. 다시 시도해주세요';
    }

    // HTTP status-based messages
    switch (this.status) {
      case 400:
        return '잘못된 요청입니다';
      case 401:
        return '인증이 필요합니다';
      case 403:
        return '접근 권한이 없습니다';
      case 404:
        return '요청한 리소스를 찾을 수 없습니다';
      case 500:
        return '서버 오류가 발생했습니다';
      case 503:
        return '서비스를 일시적으로 사용할 수 없습니다';
      default:
        return this.message;
    }
  }

  /**
   * Get detailed error info for logging/debugging
   * @returns {Object} Detailed error information
   */
  getDetailedInfo() {
    return {
      message: this.message,
      userMessage: this.getUserMessage(),
      status: this.status,
      context: this.context,
      responseData: this.response?.data,
      originalError: {
        message: this.originalError?.message,
        code: this.originalError?.code,
      },
    };
  }
}

/**
 * Handle API errors consistently
 * @param {string} operation - Description of the operation (e.g., '트리 새로고침')
 * @param {Error} error - The error that occurred
 * @param {Object} context - Additional context (domainId, pageId, etc.)
 * @returns {APIError} Wrapped error with context
 */
export const handleAPIError = (operation, error, context = {}) => {
  // Create wrapped error
  const apiError = new APIError(
    `${operation} 실패: ${error.message}`,
    error,
    context
  );

  // Log to console with full details (development/debugging)
  console.error(`[API Error] ${operation}:`, apiError.getDetailedInfo());

  return apiError;
};

/**
 * Safe error message extraction for display
 * @param {Error|APIError} error - Error object
 * @param {string} fallback - Fallback message if extraction fails
 * @returns {string} User-friendly error message
 */
export const getErrorMessage = (error, fallback = '알 수 없는 오류가 발생했습니다') => {
  if (error instanceof APIError) {
    return error.getUserMessage();
  }

  if (error?.response?.data?.message) {
    return error.response.data.message;
  }

  if (error?.message) {
    return error.message;
  }

  return fallback;
};

/**
 * Show error notification to user
 * @param {Error|APIError|string} error - Error object or message
 * @param {Object} options - Additional options
 * @param {Function} options.toast - Toast context from useToast hook (deprecated)
 * @param {string} options.title - Optional title for toast
 * @param {boolean} options.silent - If true, only log to console
 */
export const showErrorNotification = (error, options = {}) => {
  const message = typeof error === 'string' ? error : getErrorMessage(error);

  if (options.silent) {
    console.warn('[Silent Error]', message);
    return message;
  }

  // If toast function is provided, use it (backwards compatibility)
  if (options.toast) {
    options.toast.error(message, { title: options.title });
    return message;
  }

  // Use global toast service
  toastService.error(message, { title: options.title });
  return message;
};

/**
 * Show success notification to user
 * @param {string} message - Success message
 * @param {Object} options - Additional options
 * @param {Function} options.toast - Toast context from useToast hook (deprecated)
 * @param {string} options.title - Optional title for toast
 */
export const showSuccessNotification = (message, options = {}) => {
  // If toast function is provided, use it (backwards compatibility)
  if (options.toast) {
    options.toast.success(message, { title: options.title });
    return message;
  }

  // Use global toast service
  toastService.success(message, { title: options.title });
  return message;
};

/**
 * Show warning notification to user
 * @param {string} message - Warning message
 * @param {Object} options - Additional options
 * @param {Function} options.toast - Toast context from useToast hook (deprecated)
 * @param {string} options.title - Optional title for toast
 */
export const showWarningNotification = (message, options = {}) => {
  // If toast function is provided, use it (backwards compatibility)
  if (options.toast) {
    options.toast.warning(message, { title: options.title });
    return message;
  }

  // Use global toast service
  toastService.warning(message, { title: options.title });
  return message;
};

/**
 * Show info notification to user
 * @param {string} message - Info message
 * @param {Object} options - Additional options
 * @param {Function} options.toast - Toast context from useToast hook (deprecated)
 * @param {string} options.title - Optional title for toast
 */
export const showInfoNotification = (message, options = {}) => {
  // If toast function is provided, use it (backwards compatibility)
  if (options.toast) {
    options.toast.info(message, { title: options.title });
    return message;
  }

  // Use global toast service
  toastService.info(message, { title: options.title });
  return message;
};

/**
 * Check if error is a specific HTTP status
 * @param {Error|APIError} error - Error object
 * @param {number} status - HTTP status code
 * @returns {boolean}
 */
export const isErrorStatus = (error, status) => {
  return error?.response?.status === status || error?.status === status;
};

/**
 * Check if error is a validation error (400)
 * @param {Error|APIError} error - Error object
 * @returns {boolean}
 */
export const isValidationError = (error) => {
  return isErrorStatus(error, 400);
};

/**
 * Check if error is not found (404)
 * @param {Error|APIError} error - Error object
 * @returns {boolean}
 */
export const isNotFoundError = (error) => {
  return isErrorStatus(error, 404);
};

/**
 * Check if error is server error (500)
 * @param {Error|APIError} error - Error object
 * @returns {boolean}
 */
export const isServerError = (error) => {
  return isErrorStatus(error, 500);
};
