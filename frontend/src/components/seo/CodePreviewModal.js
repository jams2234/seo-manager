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
            <p>{previewData?.ai_generated !== false ? '🤖 AI가 최적의 수정안을 분석 중...' : '코드 변경사항을 분석 중...'}</p>
          </div>
        ) : previewData ? (
          <div className="code-preview-content">
            {/* AI Badge - Show if AI-generated */}
            {previewData.ai_generated && (
              <div className="ai-badge-container" style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 12px',
                background: 'linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%)',
                borderRadius: '8px',
                marginBottom: '12px',
                border: '1px solid #a5b4fc'
              }}>
                <span style={{ fontSize: '18px' }}>🤖</span>
                <span style={{ fontWeight: '600', color: '#4338ca' }}>AI 생성 수정안</span>
                {previewData.ai_confidence && (
                  <span style={{
                    marginLeft: 'auto',
                    padding: '2px 8px',
                    background: previewData.ai_confidence >= 0.8 ? '#d1fae5' : previewData.ai_confidence >= 0.6 ? '#fef3c7' : '#fee2e2',
                    color: previewData.ai_confidence >= 0.8 ? '#059669' : previewData.ai_confidence >= 0.6 ? '#d97706' : '#dc2626',
                    borderRadius: '4px',
                    fontSize: '12px',
                    fontWeight: '600'
                  }}>
                    신뢰도 {Math.round(previewData.ai_confidence * 100)}%
                  </span>
                )}
              </div>
            )}

            {/* Fallback warning */}
            {previewData.ai_fallback_reason && (
              <div style={{
                padding: '8px 12px',
                background: '#fef3c7',
                borderRadius: '8px',
                marginBottom: '12px',
                fontSize: '13px',
                color: '#92400e',
                border: '1px solid #fcd34d'
              }}>
                ⚠️ AI 분석 실패로 규칙 기반 수정안을 표시합니다.
              </div>
            )}

            {/* File Info */}
            <div className="file-info">
              <span className="project-badge">{previewData.project_type || previewData.issue_type}</span>
              <span className="file-path">{previewData.file_path}</span>
            </div>

            {/* Value Summary */}
            <div className="value-summary">
              <div className="value-row">
                <span className="label">현재 값:</span>
                <span className="value old">{previewData.old_value || previewData.current_value || '(없음)'}</span>
              </div>
              <div className="value-row">
                <span className="label">수정 값:</span>
                <span className="value new">{previewData.new_value || previewData.suggested_value}</span>
              </div>
            </div>

            {/* AI Explanation */}
            {previewData.ai_explanation && (
              <div style={{
                padding: '12px',
                background: '#f0fdf4',
                borderRadius: '8px',
                marginBottom: '12px',
                border: '1px solid #86efac'
              }}>
                <div style={{ fontWeight: '600', color: '#166534', marginBottom: '4px', fontSize: '13px' }}>
                  💡 AI 분석 설명:
                </div>
                <div style={{ fontSize: '13px', color: '#15803d', lineHeight: '1.5' }}>
                  {previewData.ai_explanation}
                </div>
              </div>
            )}

            {/* Code Diff */}
            <div className="code-diff-container">
              <div className="code-panel before">
                <div className="panel-header">
                  <span className="indicator">−</span>
                  수정 전
                </div>
                <pre className="code-block">
                  <code>{previewData.before_code || previewData.current_value || '(없음)'}</code>
                </pre>
              </div>

              <div className="code-panel after">
                <div className="panel-header">
                  <span className="indicator">+</span>
                  수정 후
                </div>
                <pre className="code-block">
                  <code>{previewData.after_code || previewData.suggested_value}</code>
                </pre>
              </div>
            </div>

            {/* Info Note */}
            <div className="info-note">
              <span className="icon">ℹ️</span>
              <span>
                {previewData.ai_generated
                  ? 'AI가 SEO 데이터를 분석하여 최적의 수정안을 생성했습니다. '
                  : ''
                }
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
            style={previewData?.ai_generated ? {
              background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)'
            } : {}}
          >
            {previewData?.ai_generated ? '🤖 AI 수정 적용' : 'Auto-fix 적용'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CodePreviewModal;
