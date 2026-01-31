/**
 * Custom Hook for SEO Issue Categories
 * Centralizes issue filtering and categorization logic
 */
import { useMemo } from 'react';

/**
 * Issue Status Constants
 */
export const IssueStatus = {
  OPEN: 'open',
  FIXED: 'fixed',
  AUTO_FIXED: 'auto_fixed',
  IGNORED: 'ignored',
};

/**
 * Verification Status Constants
 */
export const VerificationStatus = {
  NOT_DEPLOYED: 'not_deployed',
  PENDING: 'pending',
  VERIFIED: 'verified',
  NEEDS_ATTENTION: 'needs_attention',
};

/**
 * Issue Severity Constants
 */
export const IssueSeverity = {
  CRITICAL: 'critical',
  WARNING: 'warning',
  INFO: 'info',
};

/**
 * Hook to categorize and filter SEO issues
 * @param {Array} issues - Array of SEO issue objects
 * @returns {Object} Categorized issues and counts
 */
const useIssueCategories = (issues = []) => {
  const issuesArray = useMemo(() =>
    Array.isArray(issues) ? issues : [],
    [issues]
  );

  // Basic status categories
  const openIssues = useMemo(() =>
    issuesArray.filter(issue => issue.status === IssueStatus.OPEN),
    [issuesArray]
  );

  const fixedIssues = useMemo(() =>
    issuesArray.filter(issue =>
      issue.status === IssueStatus.AUTO_FIXED ||
      issue.status === IssueStatus.FIXED
    ),
    [issuesArray]
  );

  const ignoredIssues = useMemo(() =>
    issuesArray.filter(issue => issue.status === IssueStatus.IGNORED),
    [issuesArray]
  );

  // Severity-based filtering (for open issues)
  const criticalIssues = useMemo(() =>
    openIssues.filter(issue => issue.severity === IssueSeverity.CRITICAL),
    [openIssues]
  );

  const warningIssues = useMemo(() =>
    openIssues.filter(issue => issue.severity === IssueSeverity.WARNING),
    [openIssues]
  );

  const infoIssues = useMemo(() =>
    openIssues.filter(issue => issue.severity === IssueSeverity.INFO),
    [openIssues]
  );

  // Auto-fix availability
  const autoFixableIssues = useMemo(() =>
    openIssues.filter(issue => issue.auto_fix_available),
    [openIssues]
  );

  // Deployment-based categories (for fixed issues)
  const deployedIssues = useMemo(() =>
    fixedIssues.filter(issue => issue.deployed_to_git),
    [fixedIssues]
  );

  const dbOnlyIssues = useMemo(() =>
    fixedIssues.filter(issue => !issue.deployed_to_git),
    [fixedIssues]
  );

  // Verification status categories
  const verifiedIssues = useMemo(() =>
    fixedIssues.filter(issue => issue.verification_status === VerificationStatus.VERIFIED),
    [fixedIssues]
  );

  const needsAttentionIssues = useMemo(() =>
    fixedIssues.filter(issue => issue.verification_status === VerificationStatus.NEEDS_ATTENTION),
    [fixedIssues]
  );

  const pendingVerificationIssues = useMemo(() =>
    deployedIssues.filter(issue =>
      issue.verification_status === VerificationStatus.PENDING ||
      !issue.verification_status
    ),
    [deployedIssues]
  );

  // Counts
  const counts = useMemo(() => ({
    total: issuesArray.length,
    open: openIssues.length,
    fixed: fixedIssues.length,
    ignored: ignoredIssues.length,
    critical: criticalIssues.length,
    warning: warningIssues.length,
    info: infoIssues.length,
    autoFixable: autoFixableIssues.length,
    deployed: deployedIssues.length,
    dbOnly: dbOnlyIssues.length,
    verified: verifiedIssues.length,
    needsAttention: needsAttentionIssues.length,
    pendingVerification: pendingVerificationIssues.length,
  }), [
    issuesArray,
    openIssues,
    fixedIssues,
    ignoredIssues,
    criticalIssues,
    warningIssues,
    infoIssues,
    autoFixableIssues,
    deployedIssues,
    dbOnlyIssues,
    verifiedIssues,
    needsAttentionIssues,
    pendingVerificationIssues,
  ]);

  // Status checks
  const hasOpenIssues = openIssues.length > 0;
  const hasFixedIssues = fixedIssues.length > 0;
  const hasAutoFixable = autoFixableIssues.length > 0;
  const hasPendingDeployment = dbOnlyIssues.length > 0;
  const hasPendingVerification = pendingVerificationIssues.length > 0;
  const hasNeedsAttention = needsAttentionIssues.length > 0;
  const allVerified = fixedIssues.length > 0 &&
    verifiedIssues.length === fixedIssues.length;

  return {
    // Issue arrays
    issues: issuesArray,
    openIssues,
    fixedIssues,
    ignoredIssues,
    criticalIssues,
    warningIssues,
    infoIssues,
    autoFixableIssues,
    deployedIssues,
    dbOnlyIssues,
    verifiedIssues,
    needsAttentionIssues,
    pendingVerificationIssues,

    // Counts object
    counts,

    // Status checks
    hasOpenIssues,
    hasFixedIssues,
    hasAutoFixable,
    hasPendingDeployment,
    hasPendingVerification,
    hasNeedsAttention,
    allVerified,
  };
};

export default useIssueCategories;
