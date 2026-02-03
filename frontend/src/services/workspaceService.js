/**
 * Workspace Service
 * API calls for managing tree workspaces and tabs
 */
import api from './api';

const BASE_URL = '/workspaces';

export const workspaceService = {
  // ==========================================================================
  // Workspace CRUD
  // ==========================================================================

  /**
   * Get all workspaces
   * @returns {Promise} List of workspaces
   */
  listWorkspaces: () => api.get(BASE_URL + '/'),

  /**
   * Create a new workspace
   * @param {Object} data - { name, description, is_default, initial_domain_ids }
   * @returns {Promise} Created workspace
   */
  createWorkspace: (data) => api.post(BASE_URL + '/', data),

  /**
   * Get workspace detail with tabs
   * @param {number} workspaceId - Workspace ID
   * @returns {Promise} Workspace with tabs
   */
  getWorkspace: (workspaceId) => api.get(`${BASE_URL}/${workspaceId}/`),

  /**
   * Update workspace
   * @param {number} workspaceId - Workspace ID
   * @param {Object} data - { name, description, is_default }
   * @returns {Promise} Updated workspace
   */
  updateWorkspace: (workspaceId, data) => api.patch(`${BASE_URL}/${workspaceId}/`, data),

  /**
   * Delete workspace
   * @param {number} workspaceId - Workspace ID
   * @returns {Promise}
   */
  deleteWorkspace: (workspaceId) => api.delete(`${BASE_URL}/${workspaceId}/`),

  /**
   * Get or create default workspace
   * @returns {Promise} Default workspace
   */
  getDefaultWorkspace: () => api.get(`${BASE_URL}/default/`),

  // ==========================================================================
  // Tab Management
  // ==========================================================================

  /**
   * Add a new tab to workspace
   * @param {number} workspaceId - Workspace ID
   * @param {Object} data - { domain_id, name, is_active }
   * @returns {Promise} Created tab
   */
  addTab: (workspaceId, data) => api.post(`${BASE_URL}/${workspaceId}/tabs/`, data),

  /**
   * Update tab
   * @param {number} workspaceId - Workspace ID
   * @param {number} tabId - Tab ID
   * @param {Object} data - { name, is_active, viewport, preferences, custom_positions, has_unsaved_changes }
   * @returns {Promise} Updated tab
   */
  updateTab: (workspaceId, tabId, data) =>
    api.patch(`${BASE_URL}/${workspaceId}/tabs/${tabId}/`, data),

  /**
   * Remove tab from workspace
   * @param {number} workspaceId - Workspace ID
   * @param {number} tabId - Tab ID
   * @returns {Promise}
   */
  removeTab: (workspaceId, tabId) =>
    api.delete(`${BASE_URL}/${workspaceId}/tabs/${tabId}/delete/`),

  /**
   * Reorder tabs
   * @param {number} workspaceId - Workspace ID
   * @param {Array} tabIds - Ordered list of tab IDs
   * @returns {Promise} Updated workspace
   */
  reorderTabs: (workspaceId, tabIds) =>
    api.post(`${BASE_URL}/${workspaceId}/tabs/reorder/`, { tab_ids: tabIds }),

  /**
   * Activate a specific tab
   * @param {number} workspaceId - Workspace ID
   * @param {number} tabId - Tab ID
   * @returns {Promise} Activated tab
   */
  activateTab: (workspaceId, tabId) =>
    api.post(`${BASE_URL}/${workspaceId}/tabs/${tabId}/activate/`),

  /**
   * Save custom node positions for a tab
   * @param {number} workspaceId - Workspace ID
   * @param {number} tabId - Tab ID
   * @param {Object} positions - { nodeId: { x, y }, ... }
   * @returns {Promise}
   */
  saveTabPositions: (workspaceId, tabId, positions) =>
    api.post(`${BASE_URL}/${workspaceId}/tabs/${tabId}/save-positions/`, { positions }),

  // ==========================================================================
  // Utility Functions
  // ==========================================================================

  /**
   * Save tab viewport state
   * @param {number} workspaceId - Workspace ID
   * @param {number} tabId - Tab ID
   * @param {Object} viewport - { x, y, zoom }
   * @returns {Promise}
   */
  saveTabViewport: (workspaceId, tabId, viewport) =>
    api.patch(`${BASE_URL}/${workspaceId}/tabs/${tabId}/`, { viewport }),

  /**
   * Save tab preferences
   * @param {number} workspaceId - Workspace ID
   * @param {number} tabId - Tab ID
   * @param {Object} preferences - { filterMode, layoutDirection, ... }
   * @returns {Promise}
   */
  saveTabPreferences: (workspaceId, tabId, preferences) =>
    api.patch(`${BASE_URL}/${workspaceId}/tabs/${tabId}/`, { preferences }),
};

export default workspaceService;
