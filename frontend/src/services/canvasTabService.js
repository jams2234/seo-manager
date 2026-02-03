/**
 * Canvas Tab API Service
 * Manages per-domain canvas tabs
 */
import apiClient from './api';

const BASE_URL = '/canvas-tabs';

export const canvasTabService = {
  /**
   * Get all canvas tabs for a domain
   * @param {number} domainId - Domain ID
   * @returns {Promise} - List of canvas tabs
   */
  getTabs: (domainId) => apiClient.get(`${BASE_URL}/domain/${domainId}/`),

  /**
   * Add a new canvas tab to a domain
   * @param {number} domainId - Domain ID
   * @param {string} name - Optional tab name
   * @returns {Promise} - Created tab
   */
  addTab: (domainId, name = null) =>
    apiClient.post(`${BASE_URL}/domain/${domainId}/add/`, name ? { name } : {}),

  /**
   * Update a canvas tab
   * @param {number} tabId - Tab ID
   * @param {Object} data - Update data {name, viewport, custom_positions, is_active}
   * @returns {Promise} - Updated tab
   */
  updateTab: (tabId, data) =>
    apiClient.patch(`${BASE_URL}/${tabId}/update/`, data),

  /**
   * Delete a canvas tab
   * @param {number} tabId - Tab ID
   * @returns {Promise}
   */
  deleteTab: (tabId) => apiClient.delete(`${BASE_URL}/${tabId}/delete/`),

  /**
   * Activate a canvas tab
   * @param {number} tabId - Tab ID
   * @returns {Promise} - Activated tab
   */
  activateTab: (tabId) => apiClient.post(`${BASE_URL}/${tabId}/activate/`),

  /**
   * Save custom positions for a canvas tab
   * @param {number} tabId - Tab ID
   * @param {Object} positions - Node positions {pageId: {x, y}}
   * @param {Object} viewport - Viewport state {x, y, zoom}
   * @returns {Promise} - Updated tab
   */
  savePositions: (tabId, positions, viewport = null) =>
    apiClient.post(`${BASE_URL}/${tabId}/save-positions/`, { positions, viewport }),
};

export default canvasTabService;
