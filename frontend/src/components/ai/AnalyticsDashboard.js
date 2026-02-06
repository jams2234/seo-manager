/**
 * Analytics Dashboard
 * 도메인 및 페이지별 SEO 성과 추적 대시보드
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import analyticsService from '../../services/analyticsService';
import ScheduleInfoBanner from './ScheduleInfoBanner';
import ScheduleSettingsModal from './ScheduleSettingsModal';
import './AnalyticsDashboard.css';

const AnalyticsDashboard = ({ domainId }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(30);

  // Data states
  const [overview, setOverview] = useState(null);
  const [pageTrends, setPageTrends] = useState(null);
  const [keywordTrends, setKeywordTrends] = useState(null);

  // UI states
  const [selectedTab, setSelectedTab] = useState('overview'); // overview, pages, keywords
  const [expandedPages, setExpandedPages] = useState(new Set());
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  // Fetch all data
  const fetchData = useCallback(async () => {
    if (!domainId) return;

    setLoading(true);
    setError(null);

    try {
      const [overviewData, pagesData, keywordsData] = await Promise.all([
        analyticsService.getDomainOverview(domainId, days),
        analyticsService.getPageTrends(domainId, days),
        analyticsService.getKeywordTrends(domainId, days),
      ]);

      setOverview(overviewData);
      setPageTrends(pagesData);
      setKeywordTrends(keywordsData);
    } catch (err) {
      console.error('Analytics fetch error:', err);
      setError(err.message || '데이터를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }, [domainId, days]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Toggle page expansion
  const togglePage = (pageId) => {
    setExpandedPages(prev => {
      const next = new Set(prev);
      if (next.has(pageId)) {
        next.delete(pageId);
      } else {
        next.add(pageId);
      }
      return next;
    });
  };

  if (loading) {
    return (
      <div className="analytics-loading">
        <div className="spinner"></div>
        <p>SEO 성과 데이터를 불러오는 중...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analytics-error">
        <span className="error-icon">⚠️</span>
        <p>{error}</p>
        <button onClick={fetchData}>다시 시도</button>
      </div>
    );
  }

  return (
    <div className="analytics-dashboard">
      {/* Schedule Info Banner */}
      <ScheduleInfoBanner
        domainId={domainId}
        onOpenSettings={() => setShowSettingsModal(true)}
      />

      {/* Header */}
      <div className="analytics-header">
        <h2>📊 SEO 성과 분석</h2>
        <div className="analytics-controls">
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>최근 7일</option>
            <option value={30}>최근 30일</option>
            <option value={60}>최근 60일</option>
            <option value={90}>최근 90일</option>
          </select>
          <button className="refresh-btn" onClick={fetchData}>
            🔄 새로고침
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="analytics-tabs">
        <button
          className={`tab-btn ${selectedTab === 'overview' ? 'active' : ''}`}
          onClick={() => setSelectedTab('overview')}
        >
          📈 개요
        </button>
        <button
          className={`tab-btn ${selectedTab === 'pages' ? 'active' : ''}`}
          onClick={() => setSelectedTab('pages')}
        >
          📄 페이지별 ({pageTrends?.pages?.length || 0})
        </button>
        <button
          className={`tab-btn ${selectedTab === 'keywords' ? 'active' : ''}`}
          onClick={() => setSelectedTab('keywords')}
        >
          🔍 키워드 ({keywordTrends?.total_keywords || 0})
        </button>
      </div>

      {/* Content */}
      <div className="analytics-content">
        {selectedTab === 'overview' && overview && (
          <OverviewTab data={overview} />
        )}
        {selectedTab === 'pages' && pageTrends && (
          <PagesTab
            data={pageTrends}
            expandedPages={expandedPages}
            togglePage={togglePage}
          />
        )}
        {selectedTab === 'keywords' && keywordTrends && (
          <KeywordsTab data={keywordTrends} />
        )}
      </div>

      {/* Schedule Settings Modal */}
      <ScheduleSettingsModal
        isOpen={showSettingsModal}
        onClose={() => setShowSettingsModal(false)}
        domainId={domainId}
      />
    </div>
  );
};

