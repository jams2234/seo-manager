/**
 * AI Learning Dashboard Component
 * AI 지속 학습 상태 및 분석 트리거 대시보드
 */
import React, { useState, useEffect, useCallback } from 'react';
import { aiLearningService, aiSuggestionService } from '../../services/aiLearningService';
import AISuggestionsList from './AISuggestionsList';
import AIAnalysisDetailModal from './AIAnalysisDetailModal';
import AIEffectivenessDashboard from './AIEffectivenessDashboard';
import AILearningQualityGuide from './AILearningQualityGuide';
import AnalyticsDashboard from './AnalyticsDashboard';
import { getTaskStatusColor } from '../../utils/aiUtils';
import './AILearningDashboard.css';

const AILearningDashboard = ({ domainId, domainName }) => {
  const [learningStatus, setLearningStatus] = useState(null);
  const [analysisHistory, setAnalysisHistory] = useState([]);
  const [suggestionSummary, setSuggestionSummary] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [vectorStats, setVectorStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncLoading, setSyncLoading] = useState(false);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('analytics');
  const [taskProgress, setTaskProgress] = useState(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);

  // 데이터 로드 (silent: true면 로딩 스피너 표시 안함)
  const loadData = useCallback(async (silent = false) => {
    try {
      if (!silent) {
        setLoading(true);
      }
      const [statusRes, historyRes, summaryRes, suggestionsRes] = await Promise.all([
        aiLearningService.getStatus(domainId),
        aiLearningService.getAnalysisHistory(domainId, 10),
        aiSuggestionService.getSummary(domainId),
        aiSuggestionService.list({ domainId }),
      ]);

      const statusData = statusRes.data;
      if (Array.isArray(statusData) && statusData.length > 0) {
        setLearningStatus(statusData[0]);
      } else if (!Array.isArray(statusData)) {
        setLearningStatus(statusData);
      }

      setAnalysisHistory(historyRes.data || []);
      setSuggestionSummary(summaryRes.data || null);
      setSuggestions(suggestionsRes.data?.results || suggestionsRes.data || []);
    } catch (error) {
      console.error('AI Learning 데이터 로드 실패:', error);
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }, [domainId]);

  // 자식 컴포넌트에서 호출하는 silent refresh (스크롤 위치 유지)
  const handleSilentRefresh = useCallback(() => {
    loadData(true);
  }, [loadData]);

  // 벡터 통계 로드 (별도)
  const loadVectorStats = useCallback(async () => {
    try {
      const res = await aiLearningService.getVectorStats();
      setVectorStats(res.data);
    } catch (error) {
      console.error('벡터 통계 로드 실패:', error);
    }
  }, []);

  useEffect(() => {
    loadData();
    loadVectorStats();
  }, [loadData, loadVectorStats]);

  // 태스크 진행 상황 폴링
  const pollTaskProgress = useCallback(async (taskId) => {
    try {
      const res = await aiLearningService.getTaskStatus(taskId);
      setTaskProgress(res.data);

      if (!res.data.ready) {
        setTimeout(() => pollTaskProgress(taskId), 2000);
      } else {
        // 완료 시 데이터 새로고침
        setTimeout(() => {
          loadData();
          setTaskProgress(null);
          setSyncLoading(false);
          setAnalysisLoading(false);
        }, 1000);
      }
    } catch (error) {
      console.error('태스크 상태 조회 실패:', error);
      setTaskProgress(null);
      setSyncLoading(false);
      setAnalysisLoading(false);
    }
  }, [loadData]);

  // 학습 동기화 트리거
  const handleSync = async () => {
    try {
      setSyncLoading(true);
      const res = await aiLearningService.triggerSync(domainId);
      if (res.data.task_id) {
        pollTaskProgress(res.data.task_id);
      }
    } catch (error) {
      console.error('동기화 트리거 실패:', error);
      setSyncLoading(false);
    }
  };

  // AI 분석 트리거
  const handleAnalysis = async () => {
    try {
      setAnalysisLoading(true);
      const res = await aiLearningService.triggerAnalysis(domainId);
      if (res.data.task_id) {
        pollTaskProgress(res.data.task_id);
      }
    } catch (error) {
      console.error('분석 트리거 실패:', error);
      setAnalysisLoading(false);
    }
  };

  // 상태 배지 색상 (getTaskStatusColor 별칭)
  const getStatusColor = getTaskStatusColor;

  if (loading) {
    return (
      <div className="ai-learning-dashboard loading">
        <div className="loading-spinner"></div>
        <p>AI 학습 데이터 로드 중...</p>
      </div>
    );
  }

  return (
    <div className="ai-learning-dashboard">
      {/* 헤더 */}
      <div className="ai-dashboard-header">
        <div className="ai-dashboard-title">
          <span className="ai-icon">🧠</span>
          <h2>AI 지속 학습 시스템</h2>
        </div>
        <div className="ai-dashboard-actions">
          <button
            className="btn-sync"
            onClick={handleSync}
            disabled={syncLoading || analysisLoading}
          >
            {syncLoading ? '동기화 중...' : '🔄 학습 동기화'}
          </button>
          <button
            className="btn-analyze"
            onClick={handleAnalysis}
            disabled={syncLoading || analysisLoading}
          >
            {analysisLoading ? '분석 중...' : '✨ AI 분석 실행'}
          </button>
        </div>
      </div>

      {/* 진행 상황 표시 */}
      {taskProgress && (
        <div className="task-progress-bar">
          <div className="progress-info">
            <span className="progress-status">{taskProgress.status}</span>
            {taskProgress.progress && (
              <span className="progress-message">
                {taskProgress.progress.status} ({taskProgress.progress.percent}%)
              </span>
            )}
          </div>
          {taskProgress.progress && (
            <div className="progress-track">
              <div
                className="progress-fill"
                style={{ width: `${taskProgress.progress.percent}%` }}
              ></div>
            </div>
          )}
        </div>
      )}

      {/* 탭 네비게이션 */}
      <div className="ai-dashboard-tabs">
        <button
          className={`tab-btn ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          📈 성과 분석
        </button>
        <button
          className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          📊 개요
        </button>
        <button
          className={`tab-btn ${activeTab === 'suggestions' ? 'active' : ''}`}
          onClick={() => setActiveTab('suggestions')}
        >
          💡 제안 {suggestionSummary?.by_status?.pending > 0 && (
            <span className="badge-count">{suggestionSummary.by_status.pending}</span>
          )}
        </button>
        <button
          className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          📜 분석 이력
        </button>
        <button
          className={`tab-btn ${activeTab === 'effectiveness' ? 'active' : ''}`}
          onClick={() => setActiveTab('effectiveness')}
        >
          📈 효과성
        </button>
        <button
          className={`tab-btn ${activeTab === 'quality' ? 'active' : ''}`}
          onClick={() => setActiveTab('quality')}
        >
          📋 품질 가이드
        </button>
      </div>

      {/* 탭 컨텐츠 */}
      <div className="ai-dashboard-content">
        {activeTab === 'analytics' && (
          <AnalyticsDashboard domainId={domainId} />
        )}

        {activeTab === 'overview' && (
          <div className="overview-tab">
            {/* 학습 상태 카드 */}
            <div className="stats-grid">
              <div className="stat-card learning-status">
                <div className="stat-header">
                  <span className="stat-icon">📚</span>
                  <h3>학습 상태</h3>
                </div>
                <div className="stat-body">
                  {learningStatus ? (
                    <>
                      <div className="status-badge" style={{ backgroundColor: getStatusColor(learningStatus.sync_status) }}>
                        {learningStatus.sync_status || 'idle'}
                      </div>
                      <div className="stat-details">
                        <div className="detail-row">
                          <span>동기화된 페이지:</span>
                          <strong>{learningStatus.pages_synced || 0}개</strong>
                        </div>
                        <div className="detail-row">
                          <span>임베딩 업데이트:</span>
                          <strong>{learningStatus.embeddings_updated || 0}개</strong>
                        </div>
                        <div className="detail-row">
                          <span>학습 품질 점수:</span>
                          <strong>{learningStatus.learning_quality_score || 0}점</strong>
                        </div>
                        <div className="detail-row">
                          <span>마지막 동기화:</span>
                          <strong>
                            {learningStatus.last_sync_at
                              ? new Date(learningStatus.last_sync_at).toLocaleString('ko-KR')
                              : '-'}
                          </strong>
                        </div>
                      </div>
                    </>
                  ) : (
                    <p className="no-data">학습 데이터 없음</p>
                  )}
                </div>
              </div>

              {/* 제안 요약 카드 */}
              <div className="stat-card suggestions-summary">
                <div className="stat-header">
                  <span className="stat-icon">💡</span>
                  <h3>제안 현황</h3>
                </div>
                <div className="stat-body">
                  {suggestionSummary ? (
                    <>
                      <div className="summary-total">
                        <span className="total-number">{suggestionSummary.total}</span>
                        <span className="total-label">전체 제안</span>
                      </div>
                      <div className="summary-breakdown">
                        <div className="breakdown-item pending">
                          <span className="count">{suggestionSummary.by_status?.pending || 0}</span>
                          <span className="label">대기중</span>
                        </div>
                        <div className="breakdown-item accepted">
                          <span className="count">{suggestionSummary.by_status?.accepted || 0}</span>
                          <span className="label">수락됨</span>
                        </div>
                        <div className="breakdown-item applied">
                          <span className="count">{suggestionSummary.by_status?.applied || 0}</span>
                          <span className="label">적용됨</span>
                        </div>
                        <div className="breakdown-item rejected">
                          <span className="count">{suggestionSummary.by_status?.rejected || 0}</span>
                          <span className="label">거절됨</span>
                        </div>
                      </div>
                    </>
                  ) : (
                    <p className="no-data">제안 데이터 없음</p>
                  )}
                </div>
              </div>

              {/* 벡터 DB 통계 카드 */}
              <div className="stat-card vector-stats">
                <div className="stat-header">
                  <span className="stat-icon">🗄️</span>
                  <h3>벡터 저장소</h3>
                  {vectorStats?.available && (
                    <span className="status-badge success">정상</span>
                  )}
                </div>
                <div className="stat-body">
                  {vectorStats ? (
                    <div className="vector-collections">
                      <div className="collection-grid">
                        <div className="collection-item">
                          <span className="collection-icon">🌐</span>
                          <span className="collection-name">도메인 지식</span>
                          <strong className="collection-count">{vectorStats.collections?.domain_knowledge || 0}</strong>
                        </div>
                        <div className="collection-item">
                          <span className="collection-icon">📄</span>
                          <span className="collection-name">페이지 컨텍스트</span>
                          <strong className="collection-count">{vectorStats.collections?.page_context || 0}</strong>
                        </div>
                        <div className="collection-item">
                          <span className="collection-icon">🔧</span>
                          <span className="collection-name">수정 이력</span>
                          <strong className="collection-count">{vectorStats.collections?.fix_history || 0}</strong>
                        </div>
                        <div className="collection-item">
                          <span className="collection-icon">📊</span>
                          <span className="collection-name">분석 캐시</span>
                          <strong className="collection-count">{vectorStats.collections?.analysis_cache || 0}</strong>
                        </div>
                        <div className="collection-item">
                          <span className="collection-icon">🌳</span>
                          <span className="collection-name">사이트 구조</span>
                          <strong className="collection-count">{vectorStats.collections?.site_structure || 0}</strong>
                        </div>
                        <div className="collection-item">
                          <span className="collection-icon">🗺️</span>
                          <span className="collection-name">Sitemap 항목</span>
                          <strong className="collection-count">{vectorStats.collections?.sitemap_entries || 0}</strong>
                        </div>
                        <div className="collection-item highlight">
                          <span className="collection-icon">📈</span>
                          <span className="collection-name">제안 추적</span>
                          <strong className="collection-count">{vectorStats.collections?.suggestion_tracking || 0}</strong>
                        </div>
                      </div>
                      <div className="vector-total">
                        총 임베딩: <strong>{
                          Object.values(vectorStats.collections || {}).reduce((a, b) => a + (typeof b === 'number' ? b : 0), 0)
                        }개</strong>
                      </div>
                    </div>
                  ) : (
                    <p className="no-data">벡터 DB 정보 없음</p>
                  )}
                </div>
              </div>
            </div>

            {/* 최근 분석 요약 */}
            {analysisHistory.length > 0 && (
              <div className="recent-analysis">
                <h3>최근 분석 결과</h3>
                <div className="analysis-card">
                  <div className="analysis-header">
                    <span className="status-badge" style={{ backgroundColor: getStatusColor(analysisHistory[0].status) }}>
                      {analysisHistory[0].status}
                    </span>
                    <span className="trigger-type">{analysisHistory[0].trigger_type}</span>
                  </div>
                  <div className="analysis-stats">
                    <div className="stat">
                      <span className="value">{analysisHistory[0].suggestions_count}</span>
                      <span className="label">제안</span>
                    </div>
                    <div className="stat">
                      <span className="value">{analysisHistory[0].insights_count}</span>
                      <span className="label">인사이트</span>
                    </div>
                    <div className="stat">
                      <span className="value">{analysisHistory[0].duration || '-'}</span>
                      <span className="label">소요시간</span>
                    </div>
                  </div>
                  {analysisHistory[0].completed_at && (
                    <div className="analysis-time">
                      완료: {new Date(analysisHistory[0].completed_at).toLocaleString('ko-KR')}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'suggestions' && (
          <AISuggestionsList
            domainId={domainId}
            onRefresh={handleSilentRefresh}
          />
        )}

        {activeTab === 'history' && (
          <div className="history-tab">
            <h3>분석 실행 이력</h3>
            <p className="history-hint">항목을 클릭하면 상세 정보를 볼 수 있습니다.</p>
            {analysisHistory.length > 0 ? (
              <div className="history-list">
                {analysisHistory.map((run) => (
                  <div
                    key={run.id}
                    className="history-item clickable"
                    onClick={() => setSelectedAnalysis(run)}
                  >
                    <div className="history-header">
                      <span className="status-badge" style={{ backgroundColor: getStatusColor(run.status) }}>
                        {run.status}
                      </span>
                      <span className="trigger-badge">{run.trigger_type}</span>
                      <span className="history-time">
                        {run.started_at ? new Date(run.started_at).toLocaleString('ko-KR') : '-'}
                      </span>
                    </div>
                    <div className="history-body">
                      <div className="history-stats">
                        <span>제안: {run.suggestions_count}개</span>
                        <span>인사이트: {run.insights_count}개</span>
                        {run.duration && <span>소요: {run.duration}</span>}
                      </div>
                      {run.error_message && (
                        <div className="history-error">
                          오류: {run.error_message}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-data">분석 이력이 없습니다.</p>
            )}
          </div>
        )}

        {activeTab === 'effectiveness' && (
          <AIEffectivenessDashboard domainId={domainId} />
        )}

        {activeTab === 'quality' && (
          <AILearningQualityGuide
            learningState={learningStatus}
            suggestions={suggestions}
          />
        )}
      </div>

      {/* 분석 상세 모달 */}
      {selectedAnalysis && (
        <AIAnalysisDetailModal
          analysisRun={selectedAnalysis}
          onClose={() => setSelectedAnalysis(null)}
        />
      )}
    </div>
  );
};

export default AILearningDashboard;
