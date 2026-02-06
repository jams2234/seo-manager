import toastService from '../../services/toastService';
import React, { useState } from 'react';
import ModalOverlay from '../common/ModalOverlay';
import './FixHistoryModal.css';

const FixHistoryModal = ({ issue, onClose, onRevert, onUpdateFixValue, gitEnabled }) => {
  const [reverting, setReverting] = useState(false);
  const [deployRevert, setDeployRevert] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editedValue, setEditedValue] = useState(issue.suggested_value || '');

  const handleRevert = async () => {
    const deployMessage = deployRevert && gitEnabled && issue.deployed_to_git
      ? '\n\n🚀 변경 사항을 Git에서도 되돌립니다.'
      : '';

    if (!window.confirm(`이 이슈를 되돌리시겠습니까?${deployMessage}\n\n수정 전 상태로 복원됩니다.`)) {
      return;
    }

    try {
      setReverting(true);
      await onRevert(issue.id, deployRevert);
      toastService.success('이슈가 성공적으로 되돌려졌습니다!');
      onClose();
    } catch (err) {
      toastService.error('되돌리기 실패: ' + err.message);
    } finally {
      setReverting(false);
    }
  };

  const handleSaveEdit = async () => {
    if (!editedValue.trim()) {
      toastService.warning('수정값을 입력해주세요.');
      return;
    }

    if (editedValue === issue.suggested_value) {
      setEditing(false);
      return;
    }

    try {
      await onUpdateFixValue(issue.id, editedValue);
      const wasDeployed = issue.deployed_to_git;
      const message = wasDeployed
        ? '수정값이 업데이트되었습니다!\n\n⚠️ 변경 사항을 웹사이트에 반영하려면 다시 Git에 배포해야 합니다.'
        : '수정값이 업데이트되었습니다!';
      toastService.success(message);
      setEditing(false);
    } catch (err) {
      toastService.error('수정값 업데이트 실패: ' + err.message);
    }
  };

  return (
    <ModalOverlay onClose={onClose} className="modal-overlay">
      <div className="fix-history-modal">
        {/* Header */}
        <div className="modal-header">
          <h3>수정 내역</h3>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        {/* Issue Info */}
        <div className="modal-body">
          <div className="issue-info-section">
            <div className="info-row">
              <span className="info-label">이슈 타입:</span>
              <span className="info-value">{issue.issue_type}</span>
            </div>
            <div className="info-row">
              <span className="info-label">심각도:</span>
              <span className={`severity-badge ${issue.severity}`}>{issue.severity}</span>
            </div>
            <div className="info-row">
              <span className="info-label">상태:</span>
              <span className={`status-badge ${issue.status}`}>
                {issue.status === 'auto_fixed' ? 'AUTO-FIXED' : 'FIXED'}
              </span>
            </div>
          </div>

          {/* Title */}
          <div className="issue-title-section">
            <h4>{issue.title}</h4>
            {issue.message && <p className="issue-description">{issue.message}</p>}
          </div>

          {/* Before/After Comparison */}
          <div className="comparison-section">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h4 style={{ margin: 0 }}>변경 내역</h4>
              {issue.current_value && issue.suggested_value && !editing && (
                <button
                  className="btn-edit-value"
                  onClick={() => {
                    if (issue.deployed_to_git) {
                      if (!window.confirm('⚠️ 이 이슈는 이미 Git에 배포되었습니다.\n\n수정값을 변경하려면 다시 배포해야 합니다.\n계속하시겠습니까?')) {
                        return;
                      }
                    }
                    setEditing(true);
                  }}
                  style={{
                    padding: '6px 12px',
                    background: issue.deployed_to_git ? '#f59e0b' : '#3b82f6',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    fontSize: '12px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  title={issue.deployed_to_git ? '이미 배포된 이슈입니다. 수정 후 재배포 필요' : '수정값 변경'}
                >
                  ✏️ 수정값 변경
                </button>
              )}
            </div>

            {issue.current_value && issue.suggested_value ? (
              <>
                <div className="comparison-grid">
                  <div className="comparison-item before">
                    <div className="comparison-label">
                      <span className="label-icon">❌</span>
                      <span>수정 전</span>
                    </div>
                    <div className="comparison-value">{issue.current_value}</div>
                  </div>
                  <div className="comparison-arrow">→</div>
                  <div className="comparison-item after">
                    <div className="comparison-label">
                      <span className="label-icon">✅</span>
                      <span>수정 후</span>
                    </div>
                    {editing ? (
                      <textarea
                        className="comparison-value-edit"
                        value={editedValue}
                        onChange={(e) => setEditedValue(e.target.value)}
                        rows={3}
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '2px solid #3b82f6',
                          borderRadius: '4px',
                          fontSize: '14px',
                          fontFamily: 'inherit',
                          resize: 'vertical'
                        }}
                      />
                    ) : (
                      <div className="comparison-value">{issue.suggested_value}</div>
                    )}
                  </div>
                </div>
                {editing && (
                  <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                    <button
                      onClick={handleSaveEdit}
                      style={{
                        flex: 1,
                        padding: '8px',
                        background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        fontWeight: '600',
                        cursor: 'pointer'
                      }}
                    >
                      💾 저장
                    </button>
                    <button
                      onClick={() => {
                        setEditing(false);
                        setEditedValue(issue.suggested_value);
                      }}
                      style={{
                        flex: 1,
                        padding: '8px',
                        background: '#6b7280',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        fontWeight: '600',
                        cursor: 'pointer'
                      }}
                    >
                      취소
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div style={{
                background: '#f3f4f6',
                border: '1px dashed #d1d5db',
                borderRadius: '8px',
                padding: '20px',
                textAlign: 'center',
                color: '#6b7280'
              }}>
                <div style={{ fontSize: '24px', marginBottom: '8px' }}>📝</div>
                <div style={{ fontWeight: '600', marginBottom: '4px' }}>변경 내역 없음</div>
                <div style={{ fontSize: '13px' }}>
                  이전 버전에서 수정된 이슈입니다.<br />
                  변경 내역을 보려면 되돌린 후 다시 Auto-fix 하세요.
                </div>
              </div>
            )}
          </div>

          {/* Deployment Info */}
          <div className="deployment-info-section">
            <h4>배포 정보</h4>
            {issue.deployed_to_git ? (
              <div className="deployment-details success">
                <div className="deployment-row">
                  <span className="deployment-icon">✅</span>
                  <div className="deployment-content">
                    <div className="deployment-status">Git에 배포됨</div>
                    <div className="deployment-meta">
                      <div className="meta-item">
                        <strong>Commit:</strong>{' '}
                        <code>{issue.deployment_commit_hash?.substring(0, 7) || 'N/A'}</code>
                      </div>
                      <div className="meta-item">
                        <strong>배포일:</strong>{' '}
                        {issue.deployed_at
                          ? new Date(issue.deployed_at).toLocaleString('ko-KR')
                          : 'N/A'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="deployment-details warning">
                <div className="deployment-row">
                  <span className="deployment-icon">⚠️</span>
                  <div className="deployment-content">
                    <div className="deployment-status">데이터베이스에만 수정됨</div>
                    <div className="deployment-note">
                      실제 웹사이트에는 반영되지 않았습니다.
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Fix Suggestion */}
          {issue.fix_suggestion && (
            <div className="suggestion-section">
              <h4>권장 사항</h4>
              <p>{issue.fix_suggestion}</p>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="modal-footer">
          {gitEnabled && issue.deployed_to_git && (
            <label className="revert-deploy-checkbox">
              <input
                type="checkbox"
                checked={deployRevert}
                onChange={(e) => setDeployRevert(e.target.checked)}
              />
              <span>Git에서도 되돌리기</span>
            </label>
          )}
          <div className="footer-buttons">
            <button className="btn-secondary" onClick={onClose}>
              닫기
            </button>
            <button
              className="btn-revert"
              onClick={handleRevert}
              disabled={reverting}
            >
              {reverting ? '되돌리는 중...' : '🔄 수정 되돌리기'}
            </button>
          </div>
        </div>
      </div>
    </ModalOverlay>
  );
};

export default FixHistoryModal;
