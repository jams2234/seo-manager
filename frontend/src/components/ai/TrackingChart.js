/**
 * TrackingChart
 * AI 제안 추적 데이터 시각화 차트
 */
import React, { useState, useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts';
import './TrackingChart.css';

const METRICS = [
  { key: 'impressions', label: '노출수', color: '#667eea', unit: '' },
  { key: 'clicks', label: '클릭수', color: '#10b981', unit: '' },
  { key: 'ctr', label: 'CTR', color: '#f59e0b', unit: '%' },
  { key: 'position', label: '순위', color: '#ef4444', unit: '', inverted: true },
  { key: 'seo_score', label: 'SEO 점수', color: '#8b5cf6', unit: '' },
];

const TrackingChart = ({
  chartData,
  baseline,
  snapshots,
  selectedMetric: externalMetric,
  onMetricChange,
  showSummary = true,
  height = 300,
}) => {
  const [internalMetric, setInternalMetric] = useState('impressions');
  const selectedMetric = externalMetric || internalMetric;

  const handleMetricChange = (metric) => {
    setInternalMetric(metric);
    if (onMetricChange) {
      onMetricChange(metric);
    }
  };

  // 차트 데이터 변환
  const formattedData = useMemo(() => {
    if (!chartData || !chartData.labels) return [];

    return chartData.labels.map((label, idx) => {
      const date = new Date(label);
      return {
        date: label,
        dateFormatted: `${date.getMonth() + 1}/${date.getDate()}`,
        impressions: chartData.impressions?.[idx] || 0,
        clicks: chartData.clicks?.[idx] || 0,
        ctr: chartData.ctr?.[idx] || 0,
        position: chartData.position?.[idx] || 0,
        seo_score: chartData.seo_score?.[idx] || 0,
        health_score: chartData.health_score?.[idx] || 0,
      };
    });
  }, [chartData]);

  // 선택된 메트릭 정보
  const metricInfo = METRICS.find(m => m.key === selectedMetric) || METRICS[0];

  // 변화량 계산
  const changes = useMemo(() => {
    if (!snapshots || snapshots.length === 0) return null;

    const latest = snapshots[snapshots.length - 1];
    const baselineValue = baseline?.[selectedMetric] || 0;
    const currentValue = latest?.[selectedMetric] || 0;

    const change = currentValue - baselineValue;
    let changePercent = 0;
    if (baselineValue !== 0) {
      changePercent = ((change / Math.abs(baselineValue)) * 100).toFixed(1);
    }

    // 순위는 낮을수록 좋음
    const isPositive = metricInfo.inverted ? change < 0 : change > 0;

    return {
      baseline: baselineValue,
      current: currentValue,
      change,
      changePercent,
      isPositive,
      trackingDays: snapshots.length,
    };
  }, [snapshots, baseline, selectedMetric, metricInfo]);

  // 커스텀 툴팁
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="tracking-chart-tooltip">
          <div className="tooltip-date">{label}</div>
          <div className="tooltip-value">
            {metricInfo.label}: {data[selectedMetric]?.toLocaleString()}{metricInfo.unit}
          </div>
          {baseline?.[selectedMetric] && (
            <div className="tooltip-baseline">
              기준: {baseline[selectedMetric]?.toLocaleString()}{metricInfo.unit}
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  if (!formattedData.length) {
    return (
      <div className="tracking-chart-empty">
        <div className="empty-icon">📊</div>
        <div className="empty-text">추적 데이터가 없습니다</div>
        <div className="empty-subtext">추적이 시작되면 일일 데이터가 여기에 표시됩니다.</div>
      </div>
    );
  }

  return (
    <div className="tracking-chart">
      {/* 메트릭 선택 탭 */}
      <div className="metric-tabs">
        {METRICS.map(metric => (
          <button
            key={metric.key}
            className={`metric-tab ${selectedMetric === metric.key ? 'active' : ''}`}
            onClick={() => handleMetricChange(metric.key)}
            style={{ '--tab-color': metric.color }}
          >
            {metric.label}
          </button>
        ))}
      </div>

      {/* 요약 카드 */}
      {showSummary && changes && (
        <div className="tracking-summary">
          <div className="summary-item">
            <span className="summary-label">추적 일수</span>
            <span className="summary-value">{changes.trackingDays}일</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">기준값</span>
            <span className="summary-value">
              {changes.baseline?.toLocaleString()}{metricInfo.unit}
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">현재값</span>
            <span className="summary-value">
              {changes.current?.toLocaleString()}{metricInfo.unit}
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">변화</span>
            <span className={`summary-value change ${changes.isPositive ? 'positive' : 'negative'}`}>
              {changes.isPositive ? '+' : ''}{changes.change?.toLocaleString()}{metricInfo.unit}
              <span className="change-percent">
                ({changes.isPositive ? '+' : ''}{changes.changePercent}%)
              </span>
            </span>
          </div>
        </div>
      )}

      {/* 차트 */}
      <div className="chart-container" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={formattedData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
            <XAxis
              dataKey="dateFormatted"
              stroke="#9ca3af"
              fontSize={12}
              tickLine={false}
            />
            <YAxis
              stroke="#9ca3af"
              fontSize={12}
              tickLine={false}
              domain={metricInfo.inverted ? ['auto', 'auto'] : [0, 'auto']}
              reversed={metricInfo.inverted}
              tickFormatter={(value) => value.toLocaleString()}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />

            {/* 기준선 */}
            {baseline?.[selectedMetric] && (
              <ReferenceLine
                y={baseline[selectedMetric]}
                stroke="#6b7280"
                strokeDasharray="5 5"
                label={{
                  value: '기준',
                  position: 'insideTopRight',
                  fill: '#9ca3af',
                  fontSize: 11,
                }}
              />
            )}

            {/* 데이터 라인 */}
            <Line
              type="monotone"
              dataKey={selectedMetric}
              stroke={metricInfo.color}
              strokeWidth={2}
              dot={{ fill: metricInfo.color, strokeWidth: 0, r: 3 }}
              activeDot={{ r: 6, stroke: metricInfo.color, strokeWidth: 2, fill: '#fff' }}
              name={metricInfo.label}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default TrackingChart;
