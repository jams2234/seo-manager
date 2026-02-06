/**
 * ScheduleSettingsModal
 * 스케줄 설정 및 상세 정보를 보여주는 모달
 * 스케줄 시간 편집 기능 포함
 */
import React, { useState, useEffect, useCallback } from 'react';
import ModalOverlay from '../common/ModalOverlay';
import analyticsService from '../../services/analyticsService';
import './ScheduleSettingsModal.css';

const ScheduleSettingsModal = ({ isOpen, onClose, domainId }) => {
  const [scheduleData, setScheduleData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(null);
  const [selectedTab, setSelectedTab] = useState('schedules'); // 'schedules' | 'history'
  const [editingSchedule, setEditingSchedule] = useState(null); // schedule key being edited
  const [editValues, setEditValues] = useState({ hour: 0, minute: 0 });
  const [saving, setSaving] = useState(false);

  // 스케줄 상태 조회
  const fetchScheduleStatus = useCallback(async () => {
    if (!domainId) return;

    setLoading(true);
    try {
      const data = await analyticsService.getScheduleStatus(domainId);
      setScheduleData(data);
    } catch (err) {
      console.error('Schedule status fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [domainId]);

  useEffect(() => {
    if (isOpen) {
      fetchScheduleStatus();
    }
  }, [isOpen, fetchScheduleStatus]);

  // 수동 동기화 트리거
  const handleTriggerSync = async (syncType) => {
    if (syncing) return;

    setSyncing(syncType);
    try {
      await analyticsService.triggerSync(domainId, syncType);
      setTimeout(fetchScheduleStatus, 2000);
    } catch (err) {
      console.error('Sync trigger error:', err);
    } finally {
      setSyncing(null);
    }
  };

  // GSC 과거 데이터 Backfill
  const handleBackfillTraffic = async () => {
    if (syncing) return;

    setSyncing('backfill');
    try {
      const result = await analyticsService.backfillGscTraffic(domainId, 90);
      alert(`✅ 과거 데이터 가져오기 완료\n\n기간: ${result.period?.start} ~ ${result.period?.end}\n가져온 데이터: ${result.stats?.fetched_rows}일\n새로 저장: ${result.stats?.created}건\n업데이트: ${result.stats?.updated}건`);
    } catch (err) {
      console.error('Backfill error:', err);
      alert('과거 데이터 가져오기에 실패했습니다.');
    } finally {
      setSyncing(null);
    }
  };

  // 스케줄 편집 시작
  const handleStartEdit = (schedule) => {
    // schedule_text에서 시간 추출 (예: "매일 04:00")
    const match = schedule.schedule_text.match(/(\d{1,2}):(\d{2})/);
    if (match) {
      setEditValues({
        hour: parseInt(match[1], 10),
        minute: parseInt(match[2], 10)
      });
    } else {
      setEditValues({ hour: 4, minute: 0 });
    }
    setEditingSchedule(schedule.key);
  };

  // 스케줄 편집 취소
  const handleCancelEdit = () => {
    setEditingSchedule(null);
    setEditValues({ hour: 0, minute: 0 });
  };

  // 스케줄 저장
  const handleSaveSchedule = async (scheduleKey) => {
    setSaving(true);
    try {
      await analyticsService.updateSchedule(
        scheduleKey,
        editValues.hour,
        editValues.minute,
        true
      );
      setEditingSchedule(null);
      // 스케줄 목록 새로고침
      await fetchScheduleStatus();
    } catch (err) {
      console.error('Schedule update error:', err);
      alert('스케줄 업데이트에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  // 시간 포맷
  const formatDateTime = (isoString) => {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 다음 실행까지 남은 시간
  const formatTimeUntil = (isoString) => {
    if (!isoString) return '-';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = date - now;

    if (diffMs < 0) return '곧 실행';

    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const remainingMins = diffMins % 60;

    if (diffHours > 0) {
      return remainingMins > 0 ? `${diffHours}시간 ${remainingMins}분 후` : `${diffHours}시간 후`;
    }
    return `${diffMins}분 후`;
  };

  // 스케줄 타입별 그룹핑
  const groupSchedulesByType = (schedules) => {
    const groups = {
      gsc: { label: 'GSC 동기화', icon: '🔍', schedules: [] },
      full_scan: { label: 'SEO 분석', icon: '📊', schedules: [] },
      ai_analysis: { label: 'AI 분석', icon: '🧠', schedules: [] },
      embedding: { label: '벡터 임베딩', icon: '🔄', schedules: [] },
      evaluation: { label: '효과성 평가', icon: '📈', schedules: [] },
      snapshot: { label: '스냅샷', icon: '📸', schedules: [] },
      other: { label: '기타', icon: '⏰', schedules: [] },
    };

    schedules?.forEach(s => {
      const type = s.type || 'other';
      if (groups[type]) {
        groups[type].schedules.push(s);
      } else {
        groups.other.schedules.push(s);
      }
    });

    return Object.entries(groups).filter(([_, g]) => g.schedules.length > 0);
  };

  // 시간 옵션 생성 (0-23)
  const hourOptions = Array.from({ length: 24 }, (_, i) => i);
  // 분 옵션 생성 (0, 15, 30, 45)
  const minuteOptions = [0, 15, 30, 45];

  if (!isOpen) return null;

  const groupedSchedules = groupSchedulesByType(scheduleData?.schedules);

  return (
    <ModalOverlay onClose={onClose} className="schedule-modal-overlay">
      <div className="schedule-modal">
        {/* Header */}
        <div className="schedule-modal-header">
          <h2>
            <span className="header-icon">⚙️</span>
            자동 동기화 스케줄
          </h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        {/* Tabs */}
        <div className="schedule-modal-tabs">
          <button
            className={`tab-btn ${selectedTab === 'schedules' ? 'active' : ''}`}
            onClick={() => setSelectedTab('schedules')}
          >
            📅 스케줄
          </button>
          <button
            className={`tab-btn ${selectedTab === 'history' ? 'active' : ''}`}
            onClick={() => setSelectedTab('history')}
          >
            📜 동기화 이력
          </button>
        </div>

        {/* Content */}
        <div className="schedule-modal-content">
          {loading ? (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>스케줄 정보를 불러오는 중...</p>
            </div>
          ) : selectedTab === 'schedules' ? (
            <>
              {/* Domain Info */}
              <div className="domain-info-card">
                <div className="domain-name">
                  {scheduleData?.domain?.name}
                </div>
                <div className="connection-status">
                  <span className={`status-badge ${scheduleData?.gsc_connected ? 'connected' : 'disconnected'}`}>
                    {scheduleData?.gsc_connected ? '🟢 GSC 연결됨' : '🔴 GSC 미연결'}
                  </span>
                  <span className={`status-badge ${scheduleData?.sync_status?.domain === 'active' ? 'active' : 'inactive'}`}>
                    {scheduleData?.sync_status?.domain === 'active' ? '활성' : '비활성'}
                  </span>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="quick-actions">
                <h3>빠른 실행</h3>
                <div className="action-buttons">
                  <button
                    className={`action-btn gsc ${syncing === 'gsc' ? 'syncing' : ''}`}
                    onClick={() => handleTriggerSync('gsc')}
                    disabled={syncing !== null}
                  >
                    {syncing === 'gsc' ? (
                      <span className="spinner-small" />
                    ) : (
                      <>
                        <span className="action-icon">🔍</span>
                        <span className="action-label">GSC 동기화</span>
                      </>
                    )}
                  </button>
                  <button
                    className={`action-btn scan ${syncing === 'full_scan' ? 'syncing' : ''}`}
                    onClick={() => handleTriggerSync('full_scan')}
                    disabled={syncing !== null}
                  >
                    {syncing === 'full_scan' ? (
                      <span className="spinner-small" />
                    ) : (
                      <>
                        <span className="action-icon">📊</span>
                        <span className="action-label">전체 스캔</span>
                      </>
                    )}
                  </button>
                  <button
                    className={`action-btn ai ${syncing === 'ai_analysis' ? 'syncing' : ''}`}
                    onClick={() => handleTriggerSync('ai_analysis')}
                    disabled={syncing !== null}
                  >
                    {syncing === 'ai_analysis' ? (
                      <span className="spinner-small" />
                    ) : (
                      <>
                        <span className="action-icon">🧠</span>
                        <span className="action-label">AI 분석</span>
                      </>
                    )}
                  </button>
                  <button
                    className={`action-btn backfill ${syncing === 'backfill' ? 'syncing' : ''}`}
                    onClick={handleBackfillTraffic}
                    disabled={syncing !== null || !scheduleData?.gsc_connected}
                    title={!scheduleData?.gsc_connected ? 'GSC 연결 필요' : '과거 90일 트래픽 데이터를 가져옵니다'}
                  >
                    {syncing === 'backfill' ? (
                      <span className="spinner-small" />
                    ) : (
                      <>
                        <span className="action-icon">📥</span>
                        <span className="action-label">과거 데이터</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Schedule List */}
              <div className="schedule-list">
                <h3>자동 스케줄 목록 <span className="edit-hint">(클릭하여 시간 변경)</span></h3>
                {groupedSchedules.map(([type, group]) => (
                  <div key={type} className="schedule-group">
                    <div className="group-header">
                      <span className="group-icon">{group.icon}</span>
                      <span className="group-label">{group.label}</span>
                    </div>
                    <div className="group-schedules">
                      {group.schedules.map(schedule => (
                        <div key={schedule.key} className={`schedule-item ${schedule.editable ? 'editable' : ''}`}>
                          {editingSchedule === schedule.key ? (
                            /* 편집 모드 */
                            <div className="schedule-edit-form">
                              <div className="edit-row">
                                <span className="schedule-name">{schedule.name}</span>
                                <div className="time-inputs">
                                  <select
                                    value={editValues.hour}
                                    onChange={(e) => setEditValues(prev => ({ ...prev, hour: parseInt(e.target.value, 10) }))}
                                    className="time-select"
                                  >
                                    {hourOptions.map(h => (
                                      <option key={h} value={h}>{h.toString().padStart(2, '0')}시</option>
                                    ))}
                                  </select>
                                  <span className="time-separator">:</span>
                                  <select
                                    value={editValues.minute}
                                    onChange={(e) => setEditValues(prev => ({ ...prev, minute: parseInt(e.target.value, 10) }))}
                                    className="time-select"
                                  >
                                    {minuteOptions.map(m => (
                                      <option key={m} value={m}>{m.toString().padStart(2, '0')}분</option>
                                    ))}
                                  </select>
                                </div>
                              </div>
                              <div className="edit-actions">
                                <button
                                  className="edit-btn save"
                                  onClick={() => handleSaveSchedule(schedule.key)}
                                  disabled={saving}
                                >
                                  {saving ? '저장 중...' : '저장'}
                                </button>
                                <button
                                  className="edit-btn cancel"
                                  onClick={handleCancelEdit}
                                  disabled={saving}
                                >
                                  취소
                                </button>
                              </div>
                            </div>
                          ) : (
                            /* 보기 모드 */
                            <>
                              <div
                                className="schedule-info"
                                onClick={() => schedule.editable && handleStartEdit(schedule)}
                                title={schedule.editable ? '클릭하여 시간 변경' : ''}
                              >
                                <span className="schedule-name">{schedule.name}</span>
                                <span className="schedule-time">
                                  {schedule.schedule_text}
                                  {schedule.editable && <span className="edit-icon">✏️</span>}
                                </span>
                              </div>
                              <div className="schedule-next">
                                <span className="next-label">다음 실행:</span>
                                <span className="next-time">{formatTimeUntil(schedule.next_run)}</span>
                              </div>
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* Info Note */}
              <div className="info-note">
                <span className="note-icon">💡</span>
                <span className="note-text">
                  스케줄은 서버에서 자동으로 실행됩니다.
                  GSC 데이터는 2-3일 지연이 있어 하루 2회 동기화로 충분합니다.
                  <br />
                  <strong>편집 가능한 스케줄</strong>을 클릭하여 실행 시간을 변경할 수 있습니다.
                </span>
              </div>
            </>
          ) : (
            /* History Tab */
            <div className="sync-history">
              <div className="history-card">
                <div className="history-header">
                  <span className="history-icon">🔍</span>
                  <span className="history-label">마지막 GSC 동기화</span>
                </div>
                <div className="history-time">
                  {formatDateTime(scheduleData?.last_sync?.gsc)}
                </div>
                <div className="history-status">
                  상태: <span className={`status-text ${scheduleData?.sync_status?.gsc}`}>
                    {scheduleData?.sync_status?.gsc || 'idle'}
                  </span>
                </div>
              </div>
              <div className="history-card">
                <div className="history-header">
                  <span className="history-icon">📊</span>
                  <span className="history-label">마지막 전체 스캔</span>
                </div>
                <div className="history-time">
                  {formatDateTime(scheduleData?.last_sync?.full_scan)}
                </div>
                <div className="history-status">
                  상태: <span className={`status-text ${scheduleData?.sync_status?.full_scan}`}>
                    {scheduleData?.sync_status?.full_scan || 'idle'}
                  </span>
                </div>
              </div>
              <div className="history-card">
                <div className="history-header">
                  <span className="history-icon">🧠</span>
                  <span className="history-label">마지막 AI 동기화</span>
                </div>
                <div className="history-time">
                  {formatDateTime(scheduleData?.last_sync?.ai_sync)}
                </div>
                <div className="history-status">
                  상태: <span className={`status-text ${scheduleData?.sync_status?.ai}`}>
                    {scheduleData?.sync_status?.ai || 'idle'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="schedule-modal-footer">
          <button className="footer-btn refresh" onClick={fetchScheduleStatus}>
            🔄 새로고침
          </button>
          <button className="footer-btn close" onClick={onClose}>
            닫기
          </button>
        </div>
      </div>
    </ModalOverlay>
  );
};

export default ScheduleSettingsModal;
