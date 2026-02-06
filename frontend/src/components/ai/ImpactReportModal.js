/**
 * ImpactReportModal
 * AI 제안 효과 분석 리포트 모달
 */
import React, { useState, useEffect, useCallback } from 'react';
import TrackingChart from './TrackingChart';
import { aiSuggestionService } from '../../services/aiLearningService';
import toastService from '../../services/toastService';
import './ImpactReportModal.css';

const EFFECT_LABELS = {
  positive: { label: '긍정적', color: '#10b981', icon: '📈' },
  negative: { label: '부정적', color: '#ef4444', icon: '📉' },
  neutral: { label: '중립', color: '#6b7280', icon: '➖' },
  inconclusive: { label: '불확실', color: '#f59e0b', icon: '❓' },
};

const TREND_LABELS = {
  improving: { label: '상승 추세', color: '#10b981', icon: '📈' },
  stable: { label: '안정', color: '#6b7280', icon: '➡️' },
  declining: { label: '하락 추세', color: '#ef4444', icon: '📉' },
  volatile: { label: '변동성', color: '#f59e0b', icon: '📊' },
};

const ImpactReportModal = ({ suggestionId, onClose, onTrackingEnd }) => {
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [endingTracking, setEndingTracking] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [selectedMetric, setSelectedMetric] = useState('impressions');

  // 데이터 로드
  const loadData = useCallback(async () => {
    if (!suggestionId) return;

    setLoading(true);
    try {
      const response = await aiSuggestionService.getTrackingData(suggestionId);
      if (response.data?.success) {
        setData(response.data);
        setError(null);
      } else {
        setError(response.data?.message || '데이터 로드 실패');
      }
    } catch (err) {
      console.error('Tracking data load error:', err);
      setError('데이터를 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  }, [suggestionId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // AI 분석 실행
  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      const response = await aiSuggestionService.analyzeImpact(suggestionId, 'manual');
      if (response.data?.success) {
        toastService.success('AI 분석이 완료되었습니다.');
        await loadData();
      } else {
        toastService.error(response.data?.message || '분석 실패');
      }
    } catch (err) {
      console.error('Impact analysis error:', err);
      toastService.error('분석 중 오류가 발생했습니다.');
    } finally {
      setAnalyzing(false);
    }
  };

  // 추적 종료
  const handleEndTracking = async (runFinalAnalysis = true) => {
    if (!window.confirm(
      runFinalAnalysis
        ? '추적을 종료하고 최종 분석을 실행하시겠습니까?'
        : '추적을 종료하시겠습니까? (최종 분석 없이)'
    )) {
      return;
    }

    setEndingTracking(true);
    try {
      const response = await aiSuggestionService.endTracking(suggestionId, runFinalAnalysis);
      if (response.data?.success) {
        toastService.success(`추적이 종료되었습니다. (${response.data.tracking_days}일)`);
        if (onTrackingEnd) {
          onTrackingEnd(response.data);
        }
        onClose();
      } else {
        toastService.error(response.data?.message || '추적 종료 실패');
      }
    } catch (err) {
      console.error('End tracking error:', err);
      toastService.error('추적 종료 중 오류가 발생했습니다.');
    } finally {
      setEndingTracking(false);
    }
  };

  // 스냅샷 수동 캡처
  const handleCaptureSnapshot = async () => {
    try {
      const response = await aiSuggestionService.captureSnapshot(suggestionId);
      if (response.data?.success) {
        toastService.success(`Day ${response.data.day_number} 스냅샷 캡처 완료`);
        await loadData();
      } else {
        toastService.error(response.data?.message || '스냅샷 캡처 실패');
      }
    } catch (err) {
      console.error('Snapshot capture error:', err);
      toastService.error('스냅샷 캡처 실패');
    }
  };

  // 효과 점수 색상
  const getScoreColor = (score) => {
    if (score >= 70) return '#10b981';
    if (score >= 50) return '#f59e0b';
    return '#ef4444';
  };

  if (loading) {
    return (
      <div className="impact-report-modal-overlay" onClick={onClose}>
        <div className="impact-report-modal" onClick={e => e.stopPropagation()}>
          <div className="modal-loading">
            <div className="spinner" />
            <span>데이터 로딩 중...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="impact-report-modal-overlay" onClick={onClose}>
        <div className="impact-report-modal" onClick={e => e.stopPropagation()}>
          <div className="modal-error">
            <div className="error-icon">⚠️</div>
            <div className="error-text">{error}</div>
            <button className="btn-retry" onClick={loadData}>다시 시도</button>
          </div>
        </div>
      </div>
    );
  }

  const { suggestion, baseline, current, snapshots, chart_data, analysis_logs, summary } = data;
  const latestAnalysis = suggestion?.impact_analysis || analysis_logs?.[0]?.ai_analysis;
  const effectInfo = EFFECT_LABELS[latestAnalysis?.overall_effect] || EFFECT_LABELS.inconclusive;
  const trendInfo = TREND_LABELS[summary?.overall_trend] || analysis_logs?.[0]?.trend_direction;

  return (
    <div className="impact-report-modal-overlay" onClick={onClose}>
      <div className="impact-report-modal" onClick={e => e.stopPropagation()}>
        {/* 헤더 */}
        <div className="modal-header">
          <div className="header-content">
            <h2>효과 분석 리포트</h2>
            <div className="suggestion-info">
              <span className="suggestion-type">{suggestion?.type}</span>
              <span className="suggestion-title">{suggestion?.title}</span>
            </div>
            {suggestion?.page_url && (
              <div className="page-url">{suggestion.page_url}</div>
            )}
          </div>
          <button className="btn-close" onClick={onClose}>×</button>
        </div>

        {/* 메인 콘텐츠 */}
        <div className="modal-content">
          {/* 상태 카드 */}
          <div className="status-cards">
            {/* 추적 상태 */}
            <div className="status-card tracking-status">
              <div className="card-header">
                <span className="card-icon">📊</span>
                <span className="card-title">추적 상태</span>
              </div>
              <div className="card-content">
                <div className="status-value">
                  <span className={`status-badge ${suggestion?.status}`}>
                    {suggestion?.status === 'tracking' ? '추적중' : '추적완료'}
                  </span>
                </div>
                <div className="tracking-days">
                  {suggestion?.tracking_days || snapshots?.length || 0}일 추적
                </div>
              </div>
            </div>

            {/* 효과성 점수 */}
            <div className="status-card effectiveness-score">
              <div className="card-header">
                <span className="card-icon">🎯</span>
                <span className="card-title">효과성 점수</span>
              </div>
              <div className="card-content">
                <div
                  className="score-value"
                  style={{ color: getScoreColor(suggestion?.effectiveness_score || 0) }}
                >
                  {suggestion?.effectiveness_score?.toFixed(1) || '-'}
                </div>
                <div className="score-max">/ 100</div>
              </div>
            </div>

            {/* 전체 효과 */}
            <div className="status-card overall-effect">
              <div className="card-header">
                <span className="card-icon">{effectInfo.icon}</span>
                <span className="card-title">전체 효과</span>
              </div>
              <div className="card-content">
                <div className="effect-label" style={{ color: effectInfo.color }}>
                  {effectInfo.label}
                </div>
                {latestAnalysis?.confidence && (
                  <div className="confidence">
                    신뢰도: {(latestAnalysis.confidence * 100).toFixed(0)}%
                  </div>
                )}
              </div>
            </div>

            {/* 트렌드 */}
            {trendInfo && (
              <div className="status-card trend">
                <div className="card-header">
                  <span className="card-icon">{TREND_LABELS[trendInfo]?.icon || '📈'}</span>
                  <span className="card-title">트렌드</span>
                </div>
                <div className="card-content">
                  <div className="trend-label" style={{ color: TREND_LABELS[trendInfo]?.color }}>
                    {TREND_LABELS[trendInfo]?.label || trendInfo}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* AI 분석 요약 */}
          {latestAnalysis?.summary && (
            <div className="analysis-summary">
              <div className="summary-header">
                <span className="summary-icon">🤖</span>
                <span className="summary-title">AI 분석 요약</span>
              </div>
              <div className="summary-text">{latestAnalysis.summary}</div>
            </div>
          )}

          {/* 차트 */}
          <div className="chart-section">
            <TrackingChart
              chartData={chart_data}
              baseline={baseline}
              snapshots={snapshots}
              selectedMetric={selectedMetric}
              onMetricChange={setSelectedMetric}
              height={280}
            />
          </div>

          {/* 요인 분석 */}
          {latestAnalysis?.factors?.length > 0 && (
            <div className="factors-section">
              <div className="section-header">
                <span className="section-icon">🔍</span>
                <span className="section-title">요인 분석</span>
              </div>
              <div className="factors-list">
                {latestAnalysis.factors.map((factor, idx) => (
                  <div key={idx} className={`factor-item ${factor.effect}`}>
                    <span className="factor-icon">
                      {factor.effect === 'positive' ? '✅' :
                       factor.effect === 'negative' ? '❌' : '➖'}
                    </span>
                    <div className="factor-content">
                      <div className="factor-name">{factor.factor}</div>
                      {factor.description && (
                        <div className="factor-desc">{factor.description}</div>
                      )}
                    </div>
                    {factor.confidence && (
                      <div className="factor-confidence">
                        {(factor.confidence * 100).toFixed(0)}%
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 권장사항 */}
          {latestAnalysis?.recommendations?.length > 0 && (
            <div className="recommendations-section">
              <div className="section-header">
                <span className="section-icon">💡</span>
                <span className="section-title">권장사항</span>
              </div>
              <ul className="recommendations-list">
                {latestAnalysis.recommendations.map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 분석 이력 */}
          {analysis_logs?.length > 0 && (
            <div className="analysis-history">
              <div className="section-header">
                <span className="section-icon">📋</span>
                <span className="section-title">분석 이력</span>
              </div>
              <div className="history-timeline">
                {analysis_logs.map((log, idx) => (
                  <div key={log.id || idx} className="history-item">
                    <div className="history-date">
                      {new Date(log.created_at).toLocaleDateString('ko-KR')}
                    </div>
                    <div className="history-type">
                      {log.type === 'weekly' ? '주간 분석' :
                       log.type === 'final' ? '최종 분석' :
                       log.type === 'milestone' ? '마일스톤' : '수동 분석'}
                    </div>
                    <div className="history-day">Day {log.days_since_applied}</div>
                    {log.effectiveness_score && (
                      <div className="history-score">
                        점수: {log.effectiveness_score?.toFixed(1)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 푸터 액션 */}
        <div className="modal-footer">
          <div className="footer-left">
            <button
              className="btn-secondary"
              onClick={handleCaptureSnapshot}
              disabled={suggestion?.status !== 'tracking'}
            >
              📸 스냅샷 캡처
            </button>
            <button
              className="btn-secondary"
              onClick={handleAnalyze}
              disabled={analyzing}
            >
              {analyzing ? (
                <>
                  <span className="spinner-small" />
                  분석 중...
                </>
              ) : (
                <>🔍 AI 분석 실행</>
              )}
            </button>
          </div>

          <div className="footer-right">
            {suggestion?.status === 'tracking' && (
              <>
                <button
                  className="btn-warning"
                  onClick={() => handleEndTracking(false)}
                  disabled={endingTracking}
                >
                  추적만 종료
                </button>
                <button
                  className="btn-primary"
                  onClick={() => handleEndTracking(true)}
                  disabled={endingTracking}
                >
                  {endingTracking ? (
                    <>
                      <span className="spinner-small" />
                      종료 중...
                    </>
                  ) : (
                    <>✅ 추적 종료 + 최종 분석</>
                  )}
                </button>
              </>
            )}
            {suggestion?.status === 'tracked' && (
              <button className="btn-primary" onClick={onClose}>
                확인
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ImpactReportModal;
