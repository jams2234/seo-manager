/**
 * AI Learning Service
 * AI 지속 학습 시스템 API 클라이언트
 */
import apiClient from './api';

export const aiLearningService = {
  // ============================================
  // AI Learning Status & Control
  // ============================================

  /**
   * 학습 상태 조회
   * @param {number} domainId - 도메인 ID (선택)
   */
  getStatus: (domainId = null) => {
    const params = domainId ? { domain_id: domainId } : {};
    return apiClient.get('/ai-learning/status/', { params });
  },

  /**
   * 수동 학습 동기화 트리거
   * @param {number} domainId - 도메인 ID
   */
  triggerSync: (domainId) =>
    apiClient.post('/ai-learning/trigger_sync/', { domain_id: domainId }),

  /**
   * 수동 AI 분석 트리거
   * @param {number} domainId - 도메인 ID
   */
  triggerAnalysis: (domainId) =>
    apiClient.post('/ai-learning/trigger_analysis/', { domain_id: domainId }),

  /**
   * 분석 실행 이력 조회
   * @param {number} domainId - 도메인 ID (선택)
   * @param {number} limit - 결과 수 제한
   */
  getAnalysisHistory: (domainId = null, limit = 20) => {
    const params = { limit };
    if (domainId) params.domain_id = domainId;
    return apiClient.get('/ai-learning/analysis_history/', { params });
  },

  /**
   * 벡터 저장소 통계 조회
   */
  getVectorStats: () => apiClient.get('/ai-learning/vector_stats/'),

  /**
   * Celery 태스크 상태 조회
   * @param {string} taskId - Celery 태스크 ID
   */
  getTaskStatus: (taskId) =>
    apiClient.get('/ai-learning/task_status/', { params: { task_id: taskId } }),
};

export const aiSuggestionService = {
  // ============================================
  // AI Suggestions CRUD
  // ============================================

  /**
   * 제안 목록 조회
   * @param {Object} filters - 필터 옵션
   */
  list: (filters = {}) => {
    const params = {};
    if (filters.domainId) params.domain_id = filters.domainId;
    if (filters.status) params.status = filters.status;
    if (filters.type) params.type = filters.type;
    if (filters.priority) params.priority = filters.priority;
    if (filters.pageId) params.page_id = filters.pageId;
    return apiClient.get('/ai-suggestions/', { params });
  },

  /**
   * 제안 상세 조회
   * @param {number} id - 제안 ID
   */
  get: (id) => apiClient.get(`/ai-suggestions/${id}/`),

  /**
   * 제안 요약 통계
   * @param {number} domainId - 도메인 ID (선택)
   */
  getSummary: (domainId = null) => {
    const params = domainId ? { domain_id: domainId } : {};
    return apiClient.get('/ai-suggestions/summary/', { params });
  },

  // ============================================
  // AI Suggestions Actions
  // ============================================

  /**
   * 제안 수락
   * @param {number} id - 제안 ID
   * @param {boolean} deployToGit - Git 저장소에 배포 여부
   */
  accept: (id, deployToGit = false) =>
    apiClient.post(`/ai-suggestions/${id}/accept/`, { deploy_to_git: deployToGit }),

  /**
   * 제안 거절
   * @param {number} id - 제안 ID
   * @param {string} reason - 거절 사유
   */
  reject: (id, reason = '') =>
    apiClient.post(`/ai-suggestions/${id}/reject/`, { reason }),

  /**
   * 제안 보류
   * @param {number} id - 제안 ID
   * @param {string} until - 보류 기한 (ISO 형식)
   */
  defer: (id, until = null) =>
    apiClient.post(`/ai-suggestions/${id}/defer/`, until ? { until } : {}),

  /**
   * 피드백 제출
   * @param {number} id - 제안 ID
   * @param {string} feedbackType - helpful, not_helpful, incorrect
   * @param {string} comment - 코멘트
   */
  feedback: (id, feedbackType, comment = '') =>
    apiClient.post(`/ai-suggestions/${id}/feedback/`, {
      feedback_type: feedbackType,
      comment,
    }),

  /**
   * 수동 적용 완료 표시
   * @param {number} id - 제안 ID
   */
  markApplied: (id) => apiClient.post(`/ai-suggestions/${id}/mark_applied/`),

  /**
   * 배포 미리보기
   * @param {number} id - 제안 ID
   * @returns {Object} - 변경 미리보기 정보 (db_changes, git_changes, git_config, warnings)
   */
  previewDeployment: (id) => apiClient.get(`/ai-suggestions/${id}/preview_deployment/`),

  // ============================================
  // AI Suggestions Tracking
  // ============================================

  /**
   * 추적 시작
   * @param {number} id - 제안 ID
   * @returns {Object} - baseline_metrics, tracking_started_at
   */
  startTracking: (id) => apiClient.post(`/ai-suggestions/${id}/start_tracking/`),

  /**
   * 추적 데이터 조회
   * @param {number} id - 제안 ID
   * @returns {Object} - suggestion, baseline, current, snapshots, chart_data, analysis_logs
   */
  getTrackingData: (id) => apiClient.get(`/ai-suggestions/${id}/tracking_data/`),

  /**
   * 효과 분석 실행
   * @param {number} id - 제안 ID
   * @param {string} analysisType - 'manual', 'weekly', 'milestone', 'final'
   * @returns {Object} - analysis, changes, effectiveness_score, trend_direction
   */
  analyzeImpact: (id, analysisType = 'manual') =>
    apiClient.post(`/ai-suggestions/${id}/analyze_impact/`, { analysis_type: analysisType }),

  /**
   * 추적 종료
   * @param {number} id - 제안 ID
   * @param {boolean} runFinalAnalysis - 최종 분석 실행 여부
   * @returns {Object} - final_metrics, impact_analysis, effectiveness_score
   */
  endTracking: (id, runFinalAnalysis = true) =>
    apiClient.post(`/ai-suggestions/${id}/end_tracking/`, { run_final_analysis: runFinalAnalysis }),

  /**
   * 추적중인 제안 목록
   * @param {number} domainId - 도메인 ID (선택)
   * @returns {Object} - tracking_count, suggestions
   */
  getTrackingList: (domainId = null) => {
    const params = domainId ? { domain_id: domainId } : {};
    return apiClient.get('/ai-suggestions/tracking_list/', { params });
  },

  /**
   * 스냅샷 수동 캡처
   * @param {number} id - 제안 ID
   * @returns {Object} - snapshot, day_number
   */
  captureSnapshot: (id) => apiClient.post(`/ai-suggestions/${id}/capture_snapshot/`),
};

export default aiLearningService;
