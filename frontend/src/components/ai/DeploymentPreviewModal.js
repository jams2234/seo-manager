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
  const [isDeploying, setIsDeploying] = useState(false);

  if (!isOpen) return null;

  // Git 설정 상태 확인
  const gitConfig = previewData?.git_config || {};
  const canDeployToGit = gitConfig.can_deploy;

  const handleConfirm = async () => {
    setIsDeploying(true);
    try {
      // 항상 Git 배포 시도 (Git 설정이 되어 있으면)
      await onConfirm(canDeployToGit);
    } finally {
      setIsDeploying(false);
    }
  };

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

                {canDeployToGit ? (
                  <>
                    <div className="git-config-status">
                      <div className="config-item ok">
                        <span className="status-icon">✅</span>
                        <span>Git 배포 준비 완료</span>
                      </div>
                      <div className="config-item ok">
                        <span className="status-icon">📦</span>
                        <span>저장소: {gitConfig.repository}</span>
                      </div>
                      <div className="config-item">
                        <span className="status-icon">🌿</span>
                        <span>브랜치: {gitConfig.branch || 'main'}</span>
                      </div>
                    </div>

                    {gitChanges.length > 0 && (
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

                    <div className="deploy-notice success">
                      <span className="notice-icon">✨</span>
                      <span>DB 수정과 함께 Git 저장소에 자동 배포됩니다.</span>
                    </div>
                  </>
                ) : (
                  <div className="git-config-status">
                    <div className="config-item disabled">
                      <span className="status-icon">⚠️</span>
                      <span>Git 배포 설정이 필요합니다</span>
                    </div>
                    {!gitConfig.enabled && (
                      <div className="config-item missing">
                        <span className="status-icon">❌</span>
                        <span>Git 배포가 비활성화 상태입니다</span>
                      </div>
                    )}
                    {gitConfig.enabled && !gitConfig.repository && (
                      <div className="config-item missing">
                        <span className="status-icon">❌</span>
                        <span>Git 저장소가 설정되지 않았습니다</span>
                      </div>
                    )}
                    {gitConfig.enabled && gitConfig.repository && !gitConfig.has_token && (
                      <div className="config-item missing">
                        <span className="status-icon">❌</span>
                        <span>Git 토큰이 설정되지 않았습니다</span>
                      </div>
                    )}
                    <div className="deploy-notice warning">
                      <span className="notice-icon">⚠️</span>
                      <span>DB에만 수정됩니다. 웹사이트에 반영하려면 Git 설정을 완료하세요.</span>
                    </div>
                  </div>
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
                {canDeployToGit ? '배포 중...' : '적용 중...'}
              </>
            ) : (
              <>
                {canDeployToGit ? '✅ 적용 및 Git 배포' : '⚠️ DB에만 적용'}
              </>
            )}
          </button>
        </div>
      </div>
    </ModalOverlay>
  );
};

export default DeploymentPreviewModal;
