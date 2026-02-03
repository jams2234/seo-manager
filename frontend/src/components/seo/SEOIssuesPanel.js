import React, { useState, useEffect } from 'react';
import useSEOAnalysis from '../../hooks/useSEOAnalysis';
import useIssueCategories from '../../hooks/useIssueCategories';
import GitDeploymentSettings from './GitDeploymentSettings';
import FixHistoryModal from './FixHistoryModal';
import CodePreviewModal from './CodePreviewModal';
import './SEOIssuesPanel.css';

const SEOIssuesPanel = ({ pageId, domainId, onClose }) => {
  const {
    loading,
    error,
    issues,
    analysisReport,
    analyzePageSEO,
    fetchIssues,
    previewFix,
    autoFixIssue,
    bulkAutoFix,
    revertIssue,
    updateFixValue,
    deployPendingFixes,
    fetchLatestReport,
    fetchGitConfig,
    clearError,
  } = useSEOAnalysis();

  // Use the centralized issue categories hook
  const {
    openIssues,
    fixedIssues,
    criticalIssues,
    autoFixableIssues,
    deployedIssues,
    dbOnlyIssues,
    verifiedIssues,
    needsAttentionIssues,
    pendingVerificationIssues,
    counts,
    hasAutoFixable,
    allVerified,
  } = useIssueCategories(issues);

  const [analyzingPage, setAnalyzingPage] = useState(false);
  const [showGitSettings, setShowGitSettings] = useState(false);
  const [gitEnabled, setGitEnabled] = useState(false);
  const [deploymentResult, setDeploymentResult] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [deploying, setDeploying] = useState(false);
  const [previousHealthScore, setPreviousHealthScore] = useState(null);
  const [showVerificationPrompt, setShowVerificationPrompt] = useState(false);

  // Code preview modal state
  const [showCodePreview, setShowCodePreview] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewIssueId, setPreviewIssueId] = useState(null);

  useEffect(() => {
    if (pageId) {
      loadData();
    }
    if (domainId) {
      loadGitConfig();
    }
  }, [pageId, domainId]);

  const loadData = async () => {
    try {
      setRefreshing(true);
      await fetchIssues(pageId);
      await fetchLatestReport(pageId);
    } catch (err) {
      console.error('Error loading data:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const loadGitConfig = async () => {
    try {
      const config = await fetchGitConfig(domainId);
      setGitEnabled(config.git_enabled);
    } catch (err) {
      console.error('Error loading Git config:', err);
    }
  };

  const handleAnalyze = async (isVerification = false) => {
    if (!pageId) {
      alert('Error: No page ID provided');
      return;
    }

    try {
      setAnalyzingPage(true);
      clearError();

      // 검증 분석일 경우 이전 점수 저장
      const oldScore = analysisReport?.overall_health_score;
      if (isVerification && oldScore) {
        setPreviousHealthScore(oldScore);
      }

      await analyzePageSEO(pageId, {
        includeContentAnalysis: true,
        verifyMode: isVerification  // 검증 모드 전달
      });

      // 데이터 로드 후 새 리포트 가져오기
      await fetchIssues(pageId);
      const newReport = await fetchLatestReport(pageId);

      // 검증 프롬프트 숨기기
      setShowVerificationPrompt(false);

      if (isVerification && oldScore && newReport?.overall_health_score) {
        // 점수 변화 계산 후 결과 표시
        const newScore = newReport.overall_health_score;
        const scoreDiff = newScore - oldScore;
        const scoreMessage = scoreDiff > 0
          ? `📈 Health Score: ${oldScore} → ${newScore} (+${scoreDiff}점 상승!)`
          : scoreDiff < 0
            ? `📉 Health Score: ${oldScore} → ${newScore} (${scoreDiff}점)`
            : `📊 Health Score: ${newScore}점 (변화 없음)`;
        alert(`SEO 검증 분석 완료!\n\n${scoreMessage}\n\n배포된 수정사항이 실제 웹사이트에 반영되었는지 확인되었습니다.`);
      } else if (isVerification) {
        alert('SEO 검증 분석 완료!\n\n배포된 수정사항이 반영되었는지 확인하세요.');
      } else {
        alert('SEO analysis completed successfully!');
      }
    } catch (err) {
      console.error('SEO analysis error:', err);
      const errorMsg = err.response?.data?.error || err.message || 'Analysis failed';
      alert(`Failed to analyze page: ${errorMsg}`);
    } finally {
      setAnalyzingPage(false);
    }
  };

  // Show code preview before auto-fix
  const handleShowPreview = async (issueId) => {
    setPreviewIssueId(issueId);
    setPreviewLoading(true);
    setShowCodePreview(true);
    setPreviewData(null);

    try {
      const data = await previewFix(issueId);
      setPreviewData(data);
    } catch (err) {
      console.error('Preview failed:', err);
      // Still show modal with error state
    } finally {
      setPreviewLoading(false);
    }
  };

  // Confirm and apply auto-fix after preview (uses AI-generated value from preview)
  const handleConfirmAutoFix = async () => {
    if (!previewIssueId) return;

    setShowCodePreview(false);

    try {
      // Pass the AI-generated suggested value from preview to avoid regenerating
      const options = previewData?.suggested_value
        ? { suggestedValue: previewData.suggested_value }
        : {};

      const result = await autoFixIssue(previewIssueId, options);

      // Refresh data to show updated status
      await loadData();

      // Show success message with AI indicator
      const aiMessage = previewData?.ai_generated
        ? '🤖 AI가 분석한 최적의 수정이 적용되었습니다!\n\n'
        : '';
      alert(`${aiMessage}수정이 적용되었습니다!\n\n💾 데이터베이스에 저장되었습니다.\n수정 완료 섹션의 "🚀 Git에 배포" 버튼으로 웹사이트에 반영할 수 있습니다.`);
    } catch (err) {
      alert('Failed to auto-fix issue: ' + err.message);
    } finally {
      setPreviewIssueId(null);
      setPreviewData(null);
    }
  };

  // Legacy function - now shows preview first
  const handleAutoFix = async (issueId) => {
    handleShowPreview(issueId);
  };

  // Direct auto-fix without preview (for bulk operations)
  const handleDirectAutoFix = async (issueId) => {
    try {
      const result = await autoFixIssue(issueId);

      // Refresh data to show updated status
      await loadData();

      // Show success message with details
      const message = result.message || 'Issue auto-fixed successfully!';
      const details = result.old_value && result.new_value
        ? `\n\n이전 값: ${result.old_value}\n새 값: ${result.new_value}`
        : '';

      alert(message + details + '\n\n💾 데이터베이스에 저장되었습니다.\n수정 완료 섹션의 "🚀 Git에 배포" 버튼으로 웹사이트에 반영할 수 있습니다.');
    } catch (err) {
      alert('Failed to auto-fix issue: ' + err.message);
      console.error('Error auto-fixing issue:', err);
    }
  };

  const handleRevert = async (issueId, deployToGit) => {
    try {
      const result = await revertIssue(issueId, deployToGit);

      // Refresh data to show updated status
      await loadData();

      return result;
    } catch (err) {
      throw err;
    }
  };

  const handleUpdateFixValue = async (issueId, suggestedValue) => {
    try {
      const result = await updateFixValue(issueId, suggestedValue);

      // Refresh data to show updated value
      await loadData();

      return result;
    } catch (err) {
      throw err;
    }
  };

  const handleDeployPending = async () => {
    const pendingIssues = issues.filter(
      issue => (issue.status === 'auto_fixed' || issue.status === 'fixed') && !issue.deployed_to_git
    );

    if (pendingIssues.length === 0) {
      alert('배포할 수정 사항이 없습니다.\n\n모든 수정 사항이 이미 Git에 배포되었거나, 수정된 이슈가 없습니다.');
      return;
    }

    if (!window.confirm(`${pendingIssues.length}개의 수정 사항을 Git에 배포하시겠습니까?\n\n실제 웹사이트에 반영됩니다.`)) {
      return;
    }

    try {
      setDeploying(true);
      setDeploymentResult(null);
      const result = await deployPendingFixes(pageId);

      // 배포 성공 시 데이터 새로고침
      await loadData();

      if (result.deployed_count > 0) {
        // 배포 성공 결과 표시
        const deploymentInfo = result.deployment_results?.[0] || {};
        setDeploymentResult({
          success: true,
          message: `${result.deployed_count}개 수정사항이 Git에 배포되었습니다!`,
          commit_hash: deploymentInfo.commit_hash,
          changes_count: result.deployed_count
        });

        // 현재 Health Score 저장 (재분석 후 비교용)
        if (analysisReport?.overall_health_score) {
          setPreviousHealthScore(analysisReport.overall_health_score);
        }

        // 검증 프롬프트 표시
        setShowVerificationPrompt(true);

        // 10초 후 배포 성공 메시지만 숨김 (검증 프롬프트는 유지)
        setTimeout(() => {
          setDeploymentResult(null);
        }, 10000);
      } else {
        alert('배포할 수 있는 수정사항이 없습니다.\n\nGit 설정을 확인해주세요.');
      }
    } catch (err) {
      setDeploymentResult({
        success: false,
        error: err.message
      });
      console.error('Error deploying pending fixes:', err);
    } finally {
      setDeploying(false);
    }
  };

  const handleBulkAutoFix = async () => {
    const autoFixableIssues = issues.filter(
      issue => issue.auto_fix_available && issue.status === 'open'
    );

    if (autoFixableIssues.length === 0) {
      // Provide contextual error message
      const totalIssues = issues.length;
      const fixedIssues = issues.filter(issue => issue.status === 'auto_fixed' || issue.status === 'fixed');

      if (totalIssues === 0) {
        alert('자동 수정 가능한 이슈가 없습니다.\n\n먼저 "Run SEO Analysis"를 실행하여 SEO 분석을 진행해주세요.');
      } else if (fixedIssues.length === totalIssues) {
        alert('모든 이슈가 이미 수정되었습니다! 🎉\n\n추가로 수정할 이슈가 없습니다.');
      } else {
        alert('현재 열려있는 이슈 중 자동 수정 가능한 항목이 없습니다.\n\n수동으로 수정이 필요한 이슈만 남아있습니다.');
      }
      return;
    }

    if (!window.confirm(`${autoFixableIssues.length}개 이슈를 자동 수정하시겠습니까?\n\n💾 데이터베이스에 저장됩니다.\n수정 완료 섹션의 "🚀 Git에 배포" 버튼으로 웹사이트에 반영할 수 있습니다.`)) {
      return;
    }

    try {
      const result = await bulkAutoFix(
        autoFixableIssues.map(issue => issue.id)
      );

      await loadData();

      const message = result.message || 'Bulk auto-fix completed';
      const summary = `\n\n성공: ${result.fixed_count || 0}\n실패: ${result.failed_count || 0}\n총 ${result.total_requested || 0}개 요청`;

      alert(message + summary + '\n\n💾 데이터베이스에 저장되었습니다.');
    } catch (err) {
      alert('Failed to bulk auto-fix: ' + err.message);
      console.error('Error bulk auto-fixing:', err);
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical':
        return '#ef4444';
      case 'warning':
        return '#f59e0b';
      case 'info':
        return '#3b82f6';
      default:
        return '#6b7280';
    }
  };

  const getHealthScoreColor = (score) => {
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#f59e0b';
    return '#ef4444';
  };

  // Issue categories are now provided by useIssueCategories hook
  const autoFixableCount = counts.autoFixable;

  return (
    <div className="seo-issues-panel">
      <div className="seo-issues-header">
        <h3>SEO Analysis</h3>
        <div className="header-actions">
          {domainId && (
            <button
              className="btn-git-settings"
              onClick={() => setShowGitSettings(true)}
              title="Git 배포 설정"
            >
              ⚙️
            </button>
          )}
          <button className="close-button" onClick={onClose}>×</button>
        </div>
      </div>

      {/* Git Settings Modal */}
      {showGitSettings && domainId && (
        <div className="modal-overlay" onClick={() => setShowGitSettings(false)}>
          <div onClick={(e) => e.stopPropagation()}>
            <GitDeploymentSettings
              domainId={domainId}
              onClose={() => {
                setShowGitSettings(false);
                loadGitConfig();
              }}
            />
          </div>
        </div>
      )}

      {/* Fix History Modal */}
      {selectedIssue && (
        <FixHistoryModal
          issue={issues.find(i => i.id === selectedIssue.id) || selectedIssue}
          onClose={() => setSelectedIssue(null)}
          onRevert={handleRevert}
          onUpdateFixValue={handleUpdateFixValue}
          gitEnabled={gitEnabled}
        />
      )}

      {/* Code Preview Modal */}
      <CodePreviewModal
        isOpen={showCodePreview}
        onClose={() => {
          setShowCodePreview(false);
          setPreviewData(null);
          setPreviewIssueId(null);
        }}
        onConfirm={handleConfirmAutoFix}
        previewData={previewData}
        loading={previewLoading}
      />

      {/* Deployment Result */}
      {deploymentResult && (
        <div className={`deployment-result ${deploymentResult.success ? 'success' : 'error'}`}
          style={{
            position: 'relative',
            animation: 'slideIn 0.3s ease-out'
          }}
        >
          <button
            onClick={() => setDeploymentResult(null)}
            style={{
              position: 'absolute',
              top: '8px',
              right: '8px',
              background: 'transparent',
              border: 'none',
              fontSize: '18px',
              cursor: 'pointer',
              opacity: 0.6,
              color: 'inherit'
            }}
          >
            ×
          </button>
          {deploymentResult.success ? (
            <>
              <div className="deployment-icon">🎉</div>
              <div className="deployment-info">
                <div className="deployment-title">Git 배포 완료!</div>
                <div className="deployment-details">
                  {deploymentResult.commit_hash && (
                    <div>커밋: <code style={{ background: 'rgba(0,0,0,0.1)', padding: '2px 6px', borderRadius: '3px' }}>{deploymentResult.commit_hash.substring(0, 7)}</code></div>
                  )}
                  <div>{deploymentResult.changes_count}개 수정사항이 웹사이트에 반영되었습니다.</div>
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="deployment-icon">❌</div>
              <div className="deployment-info">
                <div className="deployment-title">Git 배포 실패</div>
                <div className="deployment-details">{deploymentResult.error}</div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Health Score Card */}
      {analysisReport && (
        <div className="health-score-card">
          <div className="health-score-main">
            <div
              className={`health-score-circle ${previousHealthScore && analysisReport.overall_health_score > previousHealthScore ? 'score-improved' : ''}`}
              style={{ borderColor: getHealthScoreColor(analysisReport.overall_health_score) }}
            >
              <span className="health-score-value">
                {analysisReport.overall_health_score}
              </span>
            </div>
            <div className="health-score-info">
              <div className="health-score-label">
                Health Score
                {previousHealthScore && previousHealthScore !== analysisReport.overall_health_score && (
                  <span
                    className={`score-change ${analysisReport.overall_health_score > previousHealthScore ? 'positive' : 'negative'}`}
                    style={{
                      marginLeft: '8px',
                      fontSize: '12px',
                      fontWeight: '700',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      background: analysisReport.overall_health_score > previousHealthScore ? '#d1fae5' : '#fee2e2',
                      color: analysisReport.overall_health_score > previousHealthScore ? '#059669' : '#dc2626'
                    }}
                  >
                    {analysisReport.overall_health_score > previousHealthScore ? '📈 +' : '📉 '}
                    {analysisReport.overall_health_score - previousHealthScore}
                  </span>
                )}
              </div>
              <div className="health-score-stats">
                <span className="stat-item critical">
                  {analysisReport.critical_issues_count} Critical
                </span>
                <span className="stat-item warning">
                  {analysisReport.warning_issues_count} Warnings
                </span>
              </div>
            </div>
          </div>
          {analysisReport.auto_fixable_count > 0 && (
            <button
              className="btn-auto-fix-all"
              onClick={handleBulkAutoFix}
              title="모든 이슈를 자동 수정합니다 (DB에 저장, Git 배포는 별도)"
            >
              💾 Auto-fix {analysisReport.auto_fixable_count} issues
            </button>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="seo-actions">
        <button
          className="btn-analyze"
          onClick={() => handleAnalyze(false)}
          disabled={analyzingPage}
        >
          {analyzingPage ? 'Analyzing...' : 'Run SEO Analysis'}
        </button>
      </div>

      {/* Verification Prompt - 배포 후 재분석 유도 */}
      {showVerificationPrompt && (
        <div className="verification-prompt">
          <div className="verification-icon">🔍</div>
          <div className="verification-content">
            <div className="verification-title">배포 완료! SEO 개선을 확인하세요</div>
            <div className="verification-text">
              수정사항이 웹사이트에 반영되었습니다.<br/>
              SEO 재분석으로 개선 효과를 확인해보세요.
            </div>
            <div className="verification-actions">
              <button
                className="btn-verify"
                onClick={() => handleAnalyze(true)}
                disabled={analyzingPage}
              >
                {analyzingPage ? '분석 중...' : '🔄 SEO 재분석하여 개선 확인'}
              </button>
              <button
                className="btn-dismiss"
                onClick={() => setShowVerificationPrompt(false)}
              >
                나중에
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="error-message">
          ❌ {error}
        </div>
      )}

      {/* Debug Info - Remove in production */}
      {!pageId && (
        <div className="error-message">
          ⚠️ Warning: No page ID provided to SEO panel
        </div>
      )}

      {/* Issues List */}
      <div className="issues-container">
        {refreshing && (
          <div className="refreshing-overlay">
            <div className="refreshing-spinner">업데이트 중...</div>
          </div>
        )}
        {loading ? (
          <div className="loading-message">Loading issues...</div>
        ) : openIssues.length === 0 && fixedIssues.length === 0 ? (
          <div className="no-issues-message">
            <div className="no-issues-icon">✓</div>
            <div className="no-issues-text">
              No analysis yet. Click "Run SEO Analysis" to start.
            </div>
          </div>
        ) : openIssues.length === 0 && fixedIssues.length > 0 ? (
          <div className="no-issues-message celebration">
            <div className="no-issues-icon celebration">🎉</div>
            <div className="no-issues-text">
              <strong>모든 이슈가 수정되었습니다!</strong>
              <div style={{ fontSize: '14px', color: '#6b7280', marginTop: '8px' }}>
                {fixedIssues.filter(i => i.deployed_to_git).length}개가 Git에 배포되어 웹사이트에 반영되었습니다.
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Open Issues Section */}
            {openIssues.length > 0 && (
              <>
                <div className="issues-summary">
                  <span>{openIssues.length} open issue{openIssues.length !== 1 ? 's' : ''}</span>
                  {autoFixableCount > 0 && (
                    <span className="auto-fixable-count">
                      {autoFixableCount} auto-fixable
                    </span>
                  )}
                </div>

                {openIssues.map((issue) => (
              <div key={issue.id} className="issue-card">
                <div className="issue-header">
                  <span
                    className="issue-severity"
                    style={{ backgroundColor: getSeverityColor(issue.severity) }}
                  >
                    {issue.severity}
                  </span>
                  {issue.auto_fix_available && (
                    <span className="auto-fix-badge">Auto-fixable</span>
                  )}
                </div>

                <div className="issue-title">{issue.title}</div>
                <div className="issue-message">{issue.message}</div>

                {issue.fix_suggestion && (
                  <div className="issue-suggestion">
                    <strong>Suggestion:</strong> {issue.fix_suggestion}
                  </div>
                )}

                {issue.current_value && (
                  <div className="issue-values">
                    <div className="value-item">
                      <span className="value-label">Current:</span>
                      <span className="value-text">{issue.current_value}</span>
                    </div>
                    {issue.suggested_value && (
                      <div className="value-item">
                        <span className="value-label">Suggested:</span>
                        <span className="value-text suggested">{issue.suggested_value}</span>
                      </div>
                    )}
                  </div>
                )}

                {issue.auto_fix_available && (
                  <button
                    className="btn-auto-fix"
                    onClick={() => handleAutoFix(issue.id)}
                    title="이슈를 자동 수정합니다 (DB에 저장, Git 배포는 별도)"
                  >
                    💾 Auto-fix
                  </button>
                )}
              </div>
            ))}
              </>
            )}

            {/* Fixed Issues Section */}
            {fixedIssues.length > 0 && (
              <>
                      <div className="fixed-issues-header" style={{
                        marginTop: '20px',
                        padding: '12px',
                        backgroundColor: '#f0fdf4',
                        borderLeft: '4px solid #10b981',
                        borderRadius: '4px'
                      }}>
                        <div style={{ fontWeight: 'bold', color: '#059669', marginBottom: '8px' }}>
                          ✅ 수정 완료 ({fixedIssues.length}개)
                        </div>
                        <div style={{ fontSize: '13px', color: '#065f46', lineHeight: '1.5', marginBottom: (dbOnlyIssues.length > 0 || pendingVerificationIssues.length > 0) && gitEnabled ? '12px' : '0' }}>
                          {verifiedIssues.length > 0 && (
                            <div>✅ 검증 완료: {verifiedIssues.length}개 (웹사이트에 반영 확인됨)</div>
                          )}
                          {needsAttentionIssues.length > 0 && (
                            <div style={{ color: '#b45309', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                              <span>⚠️ 반영 확인 필요: {needsAttentionIssues.length}개 (재배포 또는 캐시 대기)</span>
                              <button
                                onClick={() => handleAnalyze(true)}
                                disabled={analyzingPage}
                                style={{
                                  padding: '4px 10px',
                                  background: '#f59e0b',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '4px',
                                  fontSize: '12px',
                                  fontWeight: '600',
                                  cursor: analyzingPage ? 'not-allowed' : 'pointer',
                                  opacity: analyzingPage ? 0.7 : 1
                                }}
                                title="CDN 캐시 갱신 후 다시 검증하세요"
                              >
                                {analyzingPage ? '검증 중...' : '🔄 재검증'}
                              </button>
                            </div>
                          )}
                          {pendingVerificationIssues.length > 0 && (
                            <div style={{ color: '#1e40af', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                              <span>🔵 검증 대기: {pendingVerificationIssues.length}개 (SEO 재분석으로 확인)</span>
                              <button
                                onClick={() => handleAnalyze(true)}
                                disabled={analyzingPage}
                                style={{
                                  padding: '4px 10px',
                                  background: '#3b82f6',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '4px',
                                  fontSize: '12px',
                                  fontWeight: '600',
                                  cursor: analyzingPage ? 'not-allowed' : 'pointer',
                                  opacity: analyzingPage ? 0.7 : 1
                                }}
                                title="실제 웹사이트에서 수정 반영 여부 확인"
                              >
                                {analyzingPage ? '검증 중...' : '🔄 검증하기'}
                              </button>
                            </div>
                          )}
                          {dbOnlyIssues.length > 0 && (
                            <div>⚠️ DB만 수정됨: {dbOnlyIssues.length}개 (웹사이트 미반영)</div>
                          )}
                          {dbOnlyIssues.length > 0 && !gitEnabled && (
                            <div style={{ marginTop: '4px' }}>
                              💡 Git 배포를 활성화하면 웹사이트에 자동 반영할 수 있습니다.
                            </div>
                          )}
                        </div>
                        {dbOnlyIssues.length > 0 && gitEnabled && (
                          <button
                            className="btn-deploy-pending"
                            onClick={handleDeployPending}
                            disabled={deploying}
                            style={{
                              width: '100%',
                              padding: '10px',
                              background: deploying
                                ? '#9ca3af'
                                : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                              color: 'white',
                              border: 'none',
                              borderRadius: '6px',
                              fontWeight: '600',
                              fontSize: '14px',
                              cursor: deploying ? 'not-allowed' : 'pointer',
                              transition: 'transform 0.2s'
                            }}
                            onMouseOver={(e) => {
                              if (!deploying) {
                                e.currentTarget.style.transform = 'translateY(-1px)';
                                e.currentTarget.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
                              }
                            }}
                            onMouseOut={(e) => {
                              e.currentTarget.style.transform = 'translateY(0)';
                              e.currentTarget.style.boxShadow = 'none';
                            }}
                          >
                            {deploying ? (
                              <>⏳ 배포 중...</>
                            ) : (
                              <>🚀 Git에 배포 ({dbOnlyIssues.length}개 대기 중)</>
                            )}
                          </button>
                        )}
                        {/* 모든 이슈가 검증 완료된 경우 */}
                        {dbOnlyIssues.length === 0 && verifiedIssues.length === fixedIssues.length && verifiedIssues.length > 0 && (
                          <div style={{
                            marginTop: '8px',
                            padding: '12px',
                            background: 'linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%)',
                            borderRadius: '6px',
                            textAlign: 'center',
                            color: '#065f46',
                            border: '1px solid #6ee7b7'
                          }}>
                            <div style={{ fontWeight: '700', fontSize: '15px' }}>
                              🎉 모든 수정사항이 검증 완료되었습니다!
                            </div>
                            <div style={{ fontSize: '13px', marginTop: '4px', opacity: 0.8 }}>
                              실제 웹사이트에 정상 반영되었습니다.
                            </div>
                          </div>
                        )}
                        {/* 배포는 됐지만 검증 대기 중인 경우 */}
                        {dbOnlyIssues.length === 0 && pendingVerificationIssues.length > 0 && gitEnabled && (
                          <div style={{
                            marginTop: '8px',
                            padding: '12px',
                            background: 'linear-gradient(135deg, #dbeafe 0%, #e0e7ff 100%)',
                            borderRadius: '6px',
                            textAlign: 'center',
                            color: '#1e40af',
                            border: '1px solid #93c5fd'
                          }}>
                            <div style={{ fontWeight: '600', fontSize: '14px', marginBottom: '8px' }}>
                              🔵 모든 수정사항이 Git에 배포되었습니다!
                            </div>
                            <div style={{ fontSize: '13px', marginBottom: '8px', opacity: 0.9 }}>
                              SEO 재분석으로 실제 반영 여부를 확인하세요.
                            </div>
                            <button
                              onClick={() => handleAnalyze(true)}
                              disabled={analyzingPage}
                              style={{
                                padding: '8px 16px',
                                background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '6px',
                                fontWeight: '600',
                                fontSize: '13px',
                                cursor: analyzingPage ? 'not-allowed' : 'pointer',
                                opacity: analyzingPage ? 0.7 : 1,
                                transition: 'all 0.2s'
                              }}
                            >
                              {analyzingPage ? '분석 중...' : '🔄 SEO 재분석하여 검증하기'}
                            </button>
                          </div>
                        )}
                      </div>

                      {fixedIssues.map((issue) => (
                        <div key={issue.id} className="issue-card fixed-issue">
                          <div className="issue-header">
                            <span
                              className="issue-severity"
                              style={{ backgroundColor: '#10b981' }}
                            >
                              {issue.status === 'auto_fixed' ? 'AUTO-FIXED' : 'FIXED'}
                            </span>
                            {/* 검증 상태에 따른 배지 표시 */}
                            {issue.verification_status === 'verified' ? (
                              <span className="deployment-badge verified" title={`검증 완료: ${issue.verified_at ? new Date(issue.verified_at).toLocaleString('ko-KR') : 'N/A'}`}>
                                ✅ 검증 완료
                              </span>
                            ) : issue.verification_status === 'needs_attention' ? (
                              <span className="deployment-badge needs-attention" title="실제 웹사이트에서 아직 문제가 감지됩니다. CDN 캐시 또는 배포 지연일 수 있습니다.">
                                ⚠️ 반영 확인 필요
                              </span>
                            ) : issue.deployed_to_git ? (
                              <span className="deployment-badge pending-verification" title={`Git 배포 완료. SEO 재분석으로 검증하세요.\nCommit: ${issue.deployment_commit_hash || 'N/A'}`}>
                                🔵 검증 대기
                              </span>
                            ) : (
                              <span className="deployment-badge db-only" title="데이터베이스에만 수정됨. 실제 웹사이트에는 아직 반영되지 않았습니다.">
                                ⚠️ DB만 수정됨
                              </span>
                            )}
                          </div>

                          <div className="issue-title">{issue.title}</div>
                          <div className="issue-message">{issue.message}</div>

                          {issue.current_value && (
                            <div className="issue-values">
                              <div className="value-item">
                                <span className="value-label">이전:</span>
                                <span className="value-text">{issue.current_value}</span>
                              </div>
                              {issue.suggested_value && (
                                <div className="value-item">
                                  <span className="value-label">수정됨:</span>
                                  <span className="value-text suggested">{issue.suggested_value}</span>
                                </div>
                              )}
                            </div>
                          )}

                          {issue.deployed_to_git && issue.deployment_commit_hash && (
                            <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '8px' }}>
                              <strong>Commit:</strong> {issue.deployment_commit_hash.substring(0, 7)}
                              {' | '}
                              <strong>배포일:</strong> {new Date(issue.deployed_at).toLocaleString('ko-KR')}
                            </div>
                          )}

                          <button
                            className="btn-view-details"
                            onClick={() => setSelectedIssue(issue)}
                            style={{
                              width: '100%',
                              padding: '8px',
                              marginTop: '12px',
                              background: 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)',
                              color: 'white',
                              border: 'none',
                              borderRadius: '6px',
                              fontWeight: '600',
                              fontSize: '13px',
                              cursor: 'pointer',
                              transition: 'transform 0.2s'
                            }}
                            onMouseOver={(e) => {
                              e.currentTarget.style.transform = 'translateY(-1px)';
                              e.currentTarget.style.boxShadow = '0 2px 8px rgba(107, 114, 128, 0.3)';
                            }}
                            onMouseOut={(e) => {
                              e.currentTarget.style.transform = 'translateY(0)';
                              e.currentTarget.style.boxShadow = 'none';
                            }}
                          >
                            📋 상세보기 & 되돌리기
                          </button>
                        </div>
                      ))}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default SEOIssuesPanel;
