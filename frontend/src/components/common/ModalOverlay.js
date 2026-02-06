/**
 * 공통 모달 오버레이 컴포넌트
 *
 * 모든 모달에서 공통으로 사용하는 백드롭 + 중앙 정렬 컨테이너
 *
 * @example
 * <ModalOverlay onClose={handleClose} className="my-modal">
 *   <div className="modal-content">...</div>
 * </ModalOverlay>
 */
import React, { useEffect, useCallback } from 'react';
import './ModalOverlay.css';

const ModalOverlay = ({
  children,
  onClose,
  className = '',
  closeOnBackdrop = true,
  closeOnEscape = true,
  preventBodyScroll = true,
}) => {
  // ESC 키로 닫기
  const handleKeyDown = useCallback((e) => {
    if (closeOnEscape && e.key === 'Escape') {
      onClose?.();
    }
  }, [closeOnEscape, onClose]);

  // 키보드 이벤트 및 body 스크롤 제어
  useEffect(() => {
    if (closeOnEscape) {
      document.addEventListener('keydown', handleKeyDown);
    }

    // body 스크롤 방지
    if (preventBodyScroll) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';

      return () => {
        document.body.style.overflow = originalOverflow;
        if (closeOnEscape) {
          document.removeEventListener('keydown', handleKeyDown);
        }
      };
    }

    return () => {
      if (closeOnEscape) {
        document.removeEventListener('keydown', handleKeyDown);
      }
    };
  }, [closeOnEscape, preventBodyScroll, handleKeyDown]);

  // 백드롭 클릭 핸들러
  const handleBackdropClick = (e) => {
    if (closeOnBackdrop && e.target === e.currentTarget) {
      onClose?.();
    }
  };

  // 모달 내부 클릭 시 이벤트 전파 중지
  const handleModalClick = (e) => {
    e.stopPropagation();
  };

  return (
    <div
      className={`modal-overlay-backdrop ${className}`}
      onClick={handleBackdropClick}
    >
      <div className="modal-overlay-container" onClick={handleModalClick}>
        {children}
      </div>
    </div>
  );
};

export default ModalOverlay;