// ============================================================================
// Helper: Fill missing dates in trends data
// ============================================================================
const fillMissingDates = (trends, period) => {
  if (!period?.start || !period?.end) return trends;

  const startDate = new Date(period.start);
  const endDate = new Date(period.end);
  const trendMap = new Map();

  // Map existing data by date string (YYYY-MM-DD)
  trends.forEach(t => {
    if (t.date) {
      const dateKey = t.date.split('T')[0];
      trendMap.set(dateKey, t);
    }
  });

  const filledData = [];
  const currentDate = new Date(startDate);

  while (currentDate <= endDate) {
    const dateKey = currentDate.toISOString().split('T')[0];
    const existing = trendMap.get(dateKey);

    if (existing) {
      filledData.push({
        ...existing,
        dateLabel: currentDate.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }),
      });
    } else {
      // Add empty data point for missing date
      filledData.push({
        date: dateKey,
        dateLabel: currentDate.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }),
        seo_score: null,
        health_score: null,
        performance_score: null,
        impressions: null,
        clicks: null,
        ctr: null,
        avg_position: null,
        page_count: 0,
      });
    }

    currentDate.setDate(currentDate.getDate() + 1);
  }

  return filledData;
};

// ============================================================================
// Overview Tab
// ============================================================================
const OverviewTab = ({ data }) => {
  const { current_stats, comparison, trends, period, domain } = data;

  // Fill missing dates and format chart data
  const filledTrends = fillMissingDates(trends, period);

  // For display, only show every Nth label to avoid crowding
  const chartData = filledTrends.map((t, idx) => ({
    ...t,
    // Show label every 3-7 days depending on period
    displayDate: idx % Math.max(1, Math.floor(filledTrends.length / 10)) === 0 ? t.dateLabel : '',
  }));

  // Count actual data points
  const actualDataPoints = trends.length;
  const hasEnoughData = actualDataPoints >= 3;

  return (
    <div className="overview-tab">
      {/* Domain Score Cards */}
      <div className="score-cards">
        <ScoreCard
          title="Health Score"
          value={current_stats.health_score}
          icon="❤️"
          color="#ef4444"
          subtitle="이슈 기반 점수 (SEO 패널과 동일)"
        />
        <ScoreCard
          title="도메인 대표 스코어"
          value={current_stats.domain_score}
          icon="🏆"
          color="#667eea"
          subtitle="Health 50% + Perf 25% + 인덱싱 15% + CTR 10%"
        />
        <ScoreCard
          title="Lighthouse SEO"
          value={current_stats.lighthouse_seo_score}
          icon="📊"
          color="#10b981"
          subtitle="기술적 SEO 준수도"
        />
        <ScoreCard
          title="노출 키워드"
          value={current_stats.keyword_count}
          change={comparison?.changes?.keywords}
          icon="🔍"
          color="#f59e0b"
          unit="개"
        />
      </div>

      {/* Traffic Stats */}
      <div className="traffic-stats">
        <div className="stat-item">
          <span className="stat-label">총 노출수</span>
          <span className="stat-value">
            {current_stats.impressions?.toLocaleString() || 0}
            {comparison?.changes?.impressions !== undefined && (
              <ChangeIndicator value={comparison.changes.impressions} />
            )}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">총 클릭수</span>
          <span className="stat-value">
            {current_stats.clicks?.toLocaleString() || 0}
            {comparison?.changes?.clicks !== undefined && (
              <ChangeIndicator value={comparison.changes.clicks} />
            )}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">평균 CTR</span>
          <span className="stat-value">{current_stats.ctr || 0}%</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">인덱싱률</span>
          <span className="stat-value">
            {current_stats.indexed_pages}/{current_stats.total_pages} ({current_stats.indexing_rate}%)
          </span>
        </div>
      </div>

      {/* Data Availability Notice */}
      {!hasEnoughData && (
        <div className="data-notice">
          <span className="notice-icon">📊</span>
          <div className="notice-content">
            <span className="notice-title">데이터 수집 중</span>
            <span className="notice-desc">
              현재 {actualDataPoints}일치 데이터가 수집되었습니다.
              3일 이상의 데이터가 쌓이면 의미 있는 트렌드를 확인할 수 있습니다.
              매일 자동으로 데이터가 수집됩니다.
            </span>
          </div>
        </div>
      )}

      {/* Trends Chart - SEO & Health Score */}
      <div className="chart-section">
        <h3>📈 SEO 스코어 트렌드 <span className="chart-subtitle">({actualDataPoints}일 데이터)</span></h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <defs>
              <linearGradient id="colorSeo" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#667eea" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#667eea" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorHealth" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="displayDate"
              stroke="#9ca3af"
              fontSize={11}
              interval={0}
              tick={{ fill: '#9ca3af' }}
            />
            <YAxis domain={[0, 100]} stroke="#9ca3af" fontSize={12} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1f2937',
                border: 'none',
                borderRadius: '8px',
                color: '#fff'
              }}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.dateLabel || ''}
              formatter={(value, name) => [value !== null ? value : '데이터 없음', name]}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="seo_score"
              name="SEO 스코어"
              stroke="#667eea"
              strokeWidth={2}
              dot={{ fill: '#667eea', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6 }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="health_score"
              name="건강 스코어"
              stroke="#10b981"
              strokeWidth={2}
              dot={{ fill: '#10b981', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6 }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Traffic Chart */}
      <div className="chart-section">
        <h3>📊 트래픽 트렌드 <span className="chart-subtitle">(일별 노출/클릭)</span></h3>
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorImpressions" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#667eea" stopOpacity={0.4}/>
                <stop offset="95%" stopColor="#667eea" stopOpacity={0.1}/>
              </linearGradient>
              <linearGradient id="colorClicks" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0.1}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="displayDate"
              stroke="#9ca3af"
              fontSize={11}
              interval={0}
            />
            <YAxis stroke="#9ca3af" fontSize={12} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1f2937',
                border: 'none',
                borderRadius: '8px',
                color: '#fff'
              }}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.dateLabel || ''}
              formatter={(value, name) => [value !== null ? value?.toLocaleString() : '데이터 없음', name]}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="impressions"
              name="노출수"
              stroke="#667eea"
              fill="url(#colorImpressions)"
              strokeWidth={2}
              dot={{ fill: '#667eea', strokeWidth: 1, r: 3 }}
              connectNulls
            />
            <Area
              type="monotone"
              dataKey="clicks"
              name="클릭수"
              stroke="#10b981"
              fill="url(#colorClicks)"
              strokeWidth={2}
              dot={{ fill: '#10b981', strokeWidth: 1, r: 3 }}
              connectNulls
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Comparison Summary */}
      {comparison && (
        <div className="comparison-section">
          <h3>📅 기간 비교 ({comparison.start?.page_count}개 페이지)</h3>
          <div className="comparison-grid">
            <ComparisonCard
              label="SEO 스코어"
              start={comparison.start?.avg_seo_score}
              current={comparison.current?.avg_seo_score}
              change={comparison.changes?.seo_score}
              unit="점"
            />
            <ComparisonCard
              label="총 노출수"
              start={comparison.start?.total_impressions}
              current={comparison.current?.total_impressions}
              change={comparison.changes?.impressions}
            />
            <ComparisonCard
              label="총 클릭수"
              start={comparison.start?.total_clicks}
              current={comparison.current?.total_clicks}
              change={comparison.changes?.clicks}
            />
            <ComparisonCard
              label="키워드 수"
              start={comparison.start?.total_keywords}
              current={comparison.current?.total_keywords}
              change={comparison.changes?.keywords}
              unit="개"
            />
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Pages Tab
// ============================================================================
const PagesTab = ({ data, expandedPages, togglePage }) => {
  const { pages } = data;

  if (!pages || pages.length === 0) {
    return (
      <div className="empty-state">
        <span className="empty-icon">📄</span>
        <p>트렌드 데이터가 있는 페이지가 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="pages-tab">
      <div className="pages-header">
        <span>{pages.length}개 페이지</span>
        <div className="legend">
          <span className="legend-item seo">Lighthouse SEO</span>
          <span className="legend-item health">Performance</span>
          <span className="legend-item traffic" title="이슈 기반">❤️ Health</span>
        </div>
      </div>

      <div className="pages-list">
        {pages.map((page) => (
          <PageTrendCard
            key={page.page_id}
            page={page}
            isExpanded={expandedPages.has(page.page_id)}
            onToggle={() => togglePage(page.page_id)}
          />
        ))}
      </div>
    </div>
  );
};

// Page Trend Card
const PageTrendCard = ({ page, isExpanded, onToggle }) => {
  const { trends, comparison, actual_health_score } = page;

  // Mini chart data (last 7 points)
  const miniChartData = trends.slice(-7).map(t => ({
    seo: t.seo_score || 0,
    perf: t.performance_score || 0,
  }));

  // Get change indicators
  const seoChange = comparison?.changes?.seo_score || 0;
  const impressionsChange = comparison?.changes?.impressions || 0;
  const clicksChange = comparison?.changes?.clicks || 0;

  // 최신 데이터에서 키워드 목록 추출
  const latestTrend = trends[trends.length - 1];
  const topKeywords = latestTrend?.top_keywords || [];

  // 차트 데이터 준비
  const chartData = trends.map(t => ({
    ...t,
    date: new Date(t.date).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }),
  }));

  return (
    <div className={`page-trend-card ${isExpanded ? 'expanded' : ''}`}>
      <div className="page-card-header" onClick={onToggle}>
        <div className="page-info">
          <span className="page-depth">L{page.depth_level}</span>
          <div className="page-details">
            <span className="page-title">{page.title || page.path}</span>
            <span className="page-url">{page.path}</span>
          </div>
        </div>

        <div className="page-stats">
          {/* Mini sparklines with labels */}
          <div className="mini-charts-group">
            <div className="mini-chart-item" title="Lighthouse SEO">
              <span className="mini-chart-label seo">SEO</span>
              <MiniSparkline data={miniChartData} dataKey="seo" color="#667eea" />
            </div>
            <div className="mini-chart-item" title="Performance">
              <span className="mini-chart-label perf">Perf</span>
              <MiniSparkline data={miniChartData} dataKey="perf" color="#10b981" />
            </div>
          </div>

          {/* Score badges with labels */}
          <div className="score-badges">
            {actual_health_score !== null && (
              <span className="badge health" title="이슈 기반 Health Score">
                <span className="badge-label">Health</span>
                <span className="badge-value">❤️ {actual_health_score}</span>
              </span>
            )}
            {latestTrend?.seo_score && (
              <span className="badge seo" title="Lighthouse SEO">
                <span className="badge-label">SEO</span>
                <span className="badge-value">📊 {latestTrend.seo_score}</span>
              </span>
            )}
            {comparison?.current && (
              <span className="badge traffic" title="노출수">
                <span className="badge-label">노출</span>
                <span className="badge-value">
                  👁️ {(comparison.current.impressions || 0).toLocaleString()}
                  <ChangeIndicator value={impressionsChange} small />
                </span>
              </span>
            )}
          </div>

          <span className={`expand-icon ${isExpanded ? 'rotated' : ''}`}>
            ▼
          </span>
        </div>
      </div>

      {isExpanded && trends.length > 0 && (
        <div className="page-card-content">
          {/* 스코어 트렌드 차트 */}
          <div className="chart-wrapper">
            <h4>📈 스코어 트렌드</h4>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="date" stroke="#9ca3af" fontSize={10} />
                <YAxis domain={[0, 100]} stroke="#9ca3af" fontSize={10} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1f2937',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '12px'
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Line
                  type="monotone"
                  dataKey="seo_score"
                  name="Lighthouse SEO"
                  stroke="#667eea"
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
                <Line
                  type="monotone"
                  dataKey="performance_score"
                  name="Performance"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
                <Line
                  type="monotone"
                  dataKey="health_score"
                  name="Health (SEO+Perf 평균)"
                  stroke="#ef4444"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* 트래픽 트렌드 차트 */}
          <div className="chart-wrapper">
            <h4>📊 트래픽 트렌드</h4>
            <ResponsiveContainer width="100%" height={150}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorImpressions" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#667eea" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#667eea" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorClicks" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="date" stroke="#9ca3af" fontSize={10} />
                <YAxis stroke="#9ca3af" fontSize={10} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1f2937',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '12px'
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Area
                  type="monotone"
                  dataKey="impressions"
                  name="노출수"
                  stroke="#667eea"
                  fill="url(#colorImpressions)"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="clicks"
                  name="클릭수"
                  stroke="#10b981"
                  fill="url(#colorClicks)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* 키워드 목록 */}
          <div className="keywords-section">
            <h4>🔍 노출 키워드</h4>
            {topKeywords.length > 0 ? (
              <div className="keyword-chips">
                {topKeywords.map((kw, index) => (
                  <div key={kw.query} className="keyword-chip" title={`노출: ${kw.impressions}, 클릭: ${kw.clicks}`}>
                    <span className="keyword-rank">{index + 1}</span>
                    <span className="keyword-text">{kw.query}</span>
                    <span className="keyword-stats">
                      👁️{kw.impressions} · 👆{kw.clicks}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="keywords-pending-notice">
                {(comparison?.current?.impressions || 0) > 0 ? (
                  <>
                    <span className="notice-icon">🔒</span>
                    <div className="notice-content">
                      <span className="notice-title">키워드 데이터 수집 중</span>
                      <span className="notice-desc">
                        노출 {comparison?.current?.impressions || 0}회가 있지만, 개별 키워드당 노출이 낮아
                        Google 프라이버시 정책에 의해 아직 표시되지 않습니다.
                        노출이 더 쌓이면 키워드가 나타납니다.
                      </span>
                    </div>
                  </>
                ) : (
                  <>
                    <span className="notice-icon">📊</span>
                    <div className="notice-content">
                      <span className="notice-title">검색 노출 대기 중</span>
                      <span className="notice-desc">
                        아직 Google 검색에서 노출이 발생하지 않았습니다.
                        콘텐츠가 인덱싱되면 키워드 데이터가 표시됩니다.
                      </span>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Page stats detail */}
          <div className="page-stats-detail">
            <div className="stat">
              <span className="label">SEO 시작</span>
              <span className="value">{comparison?.start?.seo_score?.toFixed(0) || '-'}</span>
            </div>
            <div className="stat">
              <span className="label">SEO 현재</span>
              <span className="value">{comparison?.current?.seo_score?.toFixed(0) || '-'}</span>
            </div>
            <div className="stat">
              <span className="label">SEO 변화</span>
              <span className={`value ${seoChange > 0 ? 'positive' : seoChange < 0 ? 'negative' : ''}`}>
                {seoChange > 0 ? '+' : ''}{seoChange.toFixed(1)}
              </span>
            </div>
            <div className="stat">
              <span className="label">노출 변화</span>
              <span className={`value ${impressionsChange > 0 ? 'positive' : impressionsChange < 0 ? 'negative' : ''}`}>
                {impressionsChange > 0 ? '+' : ''}{impressionsChange.toLocaleString()}
              </span>
            </div>
            <div className="stat">
              <span className="label">클릭 변화</span>
              <span className={`value ${clicksChange > 0 ? 'positive' : clicksChange < 0 ? 'negative' : ''}`}>
                {clicksChange > 0 ? '+' : ''}{clicksChange.toLocaleString()}
              </span>
            </div>
            <div className="stat">
              <span className="label">키워드</span>
              <span className="value">{latestTrend?.keywords_count || 0}개</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Keywords Tab
// ============================================================================
const KeywordsTab = ({ data }) => {
  const { keywords, total_keywords } = data;

  if (!keywords || keywords.length === 0) {
    return (
      <div className="empty-state keywords-empty">
        <span className="empty-icon">🔒</span>
        <h3>키워드 데이터 수집 중</h3>
        <p className="empty-main">Google 프라이버시 정책에 의해 키워드가 아직 표시되지 않습니다.</p>
        <div className="empty-details">
          <div className="detail-item">
            <span className="detail-icon">📊</span>
            <span>노출 데이터는 정상 수집 중입니다</span>
          </div>
          <div className="detail-item">
            <span className="detail-icon">🔍</span>
            <span>개별 키워드당 노출이 임계값을 넘으면 표시됩니다</span>
          </div>
          <div className="detail-item">
            <span className="detail-icon">⏳</span>
            <span>보통 페이지당 50+ 노출 후 키워드가 나타납니다</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="keywords-tab">
      <div className="keywords-header">
        <span>총 {total_keywords}개 키워드 중 상위 {keywords.length}개</span>
      </div>

      <div className="keywords-table">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>키워드</th>
              <th>노출수</th>
              <th>클릭수</th>
              <th>CTR</th>
              <th>페이지</th>
            </tr>
          </thead>
          <tbody>
            {keywords.map((kw, index) => (
              <tr key={kw.keyword}>
                <td className="rank">{index + 1}</td>
                <td className="keyword">{kw.keyword}</td>
                <td className="impressions">{kw.impressions.toLocaleString()}</td>
                <td className="clicks">{kw.clicks.toLocaleString()}</td>
                <td className="ctr">{kw.ctr.toFixed(2)}%</td>
                <td className="pages">
                  <span className="page-count">{kw.page_count}개</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ============================================================================
// Helper Components
// ============================================================================

// Score Card
const ScoreCard = ({ title, value, change, icon, color, subtitle, unit = '점' }) => (
  <div className="score-card" style={{ borderColor: color }}>
    <div className="card-icon" style={{ backgroundColor: `${color}20` }}>
      {icon}
    </div>
    <div className="card-content">
      <span className="card-title">{title}</span>
      <span className="card-value" style={{ color }}>
        {value?.toFixed?.(1) || value || 0}{unit !== '점' ? ` ${unit}` : ''}
        {change !== undefined && <ChangeIndicator value={change} />}
      </span>
      {subtitle && <span className="card-subtitle">{subtitle}</span>}
    </div>
  </div>
);

// Change Indicator
const ChangeIndicator = ({ value, small = false }) => {
  if (value === undefined || value === null || value === 0) return null;

  const isPositive = value > 0;
  const className = `change-indicator ${isPositive ? 'positive' : 'negative'} ${small ? 'small' : ''}`;

  return (
    <span className={className}>
      {isPositive ? '▲' : '▼'} {Math.abs(value).toLocaleString()}
    </span>
  );
};

// Comparison Card
const ComparisonCard = ({ label, start, current, change, unit = '' }) => (
  <div className="comparison-card">
    <span className="comp-label">{label}</span>
    <div className="comp-values">
      <div className="comp-start">
        <span className="comp-period">시작</span>
        <span className="comp-value">{start?.toLocaleString() || 0}{unit}</span>
      </div>
      <span className="comp-arrow">→</span>
      <div className="comp-current">
        <span className="comp-period">현재</span>
        <span className="comp-value">{current?.toLocaleString() || 0}{unit}</span>
      </div>
      <div className={`comp-change ${change > 0 ? 'positive' : change < 0 ? 'negative' : ''}`}>
        {change > 0 ? '+' : ''}{change?.toLocaleString() || 0}
      </div>
    </div>
  </div>
);

// Mini Sparkline (simple SVG)
const MiniSparkline = ({ data, dataKey, color }) => {
  if (!data || data.length < 2) return null;

  const values = data.map(d => d[dataKey] || 0);
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;

  const width = 60;
  const height = 24;
  const padding = 2;

  const points = values.map((v, i) => {
    const x = padding + (i / (values.length - 1)) * (width - padding * 2);
    const y = height - padding - ((v - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width={width} height={height} className="mini-sparkline">
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="2"
        points={points}
      />
    </svg>
  );
};

export default AnalyticsDashboard;
