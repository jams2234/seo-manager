/**
 * AI Learning Quality Guide Component
 * 학습 품질 향상을 위한 가이드 및 추천
 */
import React, { useMemo } from 'react';
import './AILearningQualityGuide.css';

const AILearningQualityGuide = ({ learningState, suggestions }) => {
  // 품질 점수 및 개선점 분석
  const qualityAnalysis = useMemo(() => {
    const analysis = {
      score: learningState?.quality_score || 0,
      level: 'low',
      strengths: [],
      improvements: [],
      actions: [],
    };

    // 레벨 결정
    if (analysis.score >= 80) {
      analysis.level = 'high';
    } else if (analysis.score >= 50) {
      analysis.level = 'medium';
    }

    // 데이터 동기화 상태 분석
    const pagesSynced = learningState?.pages_synced || 0;
    const embeddingsUpdated = learningState?.embeddings_updated || 0;

    if (pagesSynced >= 50) {
      analysis.strengths.push({
        icon: '📄',
        text: `${pagesSynced}개 페이지가 학습되었습니다.`,
      });
    } else if (pagesSynced > 0) {
      analysis.improvements.push({
        icon: '📄',
        text: '더 많은 페이지 데이터가 필요합니다.',
        detail: `현재 ${pagesSynced}개 페이지만 학습됨`,
      });
      analysis.actions.push({
        icon: '➕',
        text: '새 페이지 추가 또는 사이트맵 업데이트',
        priority: 'high',
      });
    } else {
      analysis.improvements.push({
        icon: '📄',
        text: '학습된 페이지가 없습니다.',
        detail: '먼저 동기화를 실행하세요',
      });
      analysis.actions.push({
        icon: '🔄',
        text: '학습 동기화 실행',
        priority: 'critical',
      });
    }

    // 임베딩 상태 분석
    if (embeddingsUpdated >= pagesSynced * 0.8 && embeddingsUpdated > 0) {
      analysis.strengths.push({
        icon: '🧠',
        text: '페이지 임베딩이 최신 상태입니다.',
      });
    } else if (embeddingsUpdated > 0) {
      analysis.improvements.push({
        icon: '🧠',
        text: '일부 페이지의 임베딩이 오래되었습니다.',
        detail: `${embeddingsUpdated}/${pagesSynced} 임베딩 업데이트됨`,
      });
      analysis.actions.push({
        icon: '🔄',
        text: '임베딩 재동기화 권장',
        priority: 'medium',
      });
    }

    // 제안 상태 분석
    const pendingSuggestions = suggestions?.filter(s => s.status === 'pending')?.length || 0;
    const appliedSuggestions = suggestions?.filter(s => s.status === 'applied')?.length || 0;
    const rejectedSuggestions = suggestions?.filter(s => s.status === 'rejected')?.length || 0;

    if (appliedSuggestions >= 5) {
      analysis.strengths.push({
        icon: '✅',
        text: `${appliedSuggestions}개 제안이 적용되었습니다.`,
      });
    }

    if (pendingSuggestions > 10) {
      analysis.improvements.push({
        icon: '⏳',
        text: '처리되지 않은 제안이 많습니다.',
        detail: `${pendingSuggestions}개 제안 대기 중`,
      });
      analysis.actions.push({
        icon: '👁️',
        text: '대기 중인 제안 검토',
        priority: 'medium',
      });
    }

    // 피드백 분석
    const feedbackCount = suggestions?.filter(s => s.user_feedback)?.length || 0;
    const totalApplied = appliedSuggestions + rejectedSuggestions;

    if (feedbackCount >= totalApplied * 0.5 && feedbackCount > 0) {
      analysis.strengths.push({
        icon: '💬',
        text: '피드백이 충분히 제공되고 있습니다.',
      });
    } else if (totalApplied > 5 && feedbackCount < totalApplied * 0.3) {
      analysis.improvements.push({
        icon: '💬',
        text: '더 많은 피드백이 필요합니다.',
        detail: 'AI 학습 품질 향상에 도움됩니다',
      });
      analysis.actions.push({
        icon: '💬',
        text: '적용된 제안에 피드백 제공',
        priority: 'low',
      });
    }

    // 마지막 분석 시간 확인
    const lastAnalysis = learningState?.last_analysis_at;
    if (lastAnalysis) {
      const daysSince = Math.floor(
        (Date.now() - new Date(lastAnalysis).getTime()) / (1000 * 60 * 60 * 24)
      );
      if (daysSince <= 1) {
        analysis.strengths.push({
          icon: '📊',
          text: '최근 AI 분석이 실행되었습니다.',
        });
      } else if (daysSince > 7) {
        analysis.improvements.push({
          icon: '📊',
          text: `${daysSince}일 동안 분석이 실행되지 않았습니다.`,
          detail: '최신 데이터 분석 필요',
        });
        analysis.actions.push({
          icon: '🔍',
          text: 'AI 분석 실행',
          priority: 'high',
        });
      }
    }

    return analysis;
  }, [learningState, suggestions]);

  // 레벨 색상
  const getLevelColor = (level) => {
    switch (level) {
      case 'high': return '#10b981';
      case 'medium': return '#f59e0b';
      default: return '#ef4444';
    }
  };

  // 레벨 라벨
  const getLevelLabel = (level) => {
    switch (level) {
      case 'high': return '우수';
      case 'medium': return '보통';
      default: return '개선 필요';
    }
  };

  // 우선순위 색상
  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'critical': return '#ef4444';
      case 'high': return '#f59e0b';
      case 'medium': return '#3b82f6';
      default: return '#6b7280';
    }
  };

  return (
    <div className="quality-guide">
      {/* 품질 점수 헤더 */}
      <div className="quality-header">
        <div className="quality-score-container">
          <div
            className="quality-score-ring"
            style={{
              background: `conic-gradient(${getLevelColor(qualityAnalysis.level)} ${qualityAnalysis.score * 3.6}deg, #e2e8f0 0deg)`,
            }}
          >
            <div className="quality-score-inner">
              <span className="quality-score-value">{qualityAnalysis.score}</span>
              <span className="quality-score-label">품질 점수</span>
            </div>
          </div>
        </div>
        <div className="quality-level-info">
          <span
            className="quality-level-badge"
            style={{ backgroundColor: getLevelColor(qualityAnalysis.level) }}
          >
            {getLevelLabel(qualityAnalysis.level)}
          </span>
          <p className="quality-description">
            {qualityAnalysis.level === 'high' && 'AI 학습이 잘 진행되고 있습니다!'}
            {qualityAnalysis.level === 'medium' && '몇 가지 개선점이 있습니다.'}
            {qualityAnalysis.level === 'low' && '학습 품질 향상이 필요합니다.'}
          </p>
        </div>
      </div>

      {/* 강점 */}
      {qualityAnalysis.strengths.length > 0 && (
        <div className="quality-section strengths">
          <h4>✨ 강점</h4>
          <ul>
            {qualityAnalysis.strengths.map((item, idx) => (
              <li key={idx}>
                <span className="item-icon">{item.icon}</span>
                <span className="item-text">{item.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 개선점 */}
      {qualityAnalysis.improvements.length > 0 && (
        <div className="quality-section improvements">
          <h4>📈 개선점</h4>
          <ul>
            {qualityAnalysis.improvements.map((item, idx) => (
              <li key={idx}>
                <span className="item-icon">{item.icon}</span>
                <div className="item-content">
                  <span className="item-text">{item.text}</span>
                  {item.detail && (
                    <span className="item-detail">{item.detail}</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 권장 액션 */}
      {qualityAnalysis.actions.length > 0 && (
        <div className="quality-section actions">
          <h4>🎯 권장 액션</h4>
          <div className="actions-list">
            {qualityAnalysis.actions
              .sort((a, b) => {
                const order = { critical: 0, high: 1, medium: 2, low: 3 };
                return order[a.priority] - order[b.priority];
              })
              .map((item, idx) => (
                <div key={idx} className="action-item">
                  <span
                    className="action-priority"
                    style={{ backgroundColor: getPriorityColor(item.priority) }}
                  />
                  <span className="action-icon">{item.icon}</span>
                  <span className="action-text">{item.text}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* 팁 */}
      <div className="quality-tips">
        <h4>💡 학습 품질 향상 팁</h4>
        <ul>
          <li>정기적으로 AI 분석을 실행하여 최신 인사이트를 얻으세요.</li>
          <li>제안에 대한 피드백을 제공하면 AI가 더 정확한 제안을 합니다.</li>
          <li>사이트맵을 최신 상태로 유지하면 학습 품질이 향상됩니다.</li>
          <li>적용한 제안의 효과를 모니터링하고 결과를 기록하세요.</li>
        </ul>
      </div>
    </div>
  );
};

export default AILearningQualityGuide;
