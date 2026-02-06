/**
 * Add Page Modal Component
 * Modal for adding a new child page in edit mode
 */
import React, { useState, useRef, useEffect } from 'react';
import ModalOverlay from '../common/ModalOverlay';
import './AddPageModal.css';

const AddPageModal = ({ parentUrl, domainUrl, onClose, onSubmit }) => {
  const [path, setPath] = useState('');
  const [title, setTitle] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inputRef = useRef(null);

  // Focus input on mount
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  // Get base URL from parent
  const getBaseUrl = () => {
    try {
      const urlObj = new URL(parentUrl);
      return `${urlObj.protocol}//${urlObj.host}`;
    } catch {
      return domainUrl || '';
    }
  };

  // Get parent path
  const getParentPath = () => {
    try {
      const urlObj = new URL(parentUrl);
      return urlObj.pathname;
    } catch {
      return '/';
    }
  };

  // Validate and create full URL
  const getFullUrl = () => {
    const baseUrl = getBaseUrl();
    const parentPath = getParentPath();

    // Clean up the path
    let cleanPath = path.trim();
    if (!cleanPath) return '';

    // Remove leading slash if present (we'll add it)
    if (cleanPath.startsWith('/')) {
      cleanPath = cleanPath.substring(1);
    }

    // Combine parent path with new path
    const fullPath = parentPath.endsWith('/')
      ? `${parentPath}${cleanPath}`
      : `${parentPath}/${cleanPath}`;

    return `${baseUrl}${fullPath}`;
  };

  // Handle form submit
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!path.trim()) {
      setError('URL 경로를 입력해주세요.');
      return;
    }

    const fullUrl = getFullUrl();
    if (!fullUrl) {
      setError('유효한 URL을 생성할 수 없습니다.');
      return;
    }

    // Validate URL format
    try {
      new URL(fullUrl);
    } catch {
      setError('유효하지 않은 URL 형식입니다.');
      return;
    }

    setIsSubmitting(true);
    try {
      const urlObj = new URL(fullUrl);
      await onSubmit({
        url: fullUrl,
        path: urlObj.pathname,
        title: title.trim() || undefined
      });
    } catch (err) {
      setError(err.message || '페이지 생성에 실패했습니다.');
      setIsSubmitting(false);
    }
  };

  return (
    <ModalOverlay onClose={onClose} className="add-page-modal-backdrop">
      <div className="add-page-modal">
        <div className="add-page-modal-header">
          <h3>자식 페이지 추가</h3>
          <button className="add-page-modal-close" onClick={onClose}>
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="add-page-modal-body">
            {/* Parent URL Display */}
            <div className="form-group">
              <label>부모 페이지</label>
              <div className="parent-url-display">
                {parentUrl}
              </div>
            </div>

            {/* Path Input */}
            <div className="form-group">
              <label htmlFor="page-path">URL 경로 *</label>
              <div className="path-input-wrapper">
                <span className="path-prefix">{getParentPath()}</span>
                <input
                  ref={inputRef}
                  id="page-path"
                  type="text"
                  value={path}
                  onChange={(e) => setPath(e.target.value)}
                  placeholder="new-page"
                  disabled={isSubmitting}
                />
              </div>
              {path && (
                <div className="url-preview">
                  미리보기: {getFullUrl()}
                </div>
              )}
            </div>

            {/* Title Input */}
            <div className="form-group">
              <label htmlFor="page-title">페이지 제목 (선택)</label>
              <input
                id="page-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="페이지 제목"
                disabled={isSubmitting}
              />
            </div>

            {/* Error Display */}
            {error && (
              <div className="add-page-error">
                {error}
              </div>
            )}
          </div>

          <div className="add-page-modal-footer">
            <button
              type="button"
              className="btn-cancel"
              onClick={onClose}
              disabled={isSubmitting}
            >
              취소
            </button>
            <button
              type="submit"
              className="btn-submit"
              disabled={isSubmitting || !path.trim()}
            >
              {isSubmitting ? '생성 중...' : '추가'}
            </button>
          </div>
        </form>
      </div>
    </ModalOverlay>
  );
};

export default AddPageModal;
