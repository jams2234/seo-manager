/**
 * useNodeActions Hook
 * Manages node actions: subdomain toggle, visibility toggle, group assignment
 */
import { useRef } from 'react';
import { pageService } from '../services/domainService';

/**
 * Custom hook for node action handlers
 * @param {number} pageId - Page ID
 * @param {boolean} isSubdomain - Current subdomain status
 * @param {boolean} isVisible - Current visibility status
 * @param {Function} onUpdate - Callback to refresh data after update
 * @returns {Object} Action handlers
 */
const useNodeActions = (pageId, isSubdomain, isVisible, onUpdate) => {
  const isMountedRef = useRef(true);

  /**
   * Handle subdomain toggle
   */
  const handleSubdomainToggle = async (e) => {
    e.stopPropagation();

    const newValue = !isSubdomain;
    const confirmed = window.confirm(
      `이 페이지를 ${newValue ? '서브도메인' : '일반 페이지'}으로 변경하시겠습니까?`
    );

    if (!confirmed) return;

    try {
      await pageService.updatePage(pageId, {
        is_subdomain: newValue
      });

      if (isMountedRef.current) {
        alert(`${newValue ? '서브도메인' : '일반 페이지'}으로 변경되었습니다!`);
        if (onUpdate) {
          onUpdate();
        }
      }
    } catch (error) {
      console.error('Failed to toggle subdomain:', error);
      if (isMountedRef.current) {
        alert('서브도메인 토글 실패: ' + (error.response?.data?.error || error.message));
      }
    }
  };

  /**
   * Handle visibility toggle
   */
  const handleVisibilityToggle = async (e) => {
    e.stopPropagation();

    const newValue = isVisible === false ? true : false;
    const confirmed = window.confirm(
      `이 페이지를 ${newValue ? '보이기' : '숨기기'} 하시겠습니까?`
    );

    if (!confirmed) return;

    try {
      await pageService.updatePage(pageId, {
        is_visible: newValue
      });

      if (isMountedRef.current) {
        alert('페이지 가시성이 변경되었습니다!');
        if (onUpdate) {
          onUpdate();
        }
      }
    } catch (error) {
      console.error('Failed to toggle visibility:', error);
      if (isMountedRef.current) {
        alert('가시성 토글 실패: ' + (error.response?.data?.error || error.message));
      }
    }
  };

  /**
   * Handle group assignment change
   */
  const handleGroupChange = async (e) => {
    e.stopPropagation();
    const groupId = e.target.value === '' ? null : parseInt(e.target.value);

    try {
      await pageService.assignGroup(pageId, groupId);

      if (isMountedRef.current) {
        if (onUpdate) {
          onUpdate();
        }
      }
    } catch (error) {
      console.error('Failed to assign group:', error);
      if (isMountedRef.current) {
        alert('그룹 할당 실패: ' + (error.response?.data?.error || error.message));
      }
    }
  };

  return {
    handleSubdomainToggle,
    handleVisibilityToggle,
    handleGroupChange,
  };
};

export default useNodeActions;
