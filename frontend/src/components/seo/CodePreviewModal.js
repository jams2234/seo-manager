import React from 'react';
import './CodePreviewModal.css';

const CodePreviewModal = ({
  isOpen,
  onClose,
  onConfirm,
  previewData,
  loading
}) => {
  if (!isOpen) return null;

  return (
    <div className="code-preview-overlay" onClick={onClose}>
      <div className="code-preview-modal" onClick={e => e.stopPropagation()}>
        <div className="code-preview-header">
          <h3>코드 변경 미리보기</h3>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        {loading ? (
          <div className="code-preview-loading">
            <div className="spinner"></div>
            <p>코드 변경사항을 분석 중...</p>
          </div>
        ) : previewData ? (
          <div className="code-preview-content">
            {/* File Info */}
            <div className="file-info">
              <span className="project-badge">{previewData.project_type}</span>
              <span className="file-path">{previewData.file_path}</span>
            </div>

            {/* Value Summary */}
            <div className="value-summary">
              <div className="value-row">
                <span className="label">현재 값:</span>
                <span className="value old">{previewData.old_value || '(없음)'}</span>
              </div>
              <div className="value-row">
                <span className="label">수정 값:</span>
                <span className="value new">{previewData.new_value}</span>
              </div>
            </div>

            {/* Code Diff */}
            <div className="code-diff-container">
              <div className="code-panel before">
                <div className="panel-header">
                  <span className="indicator">−</span>
                  수정 전
                </div>
                <pre className="code-block">
                  <code>{previewData.before_code}</code>
                </pre>
              </div>

              <div className="code-panel after">
                <div className="panel-header">
                  <span className="indicator">+</span>
                  수정 후
                </div>
                <pre className="code-block">
                  <code>{previewData.after_code}</code>
                </pre>
              </div>
            </div>

            {/* Info Note */}
            <div className="info-note">
              <span className="icon">ℹ️</span>
              <span>
                'Auto-fix 적용' 클릭 시 위 변경사항이 적용됩니다.
                Git 배포 시 실제 코드 파일이 수정됩니다.
              </span>
            </div>
          </div>
        ) : (
          <div className="code-preview-error">
            <p>미리보기를 불러올 수 없습니다.</p>
          </div>
        )}

        <div className="code-preview-actions">
          <button className="btn-cancel" onClick={onClose}>
            취소
          </button>
          <button
            className="btn-confirm"
            onClick={onConfirm}
            disabled={loading || !previewData}
          >
            Auto-fix 적용
          </button>
        </div>
      </div>
    </div>
  );
};

export default CodePreviewModal;
