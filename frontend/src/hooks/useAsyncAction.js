/**
 * useAsyncAction Hook
 * 비동기 작업 실행 및 상태 관리를 위한 훅
 */
import { useState, useCallback } from 'react';

/**
 * 비동기 작업을 실행하고 로딩, 에러, 성공 상태를 관리합니다.
 *
 * @example
 * const { execute, loading, error, data } = useAsyncAction();
 *
 * const handleSubmit = async () => {
 *   const result = await execute(
 *     () => api.createItem(formData),
 *     {
 *       successMessage: '항목이 생성되었습니다.',
 *       errorMessage: '항목 생성에 실패했습니다.',
 *       onSuccess: (data) => console.log('Created:', data),
 *       onError: (error) => console.error('Failed:', error)
 *     }
 *   );
 * };
 */
const useAsyncAction = (options = {}) => {
  const {
    initialLoading = false,
    onSuccess: globalOnSuccess,
    onError: globalOnError,
    showToast = null, // Toast 함수를 외부에서 주입
  } = options;

  const [loading, setLoading] = useState(initialLoading);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  /**
   * 비동기 작업 실행
   * @param {Function} asyncFn - 실행할 비동기 함수
   * @param {Object} actionOptions - 작업별 옵션
   * @returns {Promise<{success: boolean, data?: any, error?: Error}>}
   */
  const execute = useCallback(async (asyncFn, actionOptions = {}) => {
    const {
      successMessage,
      errorMessage,
      onSuccess,
      onError,
      resetOnExecute = true,
    } = actionOptions;

    try {
      if (resetOnExecute) {
        setError(null);
      }
      setLoading(true);

      const result = await asyncFn();
      setData(result);

      // 성공 콜백
      if (onSuccess) {
        onSuccess(result);
      }
      if (globalOnSuccess) {
        globalOnSuccess(result);
      }

      // 성공 토스트
      if (successMessage && showToast) {
        showToast.success(successMessage);
      }

      return { success: true, data: result };
    } catch (err) {
      const errorObj = err instanceof Error ? err : new Error(String(err));
      setError(errorObj);

      // 에러 콜백
      if (onError) {
        onError(errorObj);
      }
      if (globalOnError) {
        globalOnError(errorObj);
      }

      // 에러 토스트
      if (errorMessage && showToast) {
        showToast.error(errorMessage);
      } else if (showToast) {
        showToast.error(errorObj.message || '작업 중 오류가 발생했습니다.');
      }

      return { success: false, error: errorObj };
    } finally {
      setLoading(false);
    }
  }, [globalOnSuccess, globalOnError, showToast]);

  /**
   * 에러 상태 초기화
   */
  const reset = useCallback(() => {
    setError(null);
    setData(null);
    setLoading(false);
  }, []);

  /**
   * 에러만 초기화
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    execute,
    loading,
    error,
    data,
    reset,
    clearError,
    isLoading: loading,
    isError: !!error,
    isSuccess: !!data && !error,
  };
};

export default useAsyncAction;
