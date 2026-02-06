/**
 * AI Suggestions List Component
 * 페이지별로 그룹화된 AI 제안 목록 (항상 펼쳐진 상태)
 */
import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { aiSuggestionService } from '../../services/aiLearningService';
import toastService from '../../services/toastService';
import AISuggestionCard from './AISuggestionCard';
import { getStatusColor, getStatusLabel, getPathFromUrl } from '../../utils/aiUtils';
import './AISuggestionsList.css';

const AISuggestionsList = ({ domainId, onRefresh }) => {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false); // 백그라운드 새로고침 (스피너 없이)
  const [filter, setFilter] = useState({
    status: '',
    type: '',
    priority: '',
  });
  const [viewMode, setViewMode] = useState('byPage'); // 'byPage' | 'byStatus'

  // 스크롤 위치 유지를 위한 ref
  const scrollPositionRef = useRef(0);
  const shouldRestoreScrollRef = useRef(false);

  // 스크롤 위치 저장
  const saveScrollPosition = useCallback(() => {
    scrollPositionRef.current = window.scrollY || document.documentElement.scrollTop;
    shouldRestoreScrollRef.current = true;
  }, []);

  // 스크롤 위치 복원
  const restoreScrollPosition = useCallback(() => {
    if (shouldRestoreScrollRef.current) {
      const savedPosition = scrollPositionRef.current;
      // 여러 번의 프레임 후에 스크롤 복원 (React 렌더링 완료 보장)
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          window.scrollTo(0, savedPosition);
          // 추가 안전장치: setTimeout으로 한번 더 시도
          setTimeout(() => {
            window.scrollTo(0, savedPosition);
          }, 50);
        });
      });
      shouldRestoreScrollRef.current = false;
    }
  }, []);

  // 제안 목록 로드
  const loadSuggestions = useCallback(async (preserveScroll = false) => {
    try {
      if (preserveScroll) {
        // 스크롤 유지 모드: 로딩 스피너 표시 안함 (콘텐츠 유지)
        saveScrollPosition();
        setIsRefreshing(true);
      } else {
        // 일반 모드: 로딩 스피너 표시
        setLoading(true);
      }

      const res = await aiSuggestionService.list({
        domainId,
        status: filter.status || undefined,
        type: filter.type || undefined,
        priority: filter.priority || undefined,
      });
      const data = res.data.results || res.data || [];
      setSuggestions(data);
    } catch (error) {
      console.error('제안 목록 로드 실패:', error);
    } finally {
      if (preserveScroll) {
        setIsRefreshing(false);
        // 데이터 업데이트 후 스크롤 복원
        restoreScrollPosition();
      } else {
        setLoading(false);
      }
    }
  }, [domainId, filter, saveScrollPosition, restoreScrollPosition]);

  useEffect(() => {
    loadSuggestions();
  }, [loadSuggestions]);

  // 제안 액션 핸들러 (loadSuggestions(true)가 스크롤 저장/복원 처리)
  const handleAccept = async (id, deployToGit = false) => {
    try {
      const response = await aiSuggestionService.accept(id, deployToGit);
      const data = response.data;

      // 응답에 따른 피드백
      if (data?.success) {
        if (data?.tracking?.success) {
          // 자동 적용 + 추적 시작 성공
          toastService.success('제안이 적용되고 효과 추적이 시작되었습니다.');
        } else if (data?.result?.success) {
          // 자동 적용 성공 (추적은 실패 또는 해당 없음)
          toastService.success(data.message || '제안이 적용되었습니다.');
        } else {
          // 수락만 됨 (수동 적용 필요)
          toastService.info(data.message || '제안이 수락되었습니다.');
        }
      } else {
        toastService.warning(data?.message || '처리 완료 (일부 실패)');
      }

      await loadSuggestions(true); // 스크롤 위치 유지 및 await
      onRefresh?.();
    } catch (error) {
      console.error('제안 수락 실패:', error);
      toastService.error('제안 수락 실패');
    }
  };

  const handleReject = async (id, reason) => {
    try {
      await aiSuggestionService.reject(id, reason);
      await loadSuggestions(true);
      onRefresh?.();
    } catch (error) {
      console.error('제안 거절 실패:', error);
    }
  };

  const handleDefer = async (id) => {
    try {
      await aiSuggestionService.defer(id);
      await loadSuggestions(true);
    } catch (error) {
      console.error('제안 보류 실패:', error);
    }
  };

  const handleMarkApplied = async (id) => {
    try {
      await aiSuggestionService.markApplied(id);
      await loadSuggestions(true);
      onRefresh?.();
    } catch (error) {
      console.error('적용 완료 표시 실패:', error);
    }
  };

  const handleFeedback = async (id, feedbackType, comment) => {
    try {
      await aiSuggestionService.feedback(id, feedbackType, comment);
      await loadSuggestions(true);
    } catch (error) {
      console.error('피드백 제출 실패:', error);
    }
  };

  // 필터 변경
  const handleFilterChange = (key, value) => {
    setFilter((prev) => ({ ...prev, [key]: value }));
  };

  // 페이지별 그룹화
  const groupedByPage = useMemo(() => {
    const groups = {};

    suggestions.forEach((suggestion) => {
      const pageKey = suggestion.page_url || '__sitewide__';
      if (!groups[pageKey]) {
        groups[pageKey] = {
          pageUrl: suggestion.page_url,
          pageTitle: suggestion.action_data?.page_title || null,
          suggestions: [],
          statusCounts: {
            pending: 0,
            accepted: 0,
            applied: 0,
            tracking: 0,
            tracked: 0,
            rejected: 0,
            deferred: 0,
          },
        };
      }
      groups[pageKey].suggestions.push(suggestion);
      groups[pageKey].statusCounts[suggestion.status] =
        (groups[pageKey].statusCounts[suggestion.status] || 0) + 1;
    });

    // 정렬: 사이트 전체 먼저, 그 다음 pending 많은 순
    const sortedKeys = Object.keys(groups).sort((a, b) => {
      if (a === '__sitewide__') return -1;
      if (b === '__sitewide__') return 1;
      const aPending = groups[a].statusCounts.pending;
      const bPending = groups[b].statusCounts.pending;
      if (aPending !== bPending) return bPending - aPending;
      return a.localeCompare(b);
    });

    const sorted = {};
    sortedKeys.forEach((key) => {
      sorted[key] = groups[key];
    });

    return sorted;
  }, [suggestions]);

  // 상태별 그룹화 (기존 방식)
  const groupedByStatus = useMemo(() => ({
    pending: suggestions.filter((s) => s.status === 'pending'),
    accepted: suggestions.filter((s) => s.status === 'accepted'),
    applied: suggestions.filter((s) => s.status === 'applied'),
    tracking: suggestions.filter((s) => s.status === 'tracking'),
    tracked: suggestions.filter((s) => s.status === 'tracked'),
    rejected: suggestions.filter((s) => s.status === 'rejected'),
    deferred: suggestions.filter((s) => s.status === 'deferred'),
  }), [suggestions]);

  // 스크롤 유지하며 새로고침하는 콜백
  const handleUpdateWithScroll = useCallback(async () => {
    await loadSuggestions(true);
  }, [loadSuggestions]);

  // 렌더링: 제안 카드
  const renderSuggestionCard = (suggestion) => (
    <AISuggestionCard
      key={suggestion.id}
      suggestion={suggestion}
      onAccept={handleAccept}
      onReject={handleReject}
      onDefer={handleDefer}
      onMarkApplied={handleMarkApplied}
      onFeedback={handleFeedback}
      onUpdate={handleUpdateWithScroll}
    />
  );

  // 페이지별 뷰 - 항상 펼쳐진 상태
  const renderByPageView = () => {
    const pageCount = Object.keys(groupedByPage).length;

    return (
      <div className="page-list-view">
        <div className="page-list-header">
          <span className="page-count">{pageCount}개 페이지</span>
        </div>

        {Object.entries(groupedByPage).map(([pageKey, group]) => {
          const isSitewide = pageKey === '__sitewide__';
          const pendingCount = group.statusCounts.pending;
          const appliedCount = group.statusCounts.applied;
          const trackingCount = group.statusCounts.tracking + group.statusCounts.tracked;

          return (
            <div key={pageKey} className={`page-section ${isSitewide ? 'sitewide' : ''}`}>
              {/* 페이지 타이틀 바 */}
              <div className="page-title-bar">
                <div className="page-title-info">
                  <span className="page-icon">{isSitewide ? '🌐' : '📄'}</span>
                  <span className="page-path">
                    {isSitewide ? '사이트 전체' : getPathFromUrl(group.pageUrl)}
                  </span>
                </div>
                <div className="page-status-badges">
                  {pendingCount > 0 && (
                    <span className="mini-badge pending">대기 {pendingCount}</span>
                  )}
                  {appliedCount > 0 && (
                    <span className="mini-badge applied">적용 {appliedCount}</span>
                  )}
                  {trackingCount > 0 && (
                    <span className="mini-badge tracking">추적 {trackingCount}</span>
                  )}
                </div>
              </div>

              {/* 제안 카드들 - 바로 표시 */}
              <div className="page-suggestions">
                {group.suggestions.map(renderSuggestionCard)}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // 상태별 뷰 (기존 방식)
  const renderByStatusView = () => (
    <>
      {Object.entries(groupedByStatus).map(([status, items]) => {
        if (items.length === 0) return null;

        return (
          <div key={status} className={`suggestions-section ${status === 'rejected' ? 'collapsed' : ''}`}>
            <h4 className={`section-title ${status}`}>
              <span className="status-dot" style={{ backgroundColor: getStatusColor(status) }} />
              {getStatusLabel(status)} ({items.length})
            </h4>
            <div className="suggestions-grid">
              {items.map(renderSuggestionCard)}
            </div>
          </div>
        );
      })}
    </>
  );

  return (
    <div className="ai-suggestions-list">
      {/* 필터 */}
      <div className="suggestions-filter">
        <div className="filter-group">
          <label>상태</label>
          <select
            value={filter.status}
            onChange={(e) => handleFilterChange('status', e.target.value)}
          >
            <option value="">전체</option>
            <option value="pending">대기중</option>
            <option value="accepted">수락됨</option>
            <option value="applied">적용됨</option>
            <option value="tracking">추적중</option>
            <option value="tracked">추적완료</option>
            <option value="rejected">거절됨</option>
            <option value="deferred">보류</option>
          </select>
        </div>

        <div className="filter-group">
          <label>유형</label>
          <select
            value={filter.type}
            onChange={(e) => handleFilterChange('type', e.target.value)}
          >
            <option value="">전체</option>
            <option value="title">제목</option>
            <option value="description">설명</option>
            <option value="content">콘텐츠</option>
            <option value="structure">구조</option>
            <option value="keyword">키워드</option>
            <option value="internal_link">내부 링크</option>
            <option value="quick_win">Quick Win</option>
            <option value="priority_action">우선 액션</option>
          </select>
        </div>

        <div className="filter-group">
          <label>우선순위</label>
          <select
            value={filter.priority}
            onChange={(e) => handleFilterChange('priority', e.target.value)}
          >
            <option value="">전체</option>
            <option value="1">높음</option>
            <option value="2">중간</option>
            <option value="3">낮음</option>
          </select>
        </div>

        {/* 뷰 모드 토글 */}
        <div className="view-mode-toggle">
          <button
            className={`view-btn ${viewMode === 'byPage' ? 'active' : ''}`}
            onClick={() => setViewMode('byPage')}
            title="페이지별 보기"
          >
            📄 페이지별
          </button>
          <button
            className={`view-btn ${viewMode === 'byStatus' ? 'active' : ''}`}
            onClick={() => setViewMode('byStatus')}
            title="상태별 보기"
          >
            📊 상태별
          </button>
        </div>

        <button className="btn-refresh" onClick={() => loadSuggestions(false)}>
          🔄 새로고침
        </button>
      </div>

      {/* 제안 목록 */}
      {loading ? (
        <div className="suggestions-loading">
          <div className="loading-spinner small"></div>
          <span>제안 로드 중...</span>
        </div>
      ) : suggestions.length === 0 ? (
        <div className="suggestions-empty">
          <span className="empty-icon">💡</span>
          <p>제안이 없습니다.</p>
          <p className="empty-hint">AI 분석을 실행하여 새로운 제안을 생성하세요.</p>
        </div>
      ) : (
        <div className={`suggestions-content ${isRefreshing ? 'refreshing' : ''}`}>
          {viewMode === 'byPage' ? renderByPageView() : renderByStatusView()}
        </div>
      )}
    </div>
  );
};

export default AISuggestionsList;
