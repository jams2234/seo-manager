/**
 * Sitemap Editor API Service
 * Handles sitemap entry CRUD, sessions, and AI analysis
 */
import apiClient from './api';

export const sitemapEditorService = {
  // =========================================================================
  // Entries
  // =========================================================================

  // List entries for a domain
  listEntries: (domainId, filters = {}) => {
    const params = { domain: domainId, ...filters };
    return apiClient.get('/sitemap-editor/entries/', { params });
  },

  // Get single entry
  getEntry: (entryId) => apiClient.get(`/sitemap-editor/entries/${entryId}/`),

  // Create new entry
  createEntry: (domainId, sessionId, data) =>
    apiClient.post('/sitemap-editor/entries/', {
      domain_id: domainId,
      session_id: sessionId,
      ...data,
    }),

  // Update entry
  updateEntry: (entryId, sessionId, data) =>
    apiClient.patch(`/sitemap-editor/entries/${entryId}/`, {
      session_id: sessionId,
      ...data,
    }),

  // Delete entry
  deleteEntry: (entryId, sessionId) =>
    apiClient.delete(`/sitemap-editor/entries/${entryId}/`, {
      data: { session_id: sessionId },
    }),

  // Check entry URL status
  checkEntryStatus: (entryId) =>
    apiClient.post(`/sitemap-editor/entries/${entryId}/check-status/`),

  // =========================================================================
  // Edit Sessions
  // =========================================================================

  // List sessions for a domain
  listSessions: (domainId, status = null) => {
    const params = { domain: domainId };
    if (status) params.status = status;
    return apiClient.get('/sitemap-editor/sessions/', { params });
  },

  // Get single session
  getSession: (sessionId) =>
    apiClient.get(`/sitemap-editor/sessions/${sessionId}/`),

  // Create new session
  createSession: (domainId, name = null) =>
    apiClient.post('/sitemap-editor/sessions/', {
      domain_id: domainId,
      name,
    }),

  // Cancel session
  cancelSession: (sessionId) =>
    apiClient.delete(`/sitemap-editor/sessions/${sessionId}/`),

  // Generate preview
  generatePreview: (sessionId) =>
    apiClient.post(`/sitemap-editor/sessions/${sessionId}/preview/`),

  // Validate session
  validateSession: (sessionId) =>
    apiClient.post(`/sitemap-editor/sessions/${sessionId}/validate/`),

  // Deploy session
  deploySession: (sessionId, commitMessage = null) =>
    apiClient.post(`/sitemap-editor/sessions/${sessionId}/deploy/`, {
      commit_message: commitMessage,
    }),

  // Get session diff
  getSessionDiff: (sessionId) =>
    apiClient.get(`/sitemap-editor/sessions/${sessionId}/diff/`),

  // Sync from live sitemap
  syncFromSitemap: (domainId, sitemapUrl = null) =>
    apiClient.post('/sitemap-editor/sessions/sync/', {
      domain_id: domainId,
      sitemap_url: sitemapUrl,
    }),

  // Bulk import entries
  bulkImport: (sessionId, entries) =>
    apiClient.post(`/sitemap-editor/sessions/${sessionId}/bulk-import/`, {
      entries,
    }),

  // =========================================================================
  // Change History
  // =========================================================================

  // List changes for a session
  listChanges: (sessionId) =>
    apiClient.get('/sitemap-editor/changes/', {
      params: { session: sessionId },
    }),

  // Get single change
  getChange: (changeId) =>
    apiClient.get(`/sitemap-editor/changes/${changeId}/`),
};

export const sitemapAIService = {
  // =========================================================================
  // AI Analysis
  // =========================================================================

  // Analyze sitemap entries
  analyzeSitemap: (domainId) =>
    apiClient.post('/sitemap-ai/analyze/', { domain_id: domainId }),

  // Get suggestions for a single entry
  getEntrySuggestions: (entryId, includeMetrics = true) =>
    apiClient.get(`/sitemap-ai/suggestions/${entryId}/`, {
      params: { include_metrics: includeMetrics },
    }),

  // Apply AI suggestions
  applySuggestions: (domainId, sessionId, suggestions) =>
    apiClient.post('/sitemap-ai/apply-suggestions/', {
      domain_id: domainId,
      session_id: sessionId,
      suggestions,
    }),

  // Analyze SEO issues
  analyzeIssues: (domainId) =>
    apiClient.post('/sitemap-ai/issues/', { domain_id: domainId }),

  // Generate full AI report
  generateReport: (domainId) =>
    apiClient.post('/sitemap-ai/report/', { domain_id: domainId }),
};

export const aiChatService = {
  // =========================================================================
  // AI Conversations
  // =========================================================================

  // List conversations
  listConversations: (filters = {}) =>
    apiClient.get('/ai-chat/conversations/', { params: filters }),

  // Get single conversation with messages
  getConversation: (conversationId) =>
    apiClient.get(`/ai-chat/conversations/${conversationId}/`),

  // Create new conversation
  createConversation: (data) =>
    apiClient.post('/ai-chat/conversations/', data),

  // Delete conversation
  deleteConversation: (conversationId) =>
    apiClient.delete(`/ai-chat/conversations/${conversationId}/`),

  // Send message to conversation
  sendMessage: (conversationId, message) =>
    apiClient.post(`/ai-chat/conversations/${conversationId}/send/`, { message }),

  // Run analysis in conversation
  runAnalysis: (conversationId, analysisType) =>
    apiClient.post(`/ai-chat/conversations/${conversationId}/analyze/`, {
      analysis_type: analysisType,
    }),
};

export default sitemapEditorService;
