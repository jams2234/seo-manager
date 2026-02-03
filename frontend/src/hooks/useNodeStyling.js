/**
 * useNodeStyling Hook
 * Transforms filtered nodes into React Flow node format with positions and styling
 */
import { useMemo } from 'react';

/**
 * Transform backend nodes to React Flow nodes with styling
 *
 * @param {Array} nodes - Filtered tree nodes
 * @param {Object} draggedPositions - Temporary positions from dragging (not yet saved)
 * @param {number} selectedPageId - Currently selected page ID
 * @param {string} highlightedNode - Node ID to highlight (during drag)
 * @param {boolean} editMode - Whether edit mode is active
 * @param {Function} refreshTreeData - Callback to refresh tree data
 * @param {number} domainId - Domain ID for API calls
 * @param {Function} onOpenSEOPanel - Callback to open SEO panel
 * @param {Function} onNodeSelect - Callback when node is clicked (for detail panel)
 * @param {number} dataRefreshKey - Key that changes when data is refreshed (triggers group list refresh)
 * @returns {Array} Styled React Flow nodes
 */
const useNodeStyling = (
  nodes,
  draggedPositions,
  selectedPageId,
  highlightedNode,
  editMode,
  refreshTreeData,
  domainId,
  onOpenSEOPanel,
  onNodeSelect,
  dataRefreshKey = 0
) => {
  return useMemo(() => {
    if (!nodes || nodes.length === 0) {
      return [];
    }

    return nodes.map((node) => {
      // Position priority: dragged > manual > backend default
      let position = { x: 0, y: 0 };

      // 1. Dragged position (highest priority - not yet saved)
      if (draggedPositions[String(node.id)]) {
        position = draggedPositions[String(node.id)];
      }
      // 2. Manual position (saved to backend)
      else if (
        node.use_manual_position &&
        node.manual_position_x !== null &&
        node.manual_position_y !== null
      ) {
        position = { x: node.manual_position_x, y: node.manual_position_y };
      }
      // 3. Backend calculated position
      else if (node.position) {
        position = node.position;
      }

      return {
        id: String(node.id),
        type: 'custom',
        position: position,
        data: {
          pageId: node.id,
          domainId: domainId,
          label: node.label || node.url,
          customLabel: node.custom_label,
          url: node.url,
          path: node.path,
          seoScore: node.seo_score,
          performanceScore: node.performance_score,
          accessibilityScore: node.accessibility_score,
          totalPages: node.total_pages,
          isSubdomain: node.is_subdomain,
          isVisible: node.is_visible,
          status: node.status,
          selected: node.id === selectedPageId,
          isDropTarget: highlightedNode === String(node.id),
          depthLevel: node.depth_level || 0,
          editMode: editMode,
          group: node.group,
          // Index status from Search Console
          is_indexed: node.is_indexed,
          index_status: node.index_status,
          coverage_state: node.coverage_state,
          // Search Console analytics
          avg_position: node.avg_position,
          impressions: node.impressions,
          clicks: node.clicks,
          ctr: node.ctr,
          top_queries: node.top_queries,
          // Sitemap mismatch tracking
          sitemap_url: node.sitemap_url,
          has_sitemap_mismatch: node.has_sitemap_mismatch,
          redirect_chain: node.redirect_chain,
          sitemap_entry: node.sitemap_entry,
          // Canonical URL index status
          canonical_is_indexed: node.canonical_is_indexed,
          canonical_index_status: node.canonical_index_status,
          canonical_coverage_state: node.canonical_coverage_state,
          // Group filter state
          isFilteredOut: node.isFilteredOut || false,
          onUpdate: () => refreshTreeData(),
          onOpenSEOPanel: onOpenSEOPanel,
          onNodeSelect: onNodeSelect,
          dataRefreshKey: dataRefreshKey,
        },
      };
    });
  }, [
    nodes,
    draggedPositions,
    selectedPageId,
    highlightedNode,
    editMode,
    refreshTreeData,
    domainId,
    onOpenSEOPanel,
    onNodeSelect,
    dataRefreshKey,
  ]);
};

export default useNodeStyling;
