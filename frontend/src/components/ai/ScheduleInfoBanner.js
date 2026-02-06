/**
 * ScheduleInfoBanner
 * 화면 상단에 스케줄 상태를 표시하는 배너 컴포넌트
 */
import React, { useState, useEffect, useCallback } from 'react';
import analyticsService from '../../services/analyticsService';
import './ScheduleInfoBanner.css';

const ScheduleInfoBanner = ({ domainId, onOpenSettings }) => {
  const [scheduleData, setScheduleData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(null); // 'gsc' | 'full_scan' | 'ai_analysis' | null
  const [showTooltip, setShowTooltip] = useState(false);
  const [error, setError] = useState(null);

  // 스케줄 상태 조회
  const fetchScheduleStatus = useCallback(async () => {
    if (!domainId) return;

    try {
      const data = await analyticsService.getScheduleStatus(domainId);
      setScheduleData(data);
      setError(null);
    } catch (err) {
      console.error('Schedule status fetch error:', err);
      setError('스케줄 정보를 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  }, [domainId]);

  useEffect(() => {
    fetchScheduleStatus();
    // 1분마다 갱신
    const interval = setInterval(fetchScheduleStatus, 60000);
    return () => clearInterval(interval);
  }, [fetchScheduleStatus]);

  // 수동 동기화 트리거
  const handleTriggerSync = async (syncType) => {
    if (syncing) return;

    setSyncing(syncType);
    try {
      await analyticsService.triggerSync(domainId, syncType);
      // 잠시 후 상태 갱신
      setTimeout(fetchScheduleStatus, 2000);
    } catch (err) {
      console.error('Sync trigger error:', err);
      setError('동기화 시작 실패');
    } finally {
      setSyncing(null);
    }
  };

  // 시간 포맷
  const formatTime = (isoString) => {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleString('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 상대 시간 (얼마 전)
  const formatRelativeTime = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return '방금 전';
    if (diffMins < 60) return `${diffMins}분 전`;
    if (diffHours < 24) return `${diffHours}시간 전`;
    return `${diffDays}일 전`;
  };

  // 다음 실행까지 남은 시간
  const formatTimeUntil = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = date - now;

    if (diffMs < 0) return '곧 실행';

    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const remainingMins = diffMins % 60;

    if (diffMins < 60) return `${diffMins}분 후`;
    if (diffHours < 24) {
      // 시간 + 분 모두 표시 (모달과 일관성 유지)
      return remainingMins > 0 ? `${diffHours}시간 ${remainingMins}분 후` : `${diffHours}시간 후`;
    }
    return formatTime(isoString);
  };

  // 다음 GSC 동기화 스케줄 찾기
  const getNextGscSync = () => {
    if (!scheduleData?.schedules) return null;
    const gscSchedules = scheduleData.schedules
      .filter(s => s.type === 'gsc' && s.next_run)
      .sort((a, b) => new Date(a.next_run) - new Date(b.next_run));
    return gscSchedules[0];
  };

  if (loading) {
    return (
      <div className="schedule-banner loading">
        <div className="schedule-banner-content">
          <span className="loading-text">스케줄 정보 로딩 중...</span>
        </div>
      </div>
    );
  }

  if (error && !scheduleData) {
    return (
      <div className="schedule-banner error">
        <div className="schedule-banner-content">
          <span className="error-icon">⚠️</span>
          <span className="error-text">{error}</span>
          <button onClick={fetchScheduleStatus} className="retry-btn">
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  const nextGsc = getNextGscSync();
  const lastSync = scheduleData?.last_sync;
  const gscConnected = scheduleData?.gsc_connected;

  return (
    <div className="schedule-banner">
      <div className="schedule-banner-content">
        {/* GSC 연결 상태 */}
        <div className="schedule-status-item">
          <span className={`status-indicator ${gscConnected ? 'connected' : 'disconnected'}`}>
            {gscConnected ? '🟢' : '🔴'}
          </span>
          <span className="status-label">GSC</span>
        </div>

        {/* 마지막 동기화 */}
        <div
          className="schedule-info-item"
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
        >
          <span className="info-icon">🔄</span>
          <span className="info-label">마지막 동기화:</span>
          <span className="info-value">
            {lastSync?.gsc ? formatRelativeTime(lastSync.gsc) : '없음'}
          </span>

          {/* 상세 툴팁 */}
          {showTooltip && (
            <div className="schedule-tooltip">
              <div className="tooltip-header">동기화 상태</div>
              <div className="tooltip-content">
                <div className="tooltip-row">
                  <span className="tooltip-label">GSC 동기화:</span>
                  <span className="tooltip-value">{formatTime(lastSync?.gsc)}</span>
                </div>
                <div className="tooltip-row">
                  <span className="tooltip-label">전체 스캔:</span>
                  <span className="tooltip-value">{formatTime(lastSync?.full_scan)}</span>
                </div>
                <div className="tooltip-row">
                  <span className="tooltip-label">AI 동기화:</span>
                  <span className="tooltip-value">{formatTime(lastSync?.ai_sync)}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 다음 예정 */}
        {nextGsc && (
          <div className="schedule-info-item next-sync">
            <span className="info-icon">⏰</span>
            <span className="info-label">다음:</span>
            <span className="info-value highlight">{formatTimeUntil(nextGsc.next_run)}</span>
          </div>
        )}

        {/* 액션 버튼들 */}
        <div className="schedule-actions">
          <button
            className={`sync-btn ${syncing === 'gsc' ? 'syncing' : ''}`}
            onClick={() => handleTriggerSync('gsc')}
            disabled={syncing !== null}
            title="GSC 동기화 실행"
          >
            {syncing === 'gsc' ? (
              <span className="spinner-small" />
            ) : (
              '🔄 GSC'
            )}
          </button>

          <button
            className={`sync-btn ${syncing === 'full_scan' ? 'syncing' : ''}`}
            onClick={() => handleTriggerSync('full_scan')}
            disabled={syncing !== null}
            title="전체 스캔 실행"
          >
            {syncing === 'full_scan' ? (
              <span className="spinner-small" />
            ) : (
              '📊 스캔'
            )}
          </button>

          <button
            className="settings-btn"
            onClick={onOpenSettings}
            title="스케줄 설정"
          >
            ⚙️
          </button>
        </div>
      </div>
    </div>
  );
};

export default ScheduleInfoBanner;
