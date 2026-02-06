/**
 * AI 관련 공통 유틸리티
 * 상태, 우선순위, 유형 등의 상수 및 헬퍼 함수
 */

// 제안 상태 정보
export const SUGGESTION_STATUS = {
  pending: { label: '대기중', color: '#f59e0b', icon: '⏳' },
  accepted: { label: '수락됨', color: '#3b82f6', icon: '✓' },
  applied: { label: '적용됨', color: '#10b981', icon: '✅' },
  rejected: { label: '거절됨', color: '#ef4444', icon: '❌' },
  deferred: { label: '보류', color: '#6b7280', icon: '⏸️' },
  tracking: { label: '추적중', color: '#8b5cf6', icon: '📊' },
  tracked: { label: '추적완료', color: '#6366f1', icon: '📈' },
};

// 우선순위 정보
export const PRIORITY_INFO = {
  1: { label: '높음', color: '#ef4444', icon: '🔴' },
  2: { label: '중간', color: '#f59e0b', icon: '🟡' },
  3: { label: '낮음', color: '#10b981', icon: '🟢' },
};

// 제안 유형 정보
export const SUGGESTION_TYPES = {
  title: { label: '제목', icon: '📝' },
  description: { label: '설명', icon: '📋' },
  content: { label: '콘텐츠', icon: '📄' },
  structure: { label: '구조', icon: '🏗️' },
  keyword: { label: '키워드', icon: '🔑' },
  internal_link: { label: '내부 링크', icon: '🔗' },
  quick_win: { label: 'Quick Win', icon: '⚡' },
  priority_action: { label: '우선 액션', icon: '🎯' },
  technical: { label: '기술', icon: '⚙️' },
  performance: { label: '성능', icon: '🚀' },
  general: { label: '일반', icon: '💡' },
  bulk_fix_descriptions: { label: '메타설명 일괄', icon: '📋' },
  bulk_fix_titles: { label: '제목 일괄', icon: '📝' },
};

// 분석/태스크 상태 색상
export const TASK_STATUS_COLORS = {
  success: '#10b981',
  completed: '#10b981',
  syncing: '#3b82f6',
  running: '#3b82f6',
  pending: '#f59e0b',
  failed: '#ef4444',
  idle: '#6b7280',
};

/**
 * 상태 정보 가져오기
 * @param {string} status - 상태 코드
 * @returns {{ label: string, color: string, icon: string }}
 */
export const getStatusInfo = (status) => {
  return SUGGESTION_STATUS[status] || { label: status, color: '#6b7280', icon: '?' };
};

/**
 * 상태 라벨 가져오기
 * @param {string} status - 상태 코드
 * @returns {string}
 */
export const getStatusLabel = (status) => {
  return SUGGESTION_STATUS[status]?.label || status;
};

/**
 * 상태 색상 가져오기
 * @param {string} status - 상태 코드
 * @returns {string}
 */
export const getStatusColor = (status) => {
  return SUGGESTION_STATUS[status]?.color || '#6b7280';
};

/**
 * 우선순위 정보 가져오기
 * @param {number} priority - 우선순위 (1, 2, 3)
 * @returns {{ label: string, color: string, icon: string }}
 */
export const getPriorityInfo = (priority) => {
  return PRIORITY_INFO[priority] || { label: '-', color: '#6b7280', icon: '⚪' };
};

/**
 * 우선순위 라벨 가져오기
 * @param {number} priority - 우선순위 (1, 2, 3)
 * @returns {string}
 */
export const getPriorityLabel = (priority) => {
  return PRIORITY_INFO[priority]?.label || '-';
};

/**
 * 제안 유형 정보 가져오기
 * @param {string} type - 유형 코드
 * @returns {{ label: string, icon: string }}
 */
export const getTypeInfo = (type) => {
  return SUGGESTION_TYPES[type] || { label: type, icon: '💡' };
};

/**
 * 제안 유형 라벨 가져오기
 * @param {string} type - 유형 코드
 * @returns {string}
 */
export const getTypeLabel = (type) => {
  return SUGGESTION_TYPES[type]?.label || type;
};

/**
 * 제안 유형 아이콘 가져오기
 * @param {string} type - 유형 코드
 * @returns {string}
 */
export const getTypeIcon = (type) => {
  return SUGGESTION_TYPES[type]?.icon || '💡';
};

/**
 * 태스크 상태 색상 가져오기
 * @param {string} status - 태스크 상태
 * @returns {string}
 */
export const getTaskStatusColor = (status) => {
  return TASK_STATUS_COLORS[status] || '#6b7280';
};

/**
 * URL에서 경로만 추출
 * @param {string} url - 전체 URL
 * @returns {string}
 */
export const getPathFromUrl = (url) => {
  if (!url) return '/';
  try {
    const urlObj = new URL(url);
    return urlObj.pathname || '/';
  } catch {
    return url;
  }
};

/**
 * 자동 적용 가능한 제안 유형인지 확인
 * @param {string} type - 제안 유형
 * @returns {boolean}
 */
export const isAutoApplicableType = (type) => {
  const autoTypes = [
    'title', 'description', 'structure',
    'keyword', 'internal_link', 'quick_win', 'priority_action',
    'bulk_fix_descriptions', 'bulk_fix_titles'
  ];
  return autoTypes.includes(type);
};

export default {
  SUGGESTION_STATUS,
  PRIORITY_INFO,
  SUGGESTION_TYPES,
  TASK_STATUS_COLORS,
  getStatusInfo,
  getStatusLabel,
  getStatusColor,
  getPriorityInfo,
  getPriorityLabel,
  getTypeInfo,
  getTypeLabel,
  getTypeIcon,
  getTaskStatusColor,
  getPathFromUrl,
  isAutoApplicableType,
};
