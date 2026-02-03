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
      toast.error('No page ID provided');
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
            : `Health Score: ${newScore} (no change)`;

        toast.success(`SEO verification complete!\n\n${scoreMessage}`, {
          title: 'Verification Complete',
          duration: 8000
        });
      } else if (isVerification) {
        toast.success('SEO verification analysis complete!', { title: 'Verification Complete' });
      } else {
        toast.success('SEO analysis completed successfully!', { title: 'Analysis Complete' });
      }
    } catch (err) {
      console.error('SEO analysis error:', err);
      const errorMsg = err.response?.data?.error || err.message || 'Analysis failed';
      toast.error(`Failed to analyze page: ${errorMsg}`);
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
      toast.error('Failed to load preview');
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
        ? 'AI-optimized fix applied!'
        : 'Fix applied successfully!';

      toast.success(`${aiMessage}\n\nSaved to database. Use "Deploy to Git" to update the website.`, {
        title: 'Auto-fix Applied',
        duration: 6000
      });
    } catch (err) {
      toast.error('Failed to auto-fix issue: ' + err.message);
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
      toast.warning('No changes to deploy.\n\nAll changes have already been deployed to Git.');
      return;
    }

    if (!window.confirm(`Deploy ${pendingIssues.length} changes to Git?\n\nThis will update the actual website.`)) {
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
          message: `${result.deployed_count} changes deployed to Git!`,
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
        toast.warning('No changes could be deployed.\n\nPlease check Git settings.');
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
        toast.info('No auto-fixable issues found.\n\nRun "SEO Analysis" first to detect issues.');
      } else if (fixedCount === totalIssues) {
        toast.success('All issues have been fixed!', { title: 'Complete' });
      } else {
        toast.info('No auto-fixable issues remaining.\n\nRemaining issues require manual attention.');
      }
      return;
    }

    if (!window.confirm(`Auto-fix ${autoFixableIssues.length} issues?\n\nChanges will be saved to database. Use "Deploy to Git" to update the website.`)) {
      return;
    }

    try {
      const result = await bulkAutoFix(
        autoFixableIssues.map(issue => issue.id)
      );

      await loadData();

      const summary = `Success: ${result.fixed_count || 0}\nFailed: ${result.failed_count || 0}`;
      toast.success(`Bulk auto-fix complete!\n\n${summary}`, {
        title: 'Bulk Fix Complete',
        duration: 6000
      });
    } catch (err) {
      toast.error('Failed to bulk auto-fix: ' + err.message);
      console.error('Error bulk auto-fixing:', err);
    }
  };

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
              title="Git deployment settings"
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
          <span role="img" aria-label="warning">⚠️</span> Warning: No page ID provided to SEO panel
        </div>
      )}

      {/* Issues List */}
      <div className="issues-container">
        {refreshing && (
          <div className="refreshing-overlay">
            <div className="refreshing-spinner">Updating...</div>
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
            <div className="no-issues-icon celebration">
              <span role="img" aria-label="celebration">🎉</span>
            </div>
            <div className="no-issues-text">
              <strong>All issues have been fixed!</strong>
              <div className="no-issues-subtext">
                {fixedIssues.filter(i => i.deployed_to_git).length} deployed to Git.
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
                    <span role="img" aria-label="check">✅</span> Fixed ({fixedIssues.length})
                  </div>

                  <div className="fixed-issues-stats">
                    {verifiedIssues.length > 0 && (
                      <div className="stat-verified">
                        <span role="img" aria-label="verified">✅</span> Verified: {verifiedIssues.length}
                      </div>
                    )}

                    {needsAttentionIssues.length > 0 && (
                      <div className="stat-needs-attention">
                        <span>
                          <span role="img" aria-label="warning">⚠️</span> Needs attention: {needsAttentionIssues.length}
                        </span>
                        <button
                          onClick={() => handleAnalyze(true)}
                          disabled={analyzingPage}
                          className="btn-inline-action warning"
                        >
                          {analyzingPage ? 'Verifying...' : 'Re-verify'}
                        </button>
                      </div>
                    )}

                    {pendingVerificationIssues.length > 0 && (
                      <div className="stat-pending">
                        <span>
                          <span role="img" aria-label="pending">🔵</span> Pending verification: {pendingVerificationIssues.length}
                        </span>
                        <button
                          onClick={() => handleAnalyze(true)}
                          disabled={analyzingPage}
                          className="btn-inline-action info"
                        >
                          {analyzingPage ? 'Verifying...' : 'Verify'}
                        </button>
                      </div>
                    )}

                    {dbOnlyIssues.length > 0 && (
                      <>
                        <div className="stat-db-only">
                          <span role="img" aria-label="db">⚠️</span> DB only: {dbOnlyIssues.length} (not deployed)
                        </div>
                        {!gitEnabled && (
                          <div className="stat-tip">
                            <span role="img" aria-label="tip">💡</span> Enable Git deployment to auto-deploy changes.
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
                        <><span role="img" aria-label="loading">⏳</span> Deploying...</>
                      ) : (
                        <><span role="img" aria-label="rocket">🚀</span> Deploy to Git ({dbOnlyIssues.length} pending)</>
                      )}
                    </button>
                  )}

                  {/* All verified celebration */}
                  {dbOnlyIssues.length === 0 && verifiedIssues.length === fixedIssues.length && verifiedIssues.length > 0 && (
                    <div className="all-verified-message">
                      <div className="message-title">
                        <span role="img" aria-label="celebration">🎉</span> All changes verified!
                      </div>
                      <div className="message-subtitle">
                        Successfully reflected on the website.
                      </div>
                    </div>
                  )}

                  {/* All deployed, pending verification */}
                  {dbOnlyIssues.length === 0 && pendingVerificationIssues.length > 0 && gitEnabled && (
                    <div className="all-deployed-message">
                      <div className="message-title">
                        <span role="img" aria-label="deployed">🔵</span> All changes deployed to Git!
                      </div>
                      <div className="message-subtitle">
                        Run SEO re-analysis to verify changes.
                      </div>
                      <button
                        onClick={() => handleAnalyze(true)}
                        disabled={analyzingPage}
                        className="btn-verify-full"
                      >
                        {analyzingPage ? 'Analyzing...' : 'Re-analyze & Verify'}
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
