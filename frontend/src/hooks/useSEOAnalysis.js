/**
 * Custom Hook for SEO Analysis API
 * Handles page analysis, issue fetching, and auto-fix operations
 */
import { useState, useCallback } from 'react';
import apiClient from '../services/api';

const useSEOAnalysis = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [issues, setIssues] = useState([]);
  const [analysisReport, setAnalysisReport] = useState(null);

  /**
   * Run SEO analysis on a page
   * @param {number} pageId - The page ID to analyze
   * @param {Object} options - Analysis options
   * @param {boolean} options.includeContentAnalysis - Whether to include content analysis
   * @param {string[]} options.targetKeywords - Target keywords for analysis
   * @param {boolean} options.verifyMode - If true, verify deployed fixes against actual website
   */
  const analyzePageSEO = useCallback(async (pageId, options = {}) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.post(
        `/pages/${pageId}/analyze/`,
        {
          include_content_analysis: options.includeContentAnalysis !== false,
          target_keywords: options.targetKeywords || [],
          verify_mode: options.verifyMode || false,  // 검증 모드 추가
        }
      );
      setAnalysisReport(response.data);
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Analysis failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Fetch SEO issues for a page
   * @param {number} pageId - The page ID to fetch issues for
   * @param {Object} filters - Filter options
   * @param {string} filters.status - Filter by status (open/fixed/ignored)
   * @param {string} filters.severity - Filter by severity (critical/warning/info)
   */
  const fetchIssues = useCallback(async (pageId, filters = {}) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('page_id', pageId);  // Changed from 'page' to 'page_id' to avoid DRF pagination conflict
      if (filters.status) {
        params.append('status', filters.status);
      }
      if (filters.severity) {
        params.append('severity', filters.severity);
      }

      const response = await apiClient.get(`/seo-issues/?${params.toString()}`);
      const issuesData = response.data.results || response.data || [];
      setIssues(issuesData);
      return issuesData;
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to fetch issues';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Auto-fix a single SEO issue
   * @param {number} issueId - The issue ID to fix
   */
  const autoFixIssue = useCallback(async (issueId) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.post(`/seo-issues/${issueId}/auto-fix/`);
      // Update issues state by updating the fixed issue
      setIssues((prevIssues) =>
        prevIssues.map((issue) =>
          issue.id === issueId ? { ...issue, status: 'auto_fixed' } : issue
        )
      );
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Auto-fix failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Auto-fix multiple SEO issues at once (automatically deploys to Git if enabled)
   * @param {number[]} issueIds - Array of issue IDs to fix
   */
  const bulkAutoFix = useCallback(async (issueIds) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.post('/seo-issues/bulk-fix/', {
        issue_ids: issueIds,
      });
      // Update issues state
      setIssues((prevIssues) =>
        prevIssues.map((issue) =>
          issueIds.includes(issue.id) ? { ...issue, status: 'auto_fixed' } : issue
        )
      );
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Bulk auto-fix failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Revert a fixed issue back to open state
   * @param {number} issueId - The issue ID to revert
   * @param {boolean} deployToGit - Whether to deploy the revert to Git
   */
  const revertIssue = useCallback(async (issueId, deployToGit = false) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.post(`/seo-issues/${issueId}/revert/`, {
        deploy_to_git: deployToGit,
      });
      // Update issues state
      setIssues((prevIssues) =>
        prevIssues.map((issue) =>
          issue.id === issueId ? { ...issue, status: 'open', deployed_to_git: false } : issue
        )
      );
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Revert failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Update fix value manually
   * @param {number} issueId - The issue ID
   * @param {string} suggestedValue - New suggested value
   */
  const updateFixValue = useCallback(async (issueId, suggestedValue) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.patch(`/seo-issues/${issueId}/update-fix/`, {
        suggested_value: suggestedValue,
      });
      // Update issues state
      setIssues((prevIssues) =>
        prevIssues.map((issue) =>
          issue.id === issueId ? { ...issue, suggested_value: suggestedValue } : issue
        )
      );
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Update failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Deploy all pending fixes to Git
   * @param {number} pageId - Optional page ID to filter
   */
  const deployPendingFixes = useCallback(async (pageId) => {
    setLoading(true);
    setError(null);
    try {
      const payload = pageId ? { page_id: pageId } : {};
      const response = await apiClient.post('/seo-issues/deploy-pending/', payload);
      // Refresh issues to update deployment status
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Deployment failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Fetch latest analysis report for a page
   * @param {number} pageId - The page ID
   */
  const fetchLatestReport = useCallback(async (pageId) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get(`/seo-reports/?page_id=${pageId}&ordering=-analyzed_at`);
      const reports = response.data.results || response.data || [];
      const latestReport = reports[0] || null;
      setAnalysisReport(latestReport);
      return latestReport;
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to fetch report';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Fetch Git configuration for a domain
   * @param {number} domainId - The domain ID
   */
  const fetchGitConfig = useCallback(async (domainId) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get(`/domains/${domainId}/`);
      return {
        git_enabled: response.data.git_enabled,
        git_repository: response.data.git_repository,
        git_branch: response.data.git_branch,
        git_target_path: response.data.git_target_path,
        last_deployed_at: response.data.last_deployed_at,
        deployment_status: response.data.deployment_status,
        last_deployment_error: response.data.last_deployment_error,
      };
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to fetch Git config';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Update Git configuration for a domain
   * @param {number} domainId - The domain ID
   * @param {Object} config - Git configuration
   */
  const updateGitConfig = useCallback(async (domainId, config) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.patch(`/domains/${domainId}/`, {
        git_enabled: config.git_enabled,
        git_repository: config.git_repository,
        git_branch: config.git_branch,
        git_token: config.git_token,
        git_target_path: config.git_target_path,
      });
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to update Git config';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Reset all state
   */
  const reset = useCallback(() => {
    setLoading(false);
    setError(null);
    setIssues([]);
    setAnalysisReport(null);
  }, []);

  return {
    // State
    loading,
    error,
    issues,
    analysisReport,

    // Actions
    analyzePageSEO,
    fetchIssues,
    autoFixIssue,
    bulkAutoFix,
    revertIssue,
    updateFixValue,
    deployPendingFixes,
    fetchLatestReport,
    fetchGitConfig,
    updateGitConfig,
    clearError,
    reset,
  };
};

export default useSEOAnalysis;
