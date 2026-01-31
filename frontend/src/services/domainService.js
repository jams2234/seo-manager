/**
 * Domain API Service
 */
import apiClient from './api';

export const domainService = {
  // List all domains
  listDomains: () => apiClient.get('/domains/'),

  // Get domain by ID
  getDomain: (id) => apiClient.get(`/domains/${id}/`),

  // Create new domain
  createDomain: (data) => apiClient.post('/domains/', data),

  // Trigger full scan (background)
  scanDomain: (id) => apiClient.post(`/domains/${id}/scan/`),

  // Refresh domain data (real-time, full scan with PageSpeed)
  refreshDomain: (id) => apiClient.post(`/domains/${id}/refresh/`),

  // Refresh Search Console data only (lightweight, fast)
  refreshSearchConsole: (id) => apiClient.post(`/domains/${id}/refresh_search_console/`),

  // Get domain tree structure
  getTree: (id) => apiClient.get(`/domains/${id}/tree/`),

  // Delete domain
  deleteDomain: (id) => apiClient.delete(`/domains/${id}/`),

  // Get task status
  getTaskStatus: (taskId) => apiClient.get(`/domains/task/${taskId}/`),
};

export const pageService = {
  // List pages (with optional domain filter)
  listPages: (domainId = null) => {
    const params = domainId ? { domain: domainId } : {};
    return apiClient.get('/pages/', { params });
  },

  // Get page by ID
  getPage: (id) => apiClient.get(`/pages/${id}/`),

  // Get page metrics
  getPageMetrics: (id) => apiClient.get(`/pages/${id}/metrics/`),

  // Get page metrics history
  getPageMetricsHistory: (id) => apiClient.get(`/pages/${id}/metrics/history/`),

  // Update page (for customizations)
  updatePage: (id, data) => apiClient.patch(`/pages/${id}/`, data),

  // Bulk update positions
  bulkUpdatePositions: (updates) => apiClient.post('/pages/bulk-update-positions/', { updates }),

  // Reset page position to auto-layout
  resetPagePosition: (id) => apiClient.post(`/pages/${id}/reset-position/`),

  // Change parent page
  changeParent: (pageId, parentId) => apiClient.post(`/pages/${pageId}/change-parent/`, { parent_id: parentId }),

  // Bulk reparent multiple pages at once
  bulkReparent: (changes) => apiClient.post('/pages/bulk-reparent/', { changes }),

  // Assign group to page
  assignGroup: (pageId, groupId) => apiClient.patch(`/pages/${pageId}/`, { group: groupId }),
};

export const categoryService = {
  // List categories (with optional domain filter)
  listCategories: (domainId = null) => {
    const params = domainId ? { domain: domainId } : {};
    return apiClient.get('/page-group-categories/', { params });
  },

  // Get category by ID
  getCategory: (id) => apiClient.get(`/page-group-categories/${id}/`),

  // Create new category
  createCategory: (data) => apiClient.post('/page-group-categories/', data),

  // Update category
  updateCategory: (id, data) => apiClient.patch(`/page-group-categories/${id}/`, data),

  // Delete category
  deleteCategory: (id) => apiClient.delete(`/page-group-categories/${id}/`),

  // Get groups in category
  getCategoryGroups: (id) => apiClient.get(`/page-group-categories/${id}/groups/`),

  // Reorder category
  reorderCategory: (id, order) => apiClient.post(`/page-group-categories/${id}/reorder/`, { order }),

  // Toggle expand state
  toggleExpand: (id) => apiClient.post(`/page-group-categories/${id}/toggle-expand/`),
};

export const groupService = {
  // List groups (with optional domain and category filter)
  listGroups: (domainId = null, categoryId = null) => {
    const params = {};
    if (domainId) params.domain = domainId;
    if (categoryId !== null) params.category = categoryId;
    return apiClient.get('/page-groups/', { params });
  },

  // Get group by ID
  getGroup: (id) => apiClient.get(`/page-groups/${id}/`),

  // Create new group
  createGroup: (data) => apiClient.post('/page-groups/', data),

  // Update group
  updateGroup: (id, data) => apiClient.patch(`/page-groups/${id}/`, data),

  // Delete group
  deleteGroup: (id) => apiClient.delete(`/page-groups/${id}/`),

  // Get pages in group
  getGroupPages: (id) => apiClient.get(`/page-groups/${id}/pages/`),
};

export default domainService;
