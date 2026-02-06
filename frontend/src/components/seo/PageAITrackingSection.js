/**
 * Page AI Tracking Section
 * Shows AI suggestions and tracking status for a specific page
 */
import React, { useState, useEffect } from 'react';
import { aiSuggestionService } from '../../services/aiLearningService';
import { getStatusLabel, getStatusColor, getTypeLabel } from '../../utils/aiUtils';
import { formatRelative } from '../../utils/dateUtils';
import './PageAITrackingSection.css';

const PageAITrackingSection = ({ pageId, domainId, onOpenImpactReport }) => {
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (pageId) {
      loadSuggestions();
    }
  }, [pageId]);

  const loadSuggestions = async () => {
    try {
      setLoading(true);
      // Get all suggestions for this page (tracking + tracked + applied)
      const response = await aiSuggestionService.list({ pageId });
      const allSuggestions = response.data.results || response.data || [];

      // Filter to show tracking/tracked/applied suggestions
      const relevantSuggestions = allSuggestions.filter(
        s => ['tracking', 'tracked', 'applied'].includes(s.status)
      );

      setSuggestions(relevantSuggestions);
    } catch (error) {
      console.error('Failed to load page suggestions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartTracking = async (suggestionId) => {
    try {
      await aiSuggestionService.startTracking(suggestionId);
      loadSuggestions();
    } catch (error) {
      console.error('Failed to start tracking:', error);
    }
  };

  const trackingSuggestions = suggestions.filter(s => s.status === 'tracking');
  const trackedSuggestions = suggestions.filter(s => s.status === 'tracked');
  const appliedSuggestions = suggestions.filter(s => s.status === 'applied');

  const totalCount = suggestions.length;
  const trackingCount = trackingSuggestions.length;

  if (loading) {
    return (
      <div className="page-ai-tracking-section loading">
        <div className="section-header">
          <span className="section-icon">🧠</span>
          <span className="section-title">AI 제안 추적</span>
        </div>
        <div className="loading-text">로딩 중...</div>
      </div>
    );
  }

  if (totalCount === 0) {
    return null; // Don't show section if no relevant suggestions
  }

  return (
    <div className="page-ai-tracking-section">
      <div
        className="section-header clickable"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="header-left">
          <span className="section-icon">🧠</span>
          <span className="section-title">AI 제안 추적</span>
          {trackingCount > 0 && (
            <span className="tracking-badge">
              📊 추적중 {trackingCount}
            </span>
          )}
        </div>
        <div className="header-right">
          <span className="total-count">{totalCount}개</span>
          <span className={`expand-icon ${expanded ? 'expanded' : ''}`}>▼</span>
        </div>
      </div>

      {expanded && (
        <div className="section-content">
          {/* Tracking Suggestions */}
          {trackingSuggestions.length > 0 && (
            <div className="suggestion-group tracking">
              <div className="group-header">
                <span className="group-icon">📊</span>
                <span className="group-title">추적 중</span>
                <span className="group-count">{trackingSuggestions.length}</span>
              </div>
              {trackingSuggestions.map(s => (
                <SuggestionItem
                  key={s.id}
                  suggestion={s}
                  onViewReport={() => onOpenImpactReport && onOpenImpactReport(s.id)}
                />
              ))}
            </div>
          )}

          {/* Tracked (Completed) Suggestions */}
          {trackedSuggestions.length > 0 && (
            <div className="suggestion-group tracked">
              <div className="group-header">
                <span className="group-icon">✅</span>
                <span className="group-title">추적 완료</span>
                <span className="group-count">{trackedSuggestions.length}</span>
              </div>
              {trackedSuggestions.map(s => (
                <SuggestionItem
                  key={s.id}
                  suggestion={s}
                  onViewReport={() => onOpenImpactReport && onOpenImpactReport(s.id)}
                />
              ))}
            </div>
          )}

          {/* Applied (Not yet tracking) Suggestions */}
          {appliedSuggestions.length > 0 && (
            <div className="suggestion-group applied">
              <div className="group-header">
                <span className="group-icon">🔧</span>
                <span className="group-title">적용됨 (추적 대기)</span>
                <span className="group-count">{appliedSuggestions.length}</span>
              </div>
              {appliedSuggestions.map(s => (
                <SuggestionItem
                  key={s.id}
                  suggestion={s}
                  onStartTracking={() => handleStartTracking(s.id)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const SuggestionItem = ({ suggestion, onViewReport, onStartTracking }) => {
  const statusColor = getStatusColor(suggestion.status);
  const typeLabel = getTypeLabel(suggestion.suggestion_type);

  return (
    <div className="suggestion-item">
      <div className="suggestion-main">
        <span className="suggestion-type-badge">{typeLabel}</span>
        <span className="suggestion-title">{suggestion.title}</span>
      </div>
      <div className="suggestion-meta">
        <span
          className="suggestion-status"
          style={{ color: statusColor }}
        >
          {getStatusLabel(suggestion.status)}
        </span>
        {suggestion.tracking_days > 0 && (
          <span className="tracking-days">
            {suggestion.tracking_days}일 추적
          </span>
        )}
        {suggestion.effectiveness_score && (
          <span className={`effectiveness-score ${suggestion.effectiveness_score >= 60 ? 'positive' : 'negative'}`}>
            효과 {suggestion.effectiveness_score.toFixed(0)}점
          </span>
        )}
        <span className="suggestion-date">
          {formatRelative(suggestion.created_at)}
        </span>
      </div>
      <div className="suggestion-actions">
        {suggestion.status === 'tracking' && onViewReport && (
          <button
            className="btn-view-report"
            onClick={onViewReport}
          >
            📈 현황
          </button>
        )}
        {suggestion.status === 'tracked' && onViewReport && (
          <button
            className="btn-view-report"
            onClick={onViewReport}
          >
            📋 리포트
          </button>
        )}
        {suggestion.status === 'applied' && onStartTracking && (
          <button
            className="btn-start-tracking"
            onClick={onStartTracking}
          >
            📊 추적 시작
          </button>
        )}
      </div>
    </div>
  );
};

export default PageAITrackingSection;
