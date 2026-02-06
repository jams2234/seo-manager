/**
 * AI Suggestion Preview Modal Component
 * 제안 적용 전 미리보기 모달
 */
import React, { useState, useEffect } from 'react';
import { aiSuggestionService } from '../../services/aiLearningService';
import DeploymentPreviewModal from './DeploymentPreviewModal';
import { getTypeIcon, isAutoApplicableType } from '../../utils/aiUtils';
import './AISuggestionPreviewModal.css';

const AISuggestionPreviewModal = ({ suggestion, onClose, onAccept }) => {
  const [loading, setLoading] = useState(false);
  const [previewData, setPreviewData] = useState(null);

  // 배포 미리보기 모달 상태
  const [showDeploymentPreview, setShowDeploymentPreview] = useState(false);
  const [deploymentPreviewData, setDeploymentPreviewData] = useState(null);
  const [deploymentPreviewLoading, setDeploymentPreviewLoading] = useState(false);

  // Git 배포 가능 여부
  const canDeployToGit = suggestion.is_auto_applicable &&
    isAutoApplicableType(suggestion.suggestion_type);

  useEffect(() => {
    // action_data에서 미리보기 데이터 추출
    if (suggestion.action_data) {
      setPreviewData(suggestion.action_data);
    }
  }, [suggestion]);

  // 배포 미리보기 열기
  const handleShowDeploymentPreview = async () => {
    setDeploymentPreviewLoading(true);
    setShowDeploymentPreview(true);

    try {
      const response = await aiSuggestionService.previewDeployment(suggestion.id);
      setDeploymentPreviewData(response.data);
    } catch (error) {
      console.error('미리보기 로딩 실패:', error);
      setDeploymentPreviewData({
        success: false,
        error: '미리보기를 로드할 수 없습니다.',
      });
    } finally {
      setDeploymentPreviewLoading(false);
    }
  };

  // 배포 미리보기에서 확인
  const handleDeploymentConfirm = async (deployToGitFlag) => {
    setLoading(true);
    try {
      await onAccept(suggestion.id, deployToGitFlag);
      setShowDeploymentPreview(false);
      onClose();
    } catch (error) {
      console.error('수락 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  // Diff 스타일 표시 (항상 변경 전/후 모두 표시)
  const renderDiff = (oldValue, newValue, options = {}) => {
    const { alwaysShowBoth = false, emptyOldLabel = '(현재 값 없음)' } = options;
    if (!oldValue && !newValue) return null;

    // 변경 전 값이 없지만 변경 후 값이 있고, alwaysShowBoth가 true인 경우
    const showOld = oldValue || alwaysShowBoth;
    const showNew = newValue;

    return (
      <div className="diff-container">
        {showOld && (
          <div className="diff-section old">
            <div className="diff-header">
              <span className="diff-icon">➖</span>
              <span className="diff-label">변경 전</span>
            </div>
            <div className={`diff-content ${!oldValue ? 'empty' : ''}`}>
              {oldValue || emptyOldLabel}
            </div>
          </div>
        )}
        {showNew && (
          <div className="diff-section new">
            <div className="diff-header">
              <span className="diff-icon">➕</span>
              <span className="diff-label">변경 후</span>
            </div>
            <div className="diff-content">{newValue}</div>
          </div>
        )}
      </div>
    );
  };

  // 수락 핸들러 (간단한 수락 - Git 배포 없이)
  const handleAccept = async () => {
    // bulk fix 타입이거나 자동 적용 가능하고 페이지가 있으면 배포 미리보기 표시
    const isBulkFix = ['bulk_fix_descriptions', 'bulk_fix_titles'].includes(suggestion.suggestion_type);
    const hasAffectedPages = previewData?.affected_pages?.length > 0;

    if (suggestion.is_auto_applicable && (suggestion.page || (isBulkFix && hasAffectedPages))) {
      handleShowDeploymentPreview();
      return;
    }

    // 수동 적용 제안은 바로 수락
    setLoading(true);
    try {
      await onAccept(suggestion.id, false);
      onClose();
    } catch (error) {
      console.error('수락 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="preview-modal-backdrop" onClick={onClose}>
      <div className="preview-modal" onClick={(e) => e.stopPropagation()}>
        {/* 헤더 */}
        <div className="preview-header">
          <div className="preview-title">
            <span className="preview-icon">{getTypeIcon(suggestion.suggestion_type)}</span>
            <h3>제안 미리보기</h3>
          </div>
          <button className="preview-close" onClick={onClose}>×</button>
        </div>

        {/* 제안 정보 */}
        <div className="preview-info">
          <h4>{suggestion.title}</h4>
          <p className="preview-description">{suggestion.description}</p>

          {suggestion.page_url && (
            <div className="preview-page">
              <span className="page-icon">📄</span>
              <span className="page-url">{suggestion.page_url}</span>
            </div>
          )}
        </div>

        {/* 변경 내용 미리보기 */}
        <div className="preview-content">
          <h5>변경 내용</h5>

          {previewData ? (
            <div className="preview-changes">
              {/* 제목 변경 - title/bulk_fix_titles 타입에서만 표시 */}
              {['title', 'bulk_fix_titles'].includes(suggestion.suggestion_type) && previewData.new_title && (
                <div className="change-item">
                  <div className="change-label">📝 제목</div>
                  {renderDiff(
                    previewData.old_title,
                    previewData.new_title,
                    { alwaysShowBoth: true, emptyOldLabel: '(현재 제목 없음)' }
                  )}
                </div>
              )}

              {/* 설명 변경 - description/bulk_fix_descriptions 타입에서만 표시 */}
              {['description', 'bulk_fix_descriptions'].includes(suggestion.suggestion_type) && previewData.new_description && (
                <div className="change-item">
                  <div className="change-label">📋 메타 설명</div>
                  {renderDiff(
                    previewData.old_description,
                    previewData.new_description,
                    { alwaysShowBoth: true, emptyOldLabel: '(현재 메타 설명 없음)' }
                  )}
                </div>
              )}

              {/* 콘텐츠 변경 */}
              {(previewData.old_content || previewData.new_content) && (
                <div className="change-item">
                  <div className="change-label">📄 콘텐츠</div>
                  {renderDiff(previewData.old_content, previewData.new_content)}
                </div>
              )}

              {/* 코드 변경 */}
              {(previewData.old_code || previewData.new_code) && (
                <div className="change-item">
                  <div className="change-label">💻 코드</div>
                  <div className="diff-container code">
                    {previewData.old_code && (
                      <div className="diff-section old">
                        <div className="diff-header">
                          <span className="diff-icon">➖</span>
                          <span className="diff-label">이전 코드</span>
                        </div>
                        <pre className="diff-code">{previewData.old_code}</pre>
                      </div>
                    )}
                    {previewData.new_code && (
                      <div className="diff-section new">
                        <div className="diff-header">
                          <span className="diff-icon">➕</span>
                          <span className="diff-label">변경 코드</span>
                        </div>
                        <pre className="diff-code">{previewData.new_code}</pre>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 일반 변경 사항 */}
              {previewData.changes && Array.isArray(previewData.changes) && (
                <div className="change-item">
                  <div className="change-label">📋 변경 사항</div>
                  <ul className="changes-list">
                    {previewData.changes.map((change, idx) => (
                      <li key={idx}>{change}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 수동 가이드 */}
              {previewData.manual_guide && (
                <div className="change-item manual-guide">
                  <div className="change-label">📖 수동 적용 가이드</div>
                  <div className="guide-content">
                    {previewData.manual_guide}
                  </div>
                </div>
              )}

              {/* 키워드 최적화 */}
              {previewData.keywords && Array.isArray(previewData.keywords) && (
                <div className="change-item keyword-optimization">
                  <div className="change-label">🔑 키워드 최적화</div>
                  <div className="keyword-content">
                    <div className="action-row">
                      <span className="action-label">타겟 키워드:</span>
                      <div className="keyword-tags">
                        {previewData.keywords.map((kw, idx) => (
                          <span key={idx} className="keyword-tag">{kw}</span>
                        ))}
                      </div>
                    </div>
                    {previewData.target_field && (
                      <div className="action-row">
                        <span className="action-label">적용 필드:</span>
                        <span className="action-value">{previewData.target_field}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 내부 링크 제안 */}
              {previewData.suggested_links && Array.isArray(previewData.suggested_links) && (
                <div className="change-item internal-link">
                  <div className="change-label">🔗 내부 링크 제안</div>
                  <div className="internal-link-content">
                    {previewData.suggested_links.map((link, idx) => (
                      <div key={idx} className="link-item">
                        <span className="link-url">{link.url}</span>
                        <span className="link-anchor">→ "{link.anchor_text}"</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Quick Win */}
              {previewData.quick_win_type && (
                <div className="change-item quick-win">
                  <div className="change-label">⚡ Quick Win</div>
                  <div className="quick-win-content">
                    <div className="action-row">
                      <span className="action-label">유형:</span>
                      <span className="action-value">{previewData.quick_win_type}</span>
                    </div>
                    {previewData.action_type && (
                      <div className="action-row">
                        <span className="action-label">액션:</span>
                        <span className="action-value">{previewData.action_type}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 영향받는 페이지 목록 (bulk fix) */}
              {previewData.affected_pages && previewData.affected_pages.length > 0 && (
                <div className="change-item affected-pages">
                  <div className="change-label">📄 영향받는 페이지 ({previewData.affected_pages.length}개)</div>
                  <div className="affected-pages-list">
                    {previewData.affected_pages.map((page, idx) => (
                      <div key={idx} className="affected-page-item">
                        <div className="page-info">
                          <span className="page-url-short" title={page.url}>
                            {page.url.replace(/^https?:\/\/[^/]+/, '')}
                          </span>
                          <span className="page-issue">{page.issue}</span>
                        </div>
                        <div className="page-current">
                          <span className="current-label">현재:</span>
                          <span className="current-value">{page.current_value}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 우선순위 액션 데이터 (category, effort 등) */}
              {previewData.category && (
                <div className="change-item priority-action">
                  <div className="change-label">📌 우선순위 액션</div>
                  <div className="priority-action-content">
                    {previewData.category && (
                      <div className="action-row">
                        <span className="action-label">카테고리:</span>
                        <span className="action-value">{previewData.category}</span>
                      </div>
                    )}
                    {previewData.description && (
                      <div className="action-row">
                        <span className="action-label">설명:</span>
                        <span className="action-value">{previewData.description}</span>
                      </div>
                    )}
                    {previewData.expected_impact && (
                      <div className="action-row">
                        <span className="action-label">예상 효과:</span>
                        <span className="action-value highlight">{previewData.expected_impact}</span>
                      </div>
                    )}
                    {previewData.effort && (
                      <div className="action-row">
                        <span className="action-label">필요 노력:</span>
                        <span className={`action-value effort-badge effort-${previewData.effort}`}>
                          {previewData.effort === 'high' ? '높음' : previewData.effort === 'medium' ? '중간' : '낮음'}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 페이지 제안 데이터 */}
              {previewData.suggestion_type && previewData.suggested_action && (
                <div className="change-item page-suggestion">
                  <div className="change-label">📝 페이지 개선 제안</div>
                  <div className="page-suggestion-content">
                    {previewData.current_issue && (
                      <div className="action-row">
                        <span className="action-label">현재 문제:</span>
                        <span className="action-value issue">{previewData.current_issue}</span>
                      </div>
                    )}
                    {previewData.suggested_action && (
                      <div className="action-row">
                        <span className="action-label">제안 액션:</span>
                        <span className="action-value">{previewData.suggested_action}</span>
                      </div>
                    )}
                    {previewData.expected_improvement && (
                      <div className="action-row">
                        <span className="action-label">예상 개선:</span>
                        <span className="action-value highlight">{previewData.expected_improvement}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 자동 적용 불가 경고 (데이터 부족) */}
              {suggestion.suggestion_type === 'quick_win' &&
               (previewData.description?.includes('제목') ||
                previewData.description?.includes('title') ||
                previewData.description?.includes('설명') ||
                previewData.description?.includes('description')) &&
               !previewData.page_url &&
               !previewData.affected_pages && (
                <div className="change-item warning-incomplete">
                  <div className="change-label">⚠️ 자동 적용 불가</div>
                  <div className="warning-content">
                    <p>이 제안은 구체적인 정보가 부족하여 자동 적용이 불가능합니다.</p>
                    <ul>
                      <li>어떤 페이지에 적용해야 하는지 명시되지 않음</li>
                      <li>현재 값과 새 값이 제공되지 않음</li>
                    </ul>
                    <p className="hint">수동으로 해당 페이지를 찾아 수정하거나, AI 분석을 다시 실행하세요.</p>
                  </div>
                </div>
              )}

              {/* 기타 데이터 (JSON) */}
              {!previewData.old_title && !previewData.new_title &&
               !previewData.old_description && !previewData.new_description &&
               !previewData.old_content && !previewData.new_content &&
               !previewData.old_code && !previewData.new_code &&
               !previewData.changes && !previewData.manual_guide &&
               !previewData.category && !previewData.suggested_action && (
                <div className="change-item">
                  <div className="change-label">📋 액션 데이터</div>
                  <pre className="json-preview">
                    {JSON.stringify(previewData, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="no-preview">
              <p>미리보기 데이터가 없습니다.</p>
              <p className="hint">이 제안은 수동으로 적용해야 합니다.</p>
            </div>
          )}
        </div>

        {/* 예상 효과 */}
        {suggestion.expected_impact && (
          <div className="preview-impact">
            <h5>예상 효과</h5>
            <div className="impact-content">
              <span className="impact-icon">📈</span>
              <span>{suggestion.expected_impact}</span>
            </div>
          </div>
        )}

        {/* 액션 버튼 */}
        <div className="preview-actions">
          {/* 자동 적용 가능한 경우 배포 미리보기 안내 */}
          {suggestion.is_auto_applicable && suggestion.page && suggestion.status === 'pending' && (
            <div className="auto-apply-notice">
              <span className="notice-icon">✨</span>
              <span>이 제안은 자동 적용이 가능합니다. 수락 시 변경 내용을 미리 확인할 수 있습니다.</span>
            </div>
          )}

          <div className="action-buttons">
            <button className="btn-cancel" onClick={onClose}>
              취소
            </button>
            {suggestion.status === 'pending' && (
              <button
                className="btn-accept"
                onClick={handleAccept}
                disabled={loading}
              >
                {loading ? '처리 중...' : suggestion.is_auto_applicable && suggestion.page
                  ? '🚀 수락 및 배포 미리보기'
                  : '✅ 수락'}
              </button>
            )}
          </div>
        </div>

        {/* 배포 미리보기 모달 */}
        <DeploymentPreviewModal
          isOpen={showDeploymentPreview}
          onClose={() => setShowDeploymentPreview(false)}
          suggestion={suggestion}
          previewData={deploymentPreviewData}
          loading={deploymentPreviewLoading}
          onConfirm={handleDeploymentConfirm}
        />
      </div>
    </div>
  );
};

export default AISuggestionPreviewModal;
