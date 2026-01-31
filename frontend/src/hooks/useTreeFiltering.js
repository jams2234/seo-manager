/**
 * useTreeFiltering Hook
 * Filters tree nodes based on filter mode, visibility settings, and group
 */
import { useMemo } from 'react';

/**
 * Filter tree nodes based on various criteria
 *
 * @param {Array} nodes - Raw tree nodes from backend
 * @param {string} filterMode - Filter mode: 'all', 'subdomains', 'good', 'needs-improvement'
 * @param {boolean} showHiddenNodes - Whether to show nodes marked as hidden
 * @param {number|null} activeGroupId - Filter by specific group ID (null = no group filter)
 * @returns {Array} Filtered nodes
 */
const useTreeFiltering = (nodes, filterMode, showHiddenNodes, activeGroupId = null) => {
  return useMemo(() => {
    if (!nodes || nodes.length === 0) {
      return [];
    }

    let filteredNodes = nodes;

    // Apply visibility filter
    if (!showHiddenNodes) {
      filteredNodes = filteredNodes.filter(node => node.is_visible !== false);
    }

    // Apply group filter (highest priority)
    // Instead of removing nodes, mark them as filtered (for opacity styling)
    if (activeGroupId !== null) {
      filteredNodes = filteredNodes.map(node => ({
        ...node,
        isFilteredOut: node.group?.id !== activeGroupId
      }));
    }

    // Apply filter mode
    switch (filterMode) {
      case 'subdomains':
        filteredNodes = filteredNodes.filter(node => node.is_subdomain);
        break;

      case 'good':
        filteredNodes = filteredNodes.filter(node => node.seo_score >= 90);
        break;

      case 'needs-improvement':
        filteredNodes = filteredNodes.filter(node => node.seo_score < 70);
        break;

      case 'all':
      default:
        // No additional filtering
        break;
    }

    return filteredNodes;
  }, [nodes, filterMode, showHiddenNodes, activeGroupId]);
};

export default useTreeFiltering;
