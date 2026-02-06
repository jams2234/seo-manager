/**
 * AI Analysis Detail Modal Component
 * AI 분석 실행 결과 상세 보기
 */
import React, { useState, useEffect } from 'react';
import { aiLearningService } from '../../services/aiLearningService';
import './AIAnalysisDetailModal.css';

const AIAnalysisDetailModal = ({ analysisRun, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');

  if (!analysisRun) return null;

  // 상태 배지 색상
  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#10b981';
      case 'running': return '#3b82f6';
      case 'failed': return '#ef4444';
      default: return '#6b7280';
    }
  };

  // 소요 시간 포맷
  const formatDuration = (duration) => {
    if (!duration) return '-';
    if (typeof duration === 'string') return duration;
    const seconds = Math.round(duration);
    if (seconds < 60) return `${seconds}초`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}분 ${remainingSeconds}초`;
  };

  // 결과 요약 파싱
  const resultSummary = analysisRun.result_summary || {};
  const insights = resultSummary.insights || [];
  const analysisDetails = resultSummary.analysis || {};

  return (
    <div className="ai-analysis-modal-backdrop" onClick={onClose}>
      <div className="ai-analysis-modal" onClick={(e) => e.stopPropagation()}>
        {/* 헤더 */}
        <div className="modal-header">
          <div className="modal-title">
            <span className="modal-icon">📊</span>
            <h3>AI 분석 결과 상세</h3>
          </div>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {/* 분석 정보 */}
        <div className="analysis-info-bar">
          <div className="info-item">
            <span className="info-label">상태</span>
            <span
              className="info-badge"
              style={{ backgroundColor: getStatusColor(analysisRun.status) }}
            >
              {analysisRun.status}
            </span>
          </div>
          <div className="info-item">
            <span className="info-label">트리거</span>
            <span className="info-value">{analysisRun.trigger_type}</span>
          </div>
          <div className="info-item">
            <span className="info-label">시작</span>
            <span className="info-value">
              {analysisRun.started_at
                ? new Date(analysisRun.started_at).toLocaleString('ko-KR')
                : '-'}
            </span>
          </div>
          <div className="info-item">
            <span className="info-label">완료</span>
            <span className="info-value">
              {analysisRun.completed_at
                ? new Date(analysisRun.completed_at).toLocaleString('ko-KR')
                : '-'}
            </span>
          </div>
          <div className="info-item">
            <span className="info-label">소요시간</span>
            <span className="info-value">{formatDuration(analysisRun.duration)}</span>
          </div>
        </div>

        {/* 통계 카드 */}
        <div className="analysis-stats-grid">
          <div className="stat-card suggestions">
            <span className="stat-icon">💡</span>
            <span className="stat-value">{analysisRun.suggestions_count || 0}</span>
            <span className="stat-label">제안</span>
          </div>
          <div className="stat-card insights">
            <span className="stat-icon">🔍</span>
            <span className="stat-value">{analysisRun.insights_count || 0}</span>
            <span className="stat-label">인사이트</span>
          </div>
          <div className="stat-card pages">
            <span className="stat-icon">📄</span>
            <span className="stat-value">{resultSummary.pages_analyzed || '-'}</span>
            <span className="stat-label">분석 페이지</span>
          </div>
          <div className="stat-card issues">
            <span className="stat-icon">⚠️</span>
            <span className="stat-value">{resultSummary.issues_found || '-'}</span>
            <span className="stat-label">발견 이슈</span>
          </div>
        </div>

        {/* 탭 */}
        <div className="modal-tabs">
          <button
            className={`tab-btn ${activeTab === 'summary' ? 'active' : ''}`}
            onClick={() => setActiveTab('summary')}
          >
            요약
          </button>
          <button
            className={`tab-btn ${activeTab === 'insights' ? 'active' : ''}`}
            onClick={() => setActiveTab('insights')}
          >
            인사이트 ({insights.length})
          </button>
          <button
            className={`tab-btn ${activeTab === 'details' ? 'active' : ''}`}
            onClick={() => setActiveTab('details')}
          >
            상세 분석
          </button>
          {analysisRun.error_message && (
            <button
              className={`tab-btn error ${activeTab === 'error' ? 'active' : ''}`}
              onClick={() => setActiveTab('error')}
            >
              오류
            </button>
          )}
        </div>

        {/* 탭 컨텐츠 */}
        <div className="modal-content">
          {activeTab === 'summary' && (
            <div className="tab-content summary-tab">
              {resultSummary.summary ? (
                <div className="summary-text">
                  <h4>분석 요약</h4>
                  <p>{resultSummary.summary}</p>
                </div>
              ) : (
                <div className="no-content">
                  <p>분석 요약 정보가 없습니다.</p>
                </div>
              )}

              {resultSummary.top_priorities && resultSummary.top_priorities.length > 0 && (
                <div className="priorities-section">
                  <h4>우선 조치 사항</h4>
                  <ul className="priorities-list">
                    {resultSummary.top_priorities.map((priority, idx) => (
                      <li key={idx} className="priority-item">
                        <span className="priority-number">{idx + 1}</span>
                        <div className="priority-content">
                          <span className="priority-text">
                            {typeof priority === 'string' ? priority : (priority.description || priority.category || JSON.stringify(priority))}
                          </span>
                          {typeof priority === 'object' && priority.expected_impact && (
                            <span className="priority-impact">📈 {priority.expected_impact}</span>
                          )}
                          {typeof priority === 'object' && priority.effort && (
                            <span className={`priority-effort effort-${priority.effort}`}>
                              노력: {priority.effort}
                            </span>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {resultSummary.health_score !== undefined && (
                <div className="health-score-section">
                  <h4>도메인 건강 점수</h4>
                  <div className="health-score-display">
                    <span className="health-score-value">{resultSummary.health_score}</span>
                    <span className="health-score-max">/ 100</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'insights' && (
            <div className="tab-content insights-tab">
              {insights.length > 0 ? (
                <div className="insights-list">
                  {insights.map((insight, idx) => (
                    <div key={idx} className="insight-card">
                      <div className="insight-header">
                        <span className="insight-type">{insight.type || '일반'}</span>
                        {insight.severity && (
                          <span className={`insight-severity ${insight.severity}`}>
                            {insight.severity}
                          </span>
                        )}
                      </div>
                      <h5 className="insight-title">{insight.title || insight.message}</h5>
                      {insight.description && (
                        <p className="insight-description">{insight.description}</p>
                      )}
                      {insight.recommendation && (
                        <div className="insight-recommendation">
                          <span className="rec-icon">💡</span>
                          <span>{insight.recommendation}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-content">
                  <p>인사이트 정보가 없습니다.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'details' && (
            <div className="tab-content details-tab">
              {Object.keys(analysisDetails).length > 0 ? (
                <div className="details-sections">
                  {analysisDetails.technical && (
                    <div className="detail-section">
                      <h4>🔧 기술 분석</h4>
                      <pre className="detail-content">
                        {JSON.stringify(analysisDetails.technical, null, 2)}
                      </pre>
                    </div>
                  )}
                  {analysisDetails.content && (
                    <div className="detail-section">
                      <h4>📝 콘텐츠 분석</h4>
                      <pre className="detail-content">
                        {JSON.stringify(analysisDetails.content, null, 2)}
                      </pre>
                    </div>
                  )}
                  {analysisDetails.structure && (
                    <div className="detail-section">
                      <h4>🏗️ 구조 분석</h4>
                      <pre className="detail-content">
                        {JSON.stringify(analysisDetails.structure, null, 2)}
                      </pre>
                    </div>
                  )}
                  {!analysisDetails.technical && !analysisDetails.content && !analysisDetails.structure && (
                    <pre className="detail-content full">
                      {JSON.stringify(resultSummary, null, 2)}
                    </pre>
                  )}
                </div>
              ) : (
                <div className="no-content">
                  <p>상세 분석 데이터가 없습니다.</p>
                  {resultSummary && Object.keys(resultSummary).length > 0 && (
                    <pre className="detail-content">
                      {JSON.stringify(resultSummary, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'error' && analysisRun.error_message && (
            <div className="tab-content error-tab">
              <div className="error-display">
                <h4>오류 메시지</h4>
                <pre className="error-message">{analysisRun.error_message}</pre>
              </div>
            </div>
          )}
        </div>

        {/* 푸터 */}
        <div className="modal-footer">
          <button className="btn-close" onClick={onClose}>
            닫기
          </button>
        </div>
      </div>
    </div>
  );
};

export default AIAnalysisDetailModal;
