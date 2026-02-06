/**
 * SEO Issues Panel - Main Container Component
 * Orchestrates SEO analysis and issue management
 */
import React, { useState, useEffect } from 'react';
import useSEOAnalysis from '../../hooks/useSEOAnalysis';
import useIssueCategories from '../../hooks/useIssueCategories';
import { useToast } from '../../contexts/ToastContext';
import GitDeploymentSettings from './GitDeploymentSettings';
import FixHistoryModal from './FixHistoryModal';
import CodePreviewModal from './CodePreviewModal';
import HealthScoreCard from './HealthScoreCard';
import DeploymentResultCard from './DeploymentResultCard';
import VerificationPrompt from './VerificationPrompt';
import IssueCard from './IssueCard';
import PageAITrackingSection from './PageAITrackingSection';
import { ImpactReportModal } from '../ai';
import './SEOIssuesPanel.css';

const SEOIssuesPanel = ({ pageId, domainId, onClose }) => {
  const toast = useToast();

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

  const {
    openIssues,
    fixedIssues,
    dbOnlyIssues,
    verifiedIssues,
    needsAttentionIssues,
    pendingVerificationIssues,
    counts,
  } = useIssueCategories(issues);

  // UI State
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

  // Impact report modal state
  const [impactReportSuggestionId, setImpactReportSuggestionId] = useState(null);

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
      toast.error('페이지 ID가 없습니다');
      return;
    }

    try {
      setAnalyzingPage(true);
      clearError();

      const oldScore = analysisReport?.overall_health_score;
      if (isVerification && oldScore) {
        setPreviousHealthScore(oldScore);
      }

      await analyzePageSEO(pageId, {
        includeContentAnalysis: true,
        verifyMode: isVerification
      });

      await fetchIssues(pageId);
      const newReport = await fetchLatestReport(pageId);

      setShowVerificationPrompt(false);

      if (isVerification && oldScore && newReport?.overall_health_score) {
        const newScore = newReport.overall_health_score;
        const scoreDiff = newScore - oldScore;
        const scoreMessage = scoreDiff > 0
          ? `Health Score: ${oldScore} → ${newScore} (+${scoreDiff})`
          : scoreDiff < 0
            ? `Health Score: ${oldScore} → ${newScore} (${scoreDiff})`
            : `Health Score: ${newScore} (변화 없음)`;

        toast.success(`SEO 검증 완료!\n\n${scoreMessage}`, {
          title: '검증 완료',
          duration: 8000
        });
      } else if (isVerification) {
        toast.success('SEO 검증 분석이 완료되었습니다!', { title: '검증 완료' });
      } else {
        toast.success('SEO 분석이 완료되었습니다!', { title: '분석 완료' });
      }
    } catch (err) {
      console.error('SEO analysis error:', err);
      const errorMsg = err.response?.data?.error || err.message || '분석 실패';
      toast.error(`페이지 분석 실패: ${errorMsg}`);
    } finally {
      setAnalyzingPage(false);
    }
  };

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
      toast.error('미리보기 로드 실패');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleConfirmAutoFix = async () => {
    if (!previewIssueId) return;

    setShowCodePreview(false);

    try {
      const options = previewData?.suggested_value
        ? { suggestedValue: previewData.suggested_value }
        : {};

      await autoFixIssue(previewIssueId, options);
      await loadData();

      const aiMessage = previewData?.ai_generated
        ? 'AI 최적화 수정 적용됨!'
        : '수정이 적용되었습니다!';

      toast.success(`${aiMessage}\n\n데이터베이스에 저장됨. Git 배포 시 웹사이트에 반영됩니다.`, {
        title: '오토픽스 적용',
        duration: 6000
      });
    } catch (err) {
      toast.error('오토픽스 실패: ' + err.message);
    } finally {
      setPreviewIssueId(null);
      setPreviewData(null);
    }
  };

  const handleAutoFix = async (issueId) => {
    handleShowPreview(issueId);
  };

  const handleRevert = async (issueId, deployToGit) => {
    try {
      const result = await revertIssue(issueId, deployToGit);
      await loadData();
      return result;
    } catch (err) {
      throw err;
    }
  };

  const handleUpdateFixValue = async (issueId, suggestedValue) => {
    try {
      const result = await updateFixValue(issueId, suggestedValue);
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
      toast.warning('배포할 변경사항이 없습니다.\n\n모든 변경사항이 이미 Git에 배포되었습니다.');
      return;
    }

    if (!window.confirm(`${pendingIssues.length}개 변경사항을 Git에 배포하시겠습니까?\n\n실제 웹사이트가 업데이트됩니다.`)) {
      return;
    }

    try {
      setDeploying(true);
      setDeploymentResult(null);
      const result = await deployPendingFixes(pageId);

      await loadData();

      if (result.deployed_count > 0) {
        const deploymentInfo = result.deployment_results?.[0] || {};
        setDeploymentResult({
          success: true,
          message: `${result.deployed_count}개 변경사항이 Git에 배포되었습니다!`,
          commit_hash: deploymentInfo.commit_hash,
          changes_count: result.deployed_count
        });

        if (analysisReport?.overall_health_score) {
          setPreviousHealthScore(analysisReport.overall_health_score);
        }

        setShowVerificationPrompt(true);

        setTimeout(() => {
          setDeploymentResult(null);
        }, 10000);
      } else {
        toast.warning('배포할 수 없습니다.\n\nGit 설정을 확인해주세요.');
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
      const totalIssues = issues.length;
      const fixedCount = issues.filter(issue => issue.status === 'auto_fixed' || issue.status === 'fixed').length;

      if (totalIssues === 0) {
        toast.info('자동 수정 가능한 이슈가 없습니다.\n\n먼저 "SEO 분석"을 실행하세요.');
      } else if (fixedCount === totalIssues) {
        toast.success('모든 이슈가 수정되었습니다!', { title: '완료' });
      } else {
        toast.info('자동 수정 가능한 이슈가 없습니다.\n\n나머지 이슈는 수동 수정이 필요합니다.');
      }
      return;
    }

    if (!window.confirm(`${autoFixableIssues.length}개 이슈를 자동 수정하시겠습니까?\n\n변경사항은 데이터베이스에 저장됩니다. Git 배포 시 웹사이트에 반영됩니다.`)) {
      return;
    }

    try {
      const result = await bulkAutoFix(
        autoFixableIssues.map(issue => issue.id)
      );

      await loadData();

      const summary = `성공: ${result.fixed_count || 0}\n실패: ${result.failed_count || 0}`;
      toast.success(`일괄 오토픽스 완료!\n\n${summary}`, {
        title: '일괄 수정 완료',
        duration: 6000
      });
    } catch (err) {
      toast.error('일괄 오토픽스 실패: ' + err.message);
      console.error('Error bulk auto-fixing:', err);
    }
  };

  const autoFixableCount = counts.autoFixable;

  return (
    <div className="seo-issues-panel">
      <div className="seo-issues-header">
        <h3>SEO 분석</h3>
        <div className="header-actions">
          {domainId && (
            <button
              className="btn-git-settings"
              onClick={() => setShowGitSettings(true)}
              title="Git 배포 설정"
            >
              <span role="img" aria-label="settings">⚙️</span>
            </button>
          )}
          <button className="close-button" onClick={onClose}>&times;</button>
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
      <DeploymentResultCard
        result={deploymentResult}
        onDismiss={() => setDeploymentResult(null)}
      />

      {/* Health Score Card */}
      {analysisReport && (
        <HealthScoreCard
          score={analysisReport.overall_health_score}
          previousScore={previousHealthScore}
          criticalCount={analysisReport.critical_issues_count}
          warningCount={analysisReport.warning_issues_count}
          autoFixableCount={analysisReport.auto_fixable_count}
          onBulkAutoFix={handleBulkAutoFix}
        />
      )}

      {/* AI Tracking Section */}
      {pageId && (
        <PageAITrackingSection
          pageId={pageId}
          domainId={domainId}
          onOpenImpactReport={(suggestionId) => setImpactReportSuggestionId(suggestionId)}
        />
      )}

      {/* Impact Report Modal */}
      {impactReportSuggestionId && (
        <ImpactReportModal
          suggestionId={impactReportSuggestionId}
          onClose={() => setImpactReportSuggestionId(null)}
        />
      )}

      {/* Action Buttons */}
      <div className="seo-actions">
        <button
          className="btn-analyze"
          onClick={() => handleAnalyze(false)}
          disabled={analyzingPage}
        >
          {analyzingPage ? '분석 중...' : 'SEO 분석 실행'}
        </button>
      </div>

      {/* Verification Prompt */}
      {showVerificationPrompt && (
        <VerificationPrompt
          onVerify={() => handleAnalyze(true)}
          onDismiss={() => setShowVerificationPrompt(false)}
          analyzing={analyzingPage}
        />
      )}

      {/* Error Message */}
      {error && (
        <div className="error-message">
          <span role="img" aria-label="error">❌</span> {error}
        </div>
      )}

      {/* Debug Info */}
      {!pageId && (
        <div className="error-message">
          <span role="img" aria-label="warning">⚠️</span> 경고: SEO 패널에 페이지 ID가 제공되지 않았습니다
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
          <div className="loading-message">이슈 로딩 중...</div>
        ) : openIssues.length === 0 && fixedIssues.length === 0 ? (
          <div className="no-issues-message">
            <div className="no-issues-icon">✓</div>
            <div className="no-issues-text">
              아직 분석이 없습니다. "SEO 분석 실행"을 클릭하세요.
            </div>
          </div>
        ) : openIssues.length === 0 && fixedIssues.length > 0 ? (
          <div className="no-issues-message celebration">
            <div className="no-issues-icon celebration">
              <span role="img" aria-label="celebration">🎉</span>
            </div>
            <div className="no-issues-text">
              <strong>모든 이슈가 수정되었습니다!</strong>
              <div className="no-issues-subtext">
                {fixedIssues.filter(i => i.deployed_to_git).length}개 Git 배포 완료.
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Open Issues Section */}
            {openIssues.length > 0 && (
              <>
                <div className="issues-summary">
                  <span>{openIssues.length}개 미해결 이슈</span>
                  {autoFixableCount > 0 && (
                    <span className="auto-fixable-count">
                      {autoFixableCount}개 자동 수정 가능
                    </span>
                  )}
                </div>

                {openIssues.map((issue) => (
                  <IssueCard
                    key={issue.id}
                    issue={issue}
                    variant="open"
                    onAutoFix={handleAutoFix}
                  />
                ))}
              </>
            )}

            {/* Fixed Issues Section */}
            {fixedIssues.length > 0 && (
              <>
                <div className="fixed-issues-header">
                  <div className="fixed-issues-title">
                    <span role="img" aria-label="check">✅</span> 수정 완료 ({fixedIssues.length})
                  </div>

                  <div className="fixed-issues-stats">
                    {verifiedIssues.length > 0 && (
                      <div className="stat-verified">
                        <span role="img" aria-label="verified">✅</span> 검증됨: {verifiedIssues.length}
                      </div>
                    )}

                    {needsAttentionIssues.length > 0 && (
                      <div className="stat-needs-attention">
                        <span>
                          <span role="img" aria-label="warning">⚠️</span> 주의 필요: {needsAttentionIssues.length}
                        </span>
                        <button
                          onClick={() => handleAnalyze(true)}
                          disabled={analyzingPage}
                          className="btn-inline-action warning"
                        >
                          {analyzingPage ? '검증 중...' : '재검증'}
                        </button>
                      </div>
                    )}

                    {pendingVerificationIssues.length > 0 && (
                      <div className="stat-pending">
                        <span>
                          <span role="img" aria-label="pending">🔵</span> 검증 대기: {pendingVerificationIssues.length}
                        </span>
                        <button
                          onClick={() => handleAnalyze(true)}
                          disabled={analyzingPage}
                          className="btn-inline-action info"
                        >
                          {analyzingPage ? '검증 중...' : '검증'}
                        </button>
                      </div>
                    )}

                    {dbOnlyIssues.length > 0 && (
                      <>
                        <div className="stat-db-only">
                          <span role="img" aria-label="db">⚠️</span> DB만 수정: {dbOnlyIssues.length} (미배포)
                        </div>
                        {!gitEnabled && (
                          <div className="stat-tip">
                            <span role="img" aria-label="tip">💡</span> Git 배포를 활성화하면 자동 배포됩니다.
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {dbOnlyIssues.length > 0 && gitEnabled && (
                    <button
                      className="btn-deploy-pending"
                      onClick={handleDeployPending}
                      disabled={deploying}
                    >
                      {deploying ? (
                        <><span role="img" aria-label="loading">⏳</span> 배포 중...</>
                      ) : (
                        <><span role="img" aria-label="rocket">🚀</span> Git 배포 ({dbOnlyIssues.length}개 대기)</>
                      )}
                    </button>
                  )}

                  {/* All verified celebration */}
                  {dbOnlyIssues.length === 0 && verifiedIssues.length === fixedIssues.length && verifiedIssues.length > 0 && (
                    <div className="all-verified-message">
                      <div className="message-title">
                        <span role="img" aria-label="celebration">🎉</span> 모든 변경사항 검증 완료!
                      </div>
                      <div className="message-subtitle">
                        웹사이트에 성공적으로 반영되었습니다.
                      </div>
                    </div>
                  )}

                  {/* All deployed, pending verification */}
                  {dbOnlyIssues.length === 0 && pendingVerificationIssues.length > 0 && gitEnabled && (
                    <div className="all-deployed-message">
                      <div className="message-title">
                        <span role="img" aria-label="deployed">🔵</span> 모든 변경사항이 Git에 배포되었습니다!
                      </div>
                      <div className="message-subtitle">
                        SEO 재분석으로 변경사항을 검증하세요.
                      </div>
                      <button
                        onClick={() => handleAnalyze(true)}
                        disabled={analyzingPage}
                        className="btn-verify-full"
                      >
                        {analyzingPage ? '분석 중...' : '재분석 및 검증'}
                      </button>
                    </div>
                  )}
                </div>

                {fixedIssues.map((issue) => (
                  <IssueCard
                    key={issue.id}
                    issue={issue}
                    variant="fixed"
                    onViewDetails={() => setSelectedIssue(issue)}
                  />
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
