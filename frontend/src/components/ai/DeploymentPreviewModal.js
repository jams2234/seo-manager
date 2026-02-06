import React, { useState, useEffect } from 'react';
import ModalOverlay from '../common/ModalOverlay';
import { getTypeLabel } from '../../utils/aiUtils';
import './DeploymentPreviewModal.css';

/**
 * 배포 미리보기 모달
 *
 * AI 제안 수락 전에 어떤 변경이 이루어지는지 미리보기 제공
 */
const DeploymentPreviewModal = ({
  isOpen,
  onClose,
  suggestion,
  previewData,
  loading,
  onConfirm,
}) => {
  const [deployToGit, setDeployToGit] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);

  useEffect(() => {
    // Git 배포 가능하면 기본 체크
    if (previewData?.git_config?.can_deploy) {
      setDeployToGit(true);
    }
  }, [previewData]);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    setIsDeploying(true);
    try {
      await onConfirm(deployToGit);
    } finally {
      setIsDeploying(false);
    }
  };

  const gitConfig = previewData?.git_config || {};
  const dbChanges = previewData?.db_changes || [];
  const gitChanges = previewData?.git_changes || [];
  const warnings = previewData?.warnings || [];

  return (
    <ModalOverlay onClose={onClose} className="deployment-preview-overlay">
      <div className="deployment-preview-modal">
        <div className="deployment-preview-header">
          <h2>배포 미리보기</h2>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="deployment-preview-content">
          {loading ? (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>미리보기 로딩 중...</p>
            </div>
          ) : (
            <>
              {/* 제안 정보 */}
              <div className="preview-section suggestion-info">
                <h3>제안 정보</h3>
                <div className="info-grid">
                  <div className="info-item">
                    <span className="label">유형</span>
                    <span className="value">{getTypeLabel(suggestion?.suggestion_type)}</span>
                  </div>
                  <div className="info-item">
                    <span className="label">페이지</span>
                    <span className="value">{previewData?.page_url || '없음'}</span>
                  </div>
                  <div className="info-item">
                    <span className="label">자동 적용</span>
                    <span className={`value ${previewData?.is_auto_applicable ? 'yes' : 'no'}`}>
                      {previewData?.is_auto_applicable ? '가능' : '불가'}
                    </span>
                  </div>
                </div>
              </div>

              {/* 경고 메시지 */}
              {warnings.length > 0 && (
                <div className="preview-section warnings">
                  <h3>주의사항</h3>
                  {warnings.map((warning, idx) => (
                    <div key={idx} className={`warning-item ${warning.type}`}>
                      <span className="warning-icon">⚠️</span>
                      <span>{warning.message}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* DB 변경 사항 */}
              <div className="preview-section db-changes">
                <h3>
                  <span className="section-icon">🗄️</span>
                  DB 변경 사항
                </h3>
                {dbChanges.length > 0 ? (
                  <div className="changes-list">
                    {dbChanges.map((change, idx) => (
                      <div key={idx} className="change-item">
                        <div className="change-header">
                          <span className="table-name">{change.table}</span>
                          <span className="field-name">.{change.field}</span>
                        </div>
                        <div className="change-diff">
                          <div className="diff-line removed">
                            <span className="diff-symbol">-</span>
                            <span className="diff-content">{change.current}</span>
                          </div>
                          <div className="diff-line added">
                            <span className="diff-symbol">+</span>
                            <span className="diff-content">{change.new}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="no-changes">DB 변경 사항이 없습니다.</p>
                )}
              </div>

              {/* Git 배포 설정 */}
              <div className="preview-section git-deployment">
                <h3>
                  <span className="section-icon">🚀</span>
                  Git 배포
                </h3>

                <div className="git-config-status">
                  <div className={`config-item ${gitConfig.enabled ? 'ok' : 'disabled'}`}>
                    <span className="status-icon">{gitConfig.enabled ? '✅' : '❌'}</span>
                    <span>Git 배포 {gitConfig.enabled ? '활성화' : '비활성화'}</span>
                  </div>
                  {gitConfig.enabled && (
                    <>
                      <div className={`config-item ${gitConfig.repository ? 'ok' : 'missing'}`}>
                        <span className="status-icon">{gitConfig.repository ? '✅' : '❌'}</span>
                        <span>저장소: {gitConfig.repository || '미설정'}</span>
                      </div>
                      <div className={`config-item ${gitConfig.has_token ? 'ok' : 'missing'}`}>
                        <span className="status-icon">{gitConfig.has_token ? '✅' : '❌'}</span>
                        <span>인증 토큰: {gitConfig.has_token ? '설정됨' : '미설정'}</span>
                      </div>
                      <div className="config-item">
                        <span className="status-icon">🌿</span>
                        <span>브랜치: {gitConfig.branch || 'main'}</span>
                      </div>
                    </>
                  )}
                </div>

                {gitConfig.can_deploy && gitChanges.length > 0 && (
                  <div className="git-changes">
                    <h4>변경될 파일</h4>
                    {gitChanges.map((change, idx) => (
                      <div key={idx} className="git-change-item">
                        <div className="change-type">{change.type === 'sitemap_update' ? '📄 Sitemap' : '📝 메타데이터'}</div>
                        <div className="change-description">{change.description}</div>
                        {change.possible_files && (
                          <div className="possible-files">
                            <span className="label">대상 파일 (예상):</span>
                            <ul>
                              {change.possible_files.map((file, fIdx) => (
                                <li key={fIdx}>{file}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {change.type === 'metadata_update' && (
                          <div className="new-value">
                            <span className="label">{change.field}:</span>
                            <code>{change.new_value}</code>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {gitConfig.can_deploy && (
                  <label className="deploy-option">
                    <input
                      type="checkbox"
                      checked={deployToGit}
                      onChange={(e) => setDeployToGit(e.target.checked)}
                    />
                    <span>Git 저장소에 배포 (Vercel 자동 배포 트리거)</span>
                  </label>
                )}
              </div>
            </>
          )}
        </div>

        <div className="deployment-preview-footer">
          <button className="cancel-btn" onClick={onClose} disabled={isDeploying}>
            취소
          </button>
          <button
            className="confirm-btn"
            onClick={handleConfirm}
            disabled={loading || isDeploying || !previewData?.is_auto_applicable}
          >
            {isDeploying ? (
              <>
                <span className="spinner-small"></span>
                배포 중...
              </>
            ) : (
              <>
                {deployToGit ? '적용 및 Git 배포' : 'DB에 적용'}
              </>
            )}
          </button>
        </div>
      </div>
    </ModalOverlay>
  );
};

export default DeploymentPreviewModal;
