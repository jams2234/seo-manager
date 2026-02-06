/**
 * 날짜/시간 포맷팅 유틸리티
 */

/**
 * 날짜를 한국어 형식으로 포맷
 * @param {string|Date} date - 날짜
 * @returns {string} 2026-02-06
 */
export const formatDate = (date) => {
  if (!date) return '-';
  try {
    return new Date(date).toLocaleDateString('ko-KR');
  } catch {
    return '-';
  }
};

/**
 * 날짜와 시간을 한국어 형식으로 포맷
 * @param {string|Date} date - 날짜
 * @returns {string} 2026. 2. 6. 오후 2:30:00
 */
export const formatDateTime = (date) => {
  if (!date) return '-';
  try {
    return new Date(date).toLocaleString('ko-KR');
  } catch {
    return '-';
  }
};

/**
 * 짧은 날짜/시간 포맷 (초 제외)
 * @param {string|Date} date - 날짜
 * @returns {string} 2026. 2. 6. 14:30
 */
export const formatDateTimeShort = (date) => {
  if (!date) return '-';
  try {
    return new Date(date).toLocaleString('ko-KR', {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '-';
  }
};

/**
 * 상대 시간 포맷 (예: 3시간 전, 2일 전)
 * @param {string|Date} date - 날짜
 * @returns {string}
 */
export const formatRelative = (date) => {
  if (!date) return '-';
  try {
    const now = new Date();
    const target = new Date(date);
    const diffMs = now - target;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return '방금 전';
    if (diffMin < 60) return `${diffMin}분 전`;
    if (diffHour < 24) return `${diffHour}시간 전`;
    if (diffDay < 7) return `${diffDay}일 전`;
    if (diffDay < 30) return `${Math.floor(diffDay / 7)}주 전`;
    if (diffDay < 365) return `${Math.floor(diffDay / 30)}개월 전`;
    return `${Math.floor(diffDay / 365)}년 전`;
  } catch {
    return '-';
  }
};

/**
 * 소요 시간 포맷 (초 → 분/초)
 * @param {number|string} duration - 초 단위 시간 또는 문자열
 * @returns {string}
 */
export const formatDuration = (duration) => {
  if (!duration) return '-';
  if (typeof duration === 'string') return duration;

  const seconds = Math.round(duration);
  if (seconds < 60) return `${seconds}초`;

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes < 60) {
    return remainingSeconds > 0
      ? `${minutes}분 ${remainingSeconds}초`
      : `${minutes}분`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}시간 ${remainingMinutes}분`;
};

/**
 * ISO 날짜 문자열 생성 (YYYY-MM-DD)
 * @param {Date} date - 날짜
 * @returns {string}
 */
export const toISODateString = (date = new Date()) => {
  return date.toISOString().split('T')[0];
};

/**
 * 날짜 범위 문자열 생성
 * @param {Date} start - 시작일
 * @param {Date} end - 종료일
 * @returns {string}
 */
export const formatDateRange = (start, end) => {
  if (!start || !end) return '-';
  return `${formatDate(start)} ~ ${formatDate(end)}`;
};

export default {
  formatDate,
  formatDateTime,
  formatDateTimeShort,
  formatRelative,
  formatDuration,
  toISODateString,
  formatDateRange,
};
