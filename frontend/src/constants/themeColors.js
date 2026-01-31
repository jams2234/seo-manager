/**
 * Theme Colors and Styling Constants
 * Centralized color definitions for consistent theming across the application
 */

/**
 * Depth level colors for tree visualization
 * Each level gets a distinct color for better visual hierarchy
 */
export const DEPTH_COLORS = [
  '#4F46E5', // Level 0 - Indigo (root)
  '#7C3AED', // Level 1 - Purple
  '#EC4899', // Level 2 - Pink
  '#F59E0B', // Level 3 - Amber
  '#10B981', // Level 4 - Green
  '#3B82F6', // Level 5+ - Blue
];

/**
 * Get color for a specific depth level
 * @param {number} depthLevel - The depth level (0-based)
 * @returns {string} Hex color code
 */
export const getDepthColor = (depthLevel) => {
  return DEPTH_COLORS[Math.min(depthLevel || 0, DEPTH_COLORS.length - 1)];
};

/**
 * SEO score thresholds and color classes
 */
export const SCORE_THRESHOLDS = {
  GOOD: 90,
  MEDIUM: 70,
  POOR: 0,
};

/**
 * Get color class based on SEO score
 * @param {number} score - SEO score (0-100)
 * @returns {string} Color class name ('good', 'medium', 'poor', or 'unknown')
 */
export const getScoreColor = (score) => {
  if (score === null || score === undefined) return 'unknown';
  if (score >= SCORE_THRESHOLDS.GOOD) return 'good';
  if (score >= SCORE_THRESHOLDS.MEDIUM) return 'medium';
  return 'poor';
};

/**
 * Status colors for page states
 */
export const STATUS_COLORS = {
  active: '#10B981',    // Green
  404: '#EF4444',       // Red
  500: '#F59E0B',       // Amber
  redirected: '#3B82F6', // Blue
};

/**
 * Get color for page status
 * @param {string} status - Page status
 * @returns {string} Hex color code
 */
export const getStatusColor = (status) => {
  return STATUS_COLORS[status] || STATUS_COLORS.active;
};
