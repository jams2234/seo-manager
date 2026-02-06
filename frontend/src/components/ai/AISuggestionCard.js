/**
 * AI Suggestion Card Component
 * 개별 AI 제안 카드 (수락/거절/피드백/추적)
 */
import React, { useState } from 'react';
import AISuggestionPreviewModal from './AISuggestionPreviewModal';
import ImpactReportModal from './ImpactReportModal';
import { aiSuggestionService } from '../../services/aiLearningService';
import toastService from '../../services/toastService';
import { getPriorityInfo, getStatusInfo, getTypeLabel } from '../../utils/aiUtils';
import './AISuggestionCard.css';

const AISuggestionCard = ({
  suggestion,
  onAccept,
  onReject,
  onDefer,
  onMarkApplied,
  onFeedback,
  onUpdate,
}) => {
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [showImpactReport, setShowImpactReport] = useState(false);
  const [startingTracking, setStartingTracking] = useState(false);
  const [markingApplied, setMarkingApplied] = useState(false);

  // 추적 시작
  const handleStartTracking = async () => {
    setStartingTracking(true);
    try {
      const response = await aiSuggestionService.startTracking(suggestion.id);
      if (response.data?.success) {
        toastService.success('추적이 시작되었습니다.');
        if (onUpdate) onUpdate();
      } else {
        toastService.error(response.data?.message || '추적 시작 실패');
      }
    } catch (err) {
      console.error('Start tracking error:', err);
      toastService.error('추적 시작 중 오류가 발생했습니다.');
    } finally {
      setStartingTracking(false);
    }
  };

  // 추적 종료 후 콜백
  const handleTrackingEnd = () => {
    if (onUpdate) onUpdate();
  };

  // 수동 적용 완료 + 추적 시작 (한번에)
  const handleMarkAppliedAndTrack = async () => {
    setMarkingApplied(true);
    try {
      // 1. 적용 완료 표시
      await onMarkApplied(suggestion.id);

      // 2. 바로 추적 시작
      const response = await aiSuggestionService.startTracking(suggestion.id);
      if (response.data?.success) {
        toastService.success('적용 완료! 효과 추적이 시작되었습니다.');
      } else {
        toastService.info('적용 완료! 추적은 수동으로 시작해주세요.');
      }
      if (onUpdate) onUpdate();
    } catch (err) {
      console.error('Mark applied and track error:', err);
      toastService.error('처리 중 오류가 발생했습니다.');
    } finally {
      setMarkingApplied(false);
    }
  };

  const priorityInfo = getPriorityInfo(suggestion.priority);
  const statusInfo = getStatusInfo(suggestion.status);

  // 거절 제출
  const handleRejectSubmit = () => {
    onReject(suggestion.id, rejectReason);
    setShowRejectModal(false);
    setRejectReason('');
  };

  // 피드백 제출
  const handleFeedbackSubmit = (feedbackType) => {
    onFeedback(suggestion.id, feedbackType, '');
    setShowFeedback(false);
  };

  return (
    <div className={`ai-suggestion-card status-${suggestion.status}`}>
      {/* 헤더 */}
      <div className="suggestion-header">
        <div className="suggestion-badges">
          <span
            className="badge-priority"
            style={{ backgroundColor: priorityInfo.color }}
          >
            {priorityInfo.label}
          </span>
          <span className="badge-type">{getTypeLabel(suggestion.suggestion_type)}</span>
          {suggestion.is_auto_applicable && (
            <span className="badge-auto">자동적용</span>
          )}
        </div>
        <span
          className="badge-status"
          style={{ backgroundColor: statusInfo.color }}
        >
          {statusInfo.label}
        </span>
      </div>

      {/* 제목 */}
      <h4 className="suggestion-title">{suggestion.title}</h4>

      {/* 설명 */}
      <p className={`suggestion-description ${expanded ? 'expanded' : ''}`}>
        {suggestion.description}
      </p>
      {suggestion.description && suggestion.description.length > 150 && (
        <button
          className="btn-expand"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? '접기' : '더보기'}
        </button>
      )}

      {/* 예상 효과 */}
      {suggestion.expected_impact && (
        <div className="suggestion-impact">
          <span className="impact-icon">📈</span>
          <span className="impact-text">{suggestion.expected_impact}</span>
        </div>
      )}

      {/* 페이지 정보 */}
      {suggestion.page_url && (
        <div className="suggestion-page">
          <span className="page-icon">📄</span>
          <span className="page-url" title={suggestion.page_url}>
            {suggestion.page_url}
          </span>
        </div>
      )}

      {/* 액션 버튼 */}
      <div className="suggestion-actions">
        {suggestion.status === 'pending' && (
          <>
            <button
              className="btn-preview"
              onClick={() => setShowPreview(true)}
              title="변경 내용 미리보기"
            >
              👁️ 미리보기
            </button>
            <button
              className="btn-accept"
              onClick={() => onAccept(suggestion.id)}
            >
              ✅ 수락
            </button>
            <button
              className="btn-reject"
              onClick={() => setShowRejectModal(true)}
            >
              ❌ 거절
            </button>
            <button
              className="btn-defer"
              onClick={() => onDefer(suggestion.id)}
            >
              ⏸️ 보류
            </button>
          </>
        )}

        {suggestion.status === 'accepted' && (
          <>
            {/* 자동적용 가능했던 제안이 accepted 상태면 = 자동 적용 실패 케이스 */}
            {suggestion.is_auto_applicable ? (
              <>
                <button
                  className="btn-accept"
                  onClick={() => onAccept(suggestion.id)}
                  title="다시 자동 적용 시도"
                >
                  🔄 재시도
                </button>
                <button
                  className="btn-mark-applied"
                  onClick={handleMarkAppliedAndTrack}
                  disabled={markingApplied}
                >
                  {markingApplied ? '처리중...' : '✅ 수동 적용 완료'}
                </button>
              </>
            ) : (
              <button
                className="btn-mark-applied"
                onClick={handleMarkAppliedAndTrack}
                disabled={markingApplied}
              >
                {markingApplied ? '처리중...' : '✅ 적용 완료 & 추적 시작'}
              </button>
            )}
            <button
              className="btn-reject"
              onClick={() => setShowRejectModal(true)}
            >
              ❌ 취소
            </button>
          </>
        )}

        {suggestion.status === 'applied' && (
          <>
            {/* applied 상태에서도 추적을 시작할 수 있음 (자동 추적 실패 시) */}
            <button
              className="btn-tracking"
              onClick={handleStartTracking}
              disabled={startingTracking}
            >
              {startingTracking ? (
                <>
                  <span className="spinner-small" />
                  시작중...
                </>
              ) : (
                '📊 추적 시작'
              )}
            </button>
            <button
              className="btn-feedback"
              onClick={() => setShowFeedback(!showFeedback)}
            >
              💬 피드백
            </button>
          </>
        )}

        {suggestion.status === 'tracking' && (
          <>
            <button
              className="btn-view-tracking"
              onClick={() => setShowImpactReport(true)}
            >
              📈 추적 현황
            </button>
            <span className="tracking-days-badge">
              {suggestion.tracking_days || 0}일째 추적중
            </span>
          </>
        )}

        {suggestion.status === 'tracked' && (
          <>
            <button
              className="btn-view-report"
              onClick={() => setShowImpactReport(true)}
            >
              📋 효과 리포트
            </button>
            {suggestion.effectiveness_score && (
              <span
                className="effectiveness-score-badge"
                style={{
                  color: suggestion.effectiveness_score >= 70 ? '#10b981' :
                         suggestion.effectiveness_score >= 50 ? '#f59e0b' : '#ef4444'
                }}
              >
                효과: {suggestion.effectiveness_score.toFixed(0)}점
              </span>
            )}
          </>
        )}

        {suggestion.status === 'deferred' && (
          <button
            className="btn-accept"
            onClick={() => onAccept(suggestion.id)}
          >
            ✅ 재수락
          </button>
        )}
      </div>

      {/* 피드백 선택 */}
      {showFeedback && (
        <div className="feedback-options">
          <p>이 제안이 도움이 되었나요?</p>
          <div className="feedback-buttons">
            <button
              className="btn-helpful"
              onClick={() => handleFeedbackSubmit('helpful')}
            >
              👍 도움됨
            </button>
            <button
              className="btn-not-helpful"
              onClick={() => handleFeedbackSubmit('not_helpful')}
            >
              👎 도움안됨
            </button>
            <button
              className="btn-incorrect"
              onClick={() => handleFeedbackSubmit('incorrect')}
            >
              ⚠️ 부정확
            </button>
          </div>
        </div>
      )}

      {/* 거절 사유 모달 */}
      {showRejectModal && (
        <div className="reject-modal-overlay" onClick={() => setShowRejectModal(false)}>
          <div className="reject-modal" onClick={(e) => e.stopPropagation()}>
            <h5>거절 사유</h5>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="거절 사유를 입력하세요 (선택)"
              rows={3}
            />
            <div className="modal-actions">
              <button
                className="btn-cancel"
                onClick={() => setShowRejectModal(false)}
              >
                취소
              </button>
              <button
                className="btn-confirm"
                onClick={handleRejectSubmit}
              >
                거절
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 메타 정보 */}
      <div className="suggestion-meta">
        <span className="meta-date">
          {new Date(suggestion.created_at).toLocaleDateString('ko-KR')}
        </span>
        {suggestion.user_feedback && (
          <span className="meta-feedback">피드백: {suggestion.user_feedback}</span>
        )}
      </div>

      {/* 미리보기 모달 */}
      {showPreview && (
        <AISuggestionPreviewModal
          suggestion={suggestion}
          onClose={() => setShowPreview(false)}
          onAccept={onAccept}
        />
      )}

      {/* 효과 분석 리포트 모달 */}
      {showImpactReport && (
        <ImpactReportModal
          suggestionId={suggestion.id}
          onClose={() => setShowImpactReport(false)}
          onTrackingEnd={handleTrackingEnd}
        />
      )}
    </div>
  );
};

export default AISuggestionCard;
