/**
 * Analytics Service
 * 도메인 및 페이지별 SEO 성과 추적 API 클라이언트
 */
import api from './api';

const analyticsService = {
  /**
   * 도메인 전체 개요 조회
   * @param {number} domainId - 도메인 ID
   * @param {number} days - 조회 기간 (기본 30일)
   */
  getDomainOverview: async (domainId, days = 30) => {
    const response = await api.get(`/analytics/domain_overview/`, {
      params: { domain_id: domainId, days }
    });
    return response.data;
  },

  /**
   * 페이지별 SEO 트렌드 조회
   * @param {number} domainId - 도메인 ID
   * @param {number} days - 조회 기간 (기본 30일)
   * @param {number} limit - 페이지 수 제한 (기본 50)
   */
  getPageTrends: async (domainId, days = 30, limit = 50) => {
    const response = await api.get(`/analytics/page_trends/`, {
      params: { domain_id: domainId, days, limit }
    });
    return response.data;
  },

  /**
   * 키워드 노출 트렌드 조회
   * @param {number} domainId - 도메인 ID
   * @param {number} days - 조회 기간 (기본 30일)
   */
  getKeywordTrends: async (domainId, days = 30) => {
    const response = await api.get(`/analytics/keyword_trends/`, {
      params: { domain_id: domainId, days }
    });
    return response.data;
  },

  /**
   * 시작 vs 현재 상세 비교
   * @param {number} domainId - 도메인 ID
   */
  getComparison: async (domainId) => {
    const response = await api.get(`/analytics/comparison/`, {
      params: { domain_id: domainId }
    });
    return response.data;
  },

  /**
   * 스케줄 상태 조회
   * @param {number} domainId - 도메인 ID
   */
  getScheduleStatus: async (domainId) => {
    const response = await api.get(`/analytics/schedule_status/`, {
      params: { domain_id: domainId }
    });
    return response.data;
  },

  /**
   * 수동 동기화 트리거
   * @param {number} domainId - 도메인 ID
   * @param {string} syncType - 동기화 유형 ('gsc', 'full_scan', 'ai_analysis')
   */
  triggerSync: async (domainId, syncType = 'gsc') => {
    const response = await api.post(`/analytics/trigger_sync/`, {
      domain_id: domainId,
      sync_type: syncType
    });
    return response.data;
  },

  /**
   * 스케줄 시간 업데이트
   * @param {string} scheduleKey - 스케줄 키 (예: 'daily-full-scan')
   * @param {number} hour - 실행 시간 (0-23)
   * @param {number} minute - 실행 분 (0-59)
   * @param {boolean} enabled - 활성화 여부
   */
  updateSchedule: async (scheduleKey, hour, minute = 0, enabled = true) => {
    const response = await api.post(`/analytics/update_schedule/`, {
      schedule_key: scheduleKey,
      hour,
      minute,
      enabled
    });
    return response.data;
  },

  /**
   * 스케줄 설정 조회 (DB 오버라이드 포함)
   * @param {string} scheduleKey - 특정 스케줄만 조회 (선택)
   */
  getScheduleConfig: async (scheduleKey = null) => {
    const params = {};
    if (scheduleKey) params.schedule_key = scheduleKey;

    const response = await api.get(`/analytics/get_schedule_config/`, { params });
    return response.data;
  },

  /**
   * GSC 과거 트래픽 데이터 Backfill (최초 1회)
   * @param {number} domainId - 도메인 ID
   * @param {number} days - 가져올 기간 (기본 90일)
   */
  backfillGscTraffic: async (domainId, days = 90) => {
    const response = await api.post(`/analytics/backfill_gsc_traffic/`, {
      domain_id: domainId,
      days
    });
    return response.data;
  },

  /**
   * 저장된 트래픽 히스토리 조회
   * @param {number} domainId - 도메인 ID
   * @param {number} days - 조회 기간 (기본 30일)
   */
  getTrafficHistory: async (domainId, days = 30) => {
    const response = await api.get(`/analytics/traffic_history/`, {
      params: { domain_id: domainId, days }
    });
    return response.data;
  },
};

export default analyticsService;
