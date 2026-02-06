/**
 * AI Effectiveness Dashboard Component
 * AI 수정의 효과성 평가 대시보드
 */
import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../../services/api';
import './AIEffectivenessDashboard.css';

const AIEffectivenessDashboard = ({ domainId }) => {
  const [stats, setStats] = useState(null);
  const [recentFixes, setRecentFixes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('30d');

  // 효과성 통계 로드
  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const params = { time_range: timeRange };
      if (domainId) params.domain_id = domainId;

      // 효과성 통계 API 호출
      const [statsRes, fixesRes] = await Promise.all([
        apiClient.get('/seo-issues/effectiveness_stats/', { params }),
        apiClient.get('/seo-issues/recent_fixes/', { params: { ...params, limit: 10 } }),
      ]);

      setStats(statsRes.data);
      setRecentFixes(fixesRes.data || []);
    } catch (error) {
      console.error('효과성 통계 로드 실패:', error);
      // 에러 시 기본값 설정
      setStats({
        total_fixes: 0,
        effective: 0,
        ineffective: 0,
        unknown: 0,
        effectiveness_rate: 0,
        avg_resolution_time: null,
        recurrence_rate: 0,
      });
    } finally {
      setLoading(false);
    }
  }, [domainId, timeRange]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // 효과성 배지 색상
  const getEffectivenessColor = (effectiveness) => {
    switch (effectiveness) {
      case 'effective': return '#10b981';
      case 'ineffective': return '#ef4444';
      case 'partial': return '#f59e0b';
      default: return '#6b7280';
    }
  };

  // 효과성 라벨
  const getEffectivenessLabel = (effectiveness) => {
    switch (effectiveness) {
      case 'effective': return '효과적';
      case 'ineffective': return '비효과적';
      case 'partial': return '부분적';
      default: return '평가중';
    }
  };

  if (loading) {
    return (
      <div className="effectiveness-dashboard loading">
        <div className="loading-spinner"></div>
        <p>효과성 데이터 로드 중...</p>
      </div>
    );
  }

  const effectivenessRate = stats?.effectiveness_rate || 0;

  return (
    <div className="effectiveness-dashboard">
      {/* 헤더 */}
      <div className="dashboard-header">
        <div className="header-title">
          <span className="header-icon">📈</span>
          <h3>AI 수정 효과성 평가</h3>
        </div>
        <div className="header-controls">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="time-range-select"
          >
            <option value="7d">최근 7일</option>
            <option value="30d">최근 30일</option>
            <option value="90d">최근 90일</option>
            <option value="all">전체</option>
          </select>
          <button className="btn-refresh" onClick={loadStats}>
            🔄 새로고침
          </button>
        </div>
      </div>

      {/* 효과성 점수 카드 */}
      <div className="effectiveness-score-card">
        <div className="score-circle">
          <svg viewBox="0 0 100 100" className="score-svg">
            <circle
              cx="50"
              cy="50"
              r="45"
              fill="none"
              stroke="#e2e8f0"
              strokeWidth="10"
            />
            <circle
              cx="50"
              cy="50"
              r="45"
              fill="none"
              stroke={effectivenessRate >= 70 ? '#10b981' : effectivenessRate >= 50 ? '#f59e0b' : '#ef4444'}
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={`${effectivenessRate * 2.83} 283`}
              transform="rotate(-90 50 50)"
            />
          </svg>
          <div className="score-text">
            <span className="score-value">{Math.round(effectivenessRate)}%</span>
            <span className="score-label">효과율</span>
          </div>
        </div>
        <div className="score-details">
          <p className="score-description">
            AI 수정 중 <strong>{stats?.effective || 0}건</strong>이 효과적이었습니다.
          </p>
          {stats?.recurrence_rate > 0 && (
            <p className="recurrence-warning">
              ⚠️ 재발률: {(stats.recurrence_rate * 100).toFixed(1)}%
            </p>
          )}
        </div>
      </div>

      {/* 통계 그리드 */}
      <div className="stats-grid">
        <div className="stat-item total">
          <span className="stat-icon">🔧</span>
          <span className="stat-value">{stats?.total_fixes || 0}</span>
          <span className="stat-label">총 수정</span>
        </div>
        <div className="stat-item effective">
          <span className="stat-icon">✅</span>
          <span className="stat-value">{stats?.effective || 0}</span>
          <span className="stat-label">효과적</span>
        </div>
        <div className="stat-item ineffective">
          <span className="stat-icon">❌</span>
          <span className="stat-value">{stats?.ineffective || 0}</span>
          <span className="stat-label">비효과적</span>
        </div>
        <div className="stat-item pending">
          <span className="stat-icon">⏳</span>
          <span className="stat-value">{stats?.unknown || 0}</span>
          <span className="stat-label">평가중</span>
        </div>
      </div>

      {/* 평균 해결 시간 */}
      {stats?.avg_resolution_time && (
        <div className="resolution-time-card">
          <span className="rt-icon">⏱️</span>
          <div className="rt-content">
            <span className="rt-value">{stats.avg_resolution_time}</span>
            <span className="rt-label">평균 해결 시간</span>
          </div>
        </div>
      )}

      {/* 최근 수정 이력 */}
      <div className="recent-fixes-section">
        <h4>최근 수정 이력</h4>
        {recentFixes.length > 0 ? (
          <div className="fixes-list">
            {recentFixes.map((fix, idx) => (
              <div key={fix.id || idx} className="fix-item">
                <div className="fix-header">
                  <span
                    className="fix-effectiveness"
                    style={{ backgroundColor: getEffectivenessColor(fix.effectiveness) }}
                  >
                    {getEffectivenessLabel(fix.effectiveness)}
                  </span>
                  <span className="fix-type">{fix.issue_type}</span>
                  <span className="fix-date">
                    {fix.created_at ? new Date(fix.created_at).toLocaleDateString('ko-KR') : '-'}
                  </span>
                </div>
                <div className="fix-details">
                  {fix.page_url && (
                    <span className="fix-page" title={fix.page_url}>
                      📄 {fix.page_url.length > 50 ? fix.page_url.substring(0, 47) + '...' : fix.page_url}
                    </span>
                  )}
                  {fix.issue_recurred && (
                    <span className="fix-recurred">🔄 재발 ({fix.recurrence_count || 1}회)</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="no-fixes">
            <p>수정 이력이 없습니다.</p>
          </div>
        )}
      </div>

      {/* 개선 팁 */}
      <div className="improvement-tips">
        <h4>💡 효과성 개선 팁</h4>
        <ul>
          {effectivenessRate < 50 && (
            <li>수정 후 검증 프로세스를 강화하세요.</li>
          )}
          {stats?.recurrence_rate > 0.1 && (
            <li>재발하는 이슈의 근본 원인을 분석하세요.</li>
          )}
          {stats?.unknown > stats?.effective && (
            <li>더 많은 수정에 대해 효과성 평가를 진행하세요.</li>
          )}
          {effectivenessRate >= 70 && (
            <li>좋은 성과입니다! 현재 패턴을 유지하세요.</li>
          )}
        </ul>
      </div>
    </div>
  );
};

export default AIEffectivenessDashboard;
