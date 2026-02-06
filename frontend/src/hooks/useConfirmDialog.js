/**
 * useConfirmDialog Hook
 * Promise 기반 확인 다이얼로그 관리 훅
 */
import { useState, useCallback, useRef } from 'react';

/**
 * window.confirm() 대체를 위한 Promise 기반 확인 다이얼로그
 *
 * @example
 * const { confirm, dialogState, closeDialog, ConfirmDialog } = useConfirmDialog();
 *
 * const handleDelete = async () => {
 *   const confirmed = await confirm({
 *     title: '삭제 확인',
 *     message: '정말 삭제하시겠습니까?',
 *     confirmText: '삭제',
 *     cancelText: '취소',
 *     type: 'danger'
 *   });
 *
 *   if (confirmed) {
 *     // 삭제 실행
 *   }
 * };
 *
 * // JSX에서 렌더링
 * {dialogState.isOpen && <ConfirmDialog />}
 */
const useConfirmDialog = () => {
  const [dialogState, setDialogState] = useState({
    isOpen: false,
    title: '',
    message: '',
    confirmText: '확인',
    cancelText: '취소',
    type: 'default', // 'default' | 'danger' | 'warning'
    details: null,
  });

  const resolveRef = useRef(null);

  /**
   * 확인 다이얼로그 표시
   * @param {Object} options - 다이얼로그 옵션
   * @returns {Promise<boolean>} - 확인 시 true, 취소 시 false
   */
  const confirm = useCallback((options = {}) => {
    return new Promise((resolve) => {
      resolveRef.current = resolve;
      setDialogState({
        isOpen: true,
        title: options.title || '확인',
        message: options.message || '진행하시겠습니까?',
        confirmText: options.confirmText || '확인',
        cancelText: options.cancelText || '취소',
        type: options.type || 'default',
        details: options.details || null,
      });
    });
  }, []);

  /**
   * 다이얼로그 닫기 (취소)
   */
  const closeDialog = useCallback(() => {
    if (resolveRef.current) {
      resolveRef.current(false);
      resolveRef.current = null;
    }
    setDialogState(prev => ({ ...prev, isOpen: false }));
  }, []);

  /**
   * 확인 처리
   */
  const handleConfirm = useCallback(() => {
    if (resolveRef.current) {
      resolveRef.current(true);
      resolveRef.current = null;
    }
    setDialogState(prev => ({ ...prev, isOpen: false }));
  }, []);

  /**
   * 기본 ConfirmDialog 컴포넌트
   * 커스텀 스타일이 필요하면 별도로 구현 가능
   */
  const ConfirmDialog = useCallback(() => {
    if (!dialogState.isOpen) return null;

    const getButtonStyle = () => {
      switch (dialogState.type) {
        case 'danger':
          return {
            background: '#ef4444',
            hoverBackground: '#dc2626',
          };
        case 'warning':
          return {
            background: '#f59e0b',
            hoverBackground: '#d97706',
          };
        default:
          return {
            background: '#667eea',
            hoverBackground: '#5a6fd6',
          };
      }
    };

    const buttonStyle = getButtonStyle();

    return (
      <div
        className="confirm-dialog-backdrop"
        onClick={closeDialog}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}
      >
        <div
          className="confirm-dialog"
          onClick={e => e.stopPropagation()}
          style={{
            background: 'white',
            borderRadius: '12px',
            padding: '24px',
            maxWidth: '400px',
            width: '90%',
            boxShadow: '0 10px 40px rgba(0, 0, 0, 0.2)',
          }}
        >
          <h3 style={{
            margin: '0 0 12px 0',
            fontSize: '18px',
            fontWeight: '600',
            color: '#1e293b',
          }}>
            {dialogState.title}
          </h3>

          <p style={{
            margin: '0 0 8px 0',
            fontSize: '14px',
            color: '#64748b',
            lineHeight: '1.5',
          }}>
            {dialogState.message}
          </p>

          {dialogState.details && (
            <div style={{
              margin: '12px 0',
              padding: '12px',
              background: '#f8fafc',
              borderRadius: '8px',
              fontSize: '13px',
              color: '#475569',
            }}>
              {dialogState.details}
            </div>
          )}

          <div style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '8px',
            marginTop: '20px',
          }}>
            <button
              onClick={closeDialog}
              style={{
                padding: '10px 20px',
                background: '#f3f4f6',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                color: '#64748b',
                cursor: 'pointer',
              }}
            >
              {dialogState.cancelText}
            </button>
            <button
              onClick={handleConfirm}
              style={{
                padding: '10px 20px',
                background: buttonStyle.background,
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                color: 'white',
                cursor: 'pointer',
              }}
            >
              {dialogState.confirmText}
            </button>
          </div>
        </div>
      </div>
    );
  }, [dialogState, closeDialog, handleConfirm]);

  return {
    confirm,
    dialogState,
    closeDialog,
    handleConfirm,
    ConfirmDialog,
  };
};

export default useConfirmDialog;
