/**
 * Sitemap Editor Tab Component
 * Main component for viewing and editing sitemap entries
 */
import React, { useState, useEffect, useCallback } from 'react';
import { sitemapEditorService } from '../../services/sitemapEditorService';
import SitemapTable from './SitemapTable';
import SitemapPreviewPanel from './SitemapPreviewPanel';
import SitemapAIPanel from './SitemapAIPanel';
import './SitemapEditorTab.css';

const SitemapEditorTab = ({ domainId, domain }) => {
  // State
  const [entries, setEntries] = useState([]);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState(null);


  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showInvalid, setShowInvalid] = useState(false);

  // Panels
  const [showPreview, setShowPreview] = useState(false);
  const [showAIPanel, setShowAIPanel] = useState(false);
  const [previewData, setPreviewData] = useState(null);


  // Load entries
  const loadEntries = useCallback(async () => {
    if (!domainId) return;

    try {
      setLoading(true);
      const filters = {};
      if (searchTerm) filters.search = searchTerm;
      if (statusFilter) filters.status = statusFilter;
      if (showInvalid) filters.is_valid = 'false';

      const response = await sitemapEditorService.listEntries(domainId, filters);
      setEntries(response.data.entries || response.data.results || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load entries:', err);
      setError('Failed to load sitemap entries');
    } finally {
      setLoading(false);
    }
  }, [domainId, searchTerm, statusFilter, showInvalid]);

  // Initial load
  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  // Sync from live sitemap
  const handleSync = async () => {
    if (!domainId) return;

    try {
      setSyncing(true);
      setError(null);

      const response = await sitemapEditorService.syncFromSitemap(domainId);
      const result = response.data;

      if (result.error) {
        setError(result.message);
      } else {
        alert(`Synced ${result.created} new entries, updated ${result.updated} entries`);
        loadEntries();
      }
    } catch (err) {
      console.error('Sync failed:', err);
      setError('Failed to sync from sitemap');
    } finally {
      setSyncing(false);
    }
  };

  // Create or get active session
  const getOrCreateSession = async () => {
    if (session) return session;

    try {
      // Try to find existing draft session
      const sessionsResponse = await sitemapEditorService.listSessions(domainId, 'draft');
      const sessions = sessionsResponse.data.results || [];

      if (sessions.length > 0) {
        setSession(sessions[0]);
        return sessions[0];
      }

      // Create new session
      const createResponse = await sitemapEditorService.createSession(domainId);
      const newSession = createResponse.data.session;
      setSession(newSession);
      return newSession;
    } catch (err) {
      console.error('Failed to get/create session:', err);
      throw err;
    }
  };

  // Add new entry
  const handleAddEntry = async (entryData) => {
    try {
      const activeSession = await getOrCreateSession();
      await sitemapEditorService.createEntry(domainId, activeSession.id, entryData);
      loadEntries();
    } catch (err) {
      console.error('Failed to add entry:', err);
      setError('Failed to add entry');
    }
  };

  // Update entry
  const handleUpdateEntry = async (entryId, updates) => {
    try {
      const activeSession = await getOrCreateSession();
      await sitemapEditorService.updateEntry(entryId, activeSession.id, updates);
      loadEntries();
    } catch (err) {
      console.error('Failed to update entry:', err);
      setError('Failed to update entry');
    }
  };

  // Delete entry
  const handleDeleteEntry = async (entryId) => {
    if (!window.confirm('Are you sure you want to remove this entry?')) return;

    try {
      const activeSession = await getOrCreateSession();
      await sitemapEditorService.deleteEntry(entryId, activeSession.id);
      loadEntries();
    } catch (err) {
      console.error('Failed to delete entry:', err);
      setError('Failed to delete entry');
    }
  };

  // Generate preview
  const handleGeneratePreview = async () => {
    try {
      const activeSession = await getOrCreateSession();
      const response = await sitemapEditorService.generatePreview(activeSession.id);
      setPreviewData(response.data);
      setShowPreview(true);
    } catch (err) {
      console.error('Failed to generate preview:', err);
      setError('Failed to generate preview');
    }
  };

  // Deploy to Git
  const handleDeploy = async () => {
    if (!session) {
      setError('No active editing session');
      return;
    }

    const commitMessage = window.prompt(
      'Enter commit message (optional):',
      `Update sitemap - ${new Date().toLocaleString()}`
    );

    if (commitMessage === null) return; // User cancelled

    try {
      // Validate first
      const validationResponse = await sitemapEditorService.validateSession(session.id);
      const validation = validationResponse.data;

      if (!validation.valid) {
        const proceed = window.confirm(
          `Validation found ${validation.issues.length} issues:\n` +
          validation.issues.slice(0, 3).join('\n') +
          (validation.issues.length > 3 ? `\n...and ${validation.issues.length - 3} more` : '') +
          '\n\nDeploy anyway?'
        );
        if (!proceed) return;
      }

      // Deploy
      const response = await sitemapEditorService.deploySession(session.id, commitMessage);
      const result = response.data;

      if (result.error) {
        setError(result.message);
      } else {
        alert(`Deployed successfully!\nCommit: ${result.commit_hash}`);
        setSession(null); // Clear session after successful deploy
        loadEntries();
      }
    } catch (err) {
      console.error('Deploy failed:', err);
      setError('Failed to deploy: ' + (err.response?.data?.error || err.message));
    }
  };

  // Check URL status
  const handleCheckStatus = async (entryId) => {
    try {
      const response = await sitemapEditorService.checkEntryStatus(entryId);
      const result = response.data;

      if (result.error) {
        alert(`Error: ${result.message}`);
      } else {
        loadEntries(); // Refresh to show updated status
      }
    } catch (err) {
      console.error('Status check failed:', err);
    }
  };

  // Toggle AI analysis for single entry
  const handleToggleAI = async (entryId, enabled) => {
    try {
      await sitemapEditorService.toggleEntryAI(entryId, enabled);
      // Update local state immediately for responsive UI
      setEntries(prev => prev.map(e =>
        e.id === entryId ? { ...e, ai_analysis_enabled: enabled } : e
      ));
    } catch (err) {
      console.error('Failed to toggle AI analysis:', err);
      setError('AI 분석 설정 변경에 실패했습니다.');
    }
  };

  // Bulk toggle AI analysis for multiple entries
  const handleBulkToggleAI = async (entryIds, enabled) => {
    try {
      await sitemapEditorService.bulkToggleAI(entryIds, enabled);
      // Update local state immediately
      setEntries(prev => prev.map(e =>
        entryIds.includes(e.id) ? { ...e, ai_analysis_enabled: enabled } : e
      ));
    } catch (err) {
      console.error('Failed to bulk toggle AI analysis:', err);
      setError('AI 분석 설정 일괄 변경에 실패했습니다.');
    }
  };

  return (
    <div className="sitemap-editor-tab">
      {/* Header */}
      <div className="editor-header">
        <div className="header-title">
          <h2>Sitemap Editor</h2>
          <span className="entry-count">{entries.length} entries</span>
          {session && (
            <span className="session-badge">
              Editing: {session.name}
              {session.entries_added > 0 && ` (+${session.entries_added})`}
              {session.entries_removed > 0 && ` (-${session.entries_removed})`}
              {session.entries_modified > 0 && ` (~${session.entries_modified})`}
            </span>
          )}
        </div>

        <div className="header-actions">
          <button
            onClick={handleSync}
            className="btn btn-secondary"
            disabled={syncing}
          >
            {syncing ? '동기화 중...' : '🔄 사이트맵 동기화'}
          </button>
          <button
            onClick={() => setShowAIPanel(!showAIPanel)}
            className={`btn ${showAIPanel ? 'btn-active' : 'btn-secondary'}`}
          >
            🤖 AI 분석
          </button>
          <button
            onClick={handleGeneratePreview}
            className="btn btn-secondary"
          >
            👁️ 미리보기
          </button>
          <button
            onClick={handleDeploy}
            className="btn btn-primary"
            disabled={!session}
          >
            🚀 Git 배포
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* Filters */}
      <div className="filters-bar">
        <input
          type="text"
          placeholder="URL 검색..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="filter-select"
        >
          <option value="">모든 상태</option>
          <option value="active">Active</option>
          <option value="pending_add">Pending Add</option>
          <option value="pending_modify">Pending Modify</option>
          <option value="pending_remove">Pending Remove</option>
        </select>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={showInvalid}
            onChange={(e) => setShowInvalid(e.target.checked)}
          />
          오류만 표시
        </label>
      </div>

      {/* Main Content */}
      <div className="editor-content">
        {/* URL Sidebar - AI 분석 대상 URL 목록 */}
        <div className="domain-sidebar">
          <div className="sidebar-header">
            <h4>AI 분석 대상 URL</h4>
            <span className="sidebar-count">
              {entries.filter(e => e.ai_analysis_enabled).length}개
            </span>
          </div>

          <div className="domain-list url-list">
            {loading ? (
              <div className="sidebar-loading">로딩 중...</div>
            ) : entries.filter(e => e.ai_analysis_enabled).length === 0 ? (
              <div className="sidebar-empty">
                AI 분석 대상 URL이 없습니다.
                <br />
                <small>테이블에서 체크박스를 선택하세요</small>
              </div>
            ) : (
              entries.filter(e => e.ai_analysis_enabled).map((entry) => {
                // URL에서 경로만 추출 (루트는 도메인 표시)
                let displayPath = entry.loc;
                try {
                  const url = new URL(entry.loc);
                  const pathname = url.pathname || '/';
                  // 루트 경로면 도메인명 표시, 아니면 경로 표시
                  displayPath = pathname === '/' ? url.hostname : pathname;
                } catch (e) {
                  displayPath = entry.loc;
                }

                return (
                  <div
                    key={entry.id}
                    className="domain-item url-item"
                    title={entry.loc}
                  >
                    <span className="url-path">{displayPath}</span>
                    <button
                      onClick={() => handleToggleAI(entry.id, false)}
                      className="btn-remove-domain"
                      title="AI 분석 목록에서 제거"
                    >
                      ✕
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Table */}
        <div className={`table-section ${showAIPanel ? 'with-panel' : ''}`}>
          {loading ? (
            <div className="loading-container">
              <div className="loading-spinner"></div>
              <p>Loading entries...</p>
            </div>
          ) : (
            <SitemapTable
              entries={entries}
              onAddEntry={handleAddEntry}
              onUpdateEntry={handleUpdateEntry}
              onDeleteEntry={handleDeleteEntry}
              onCheckStatus={handleCheckStatus}
              onToggleAI={handleToggleAI}
              onBulkToggleAI={handleBulkToggleAI}
            />
          )}
        </div>

        {/* AI Panel */}
        {showAIPanel && (
          <SitemapAIPanel
            domainId={domainId}
            domainName={domain?.domain_name}
            entries={entries}
            session={session}
            onApplySuggestions={(suggestions) => {
              // Refresh after applying suggestions
              loadEntries();
            }}
            onClose={() => setShowAIPanel(false)}
          />
        )}
      </div>

      {/* Preview Panel */}
      {showPreview && previewData && (
        <SitemapPreviewPanel
          previewData={previewData}
          onClose={() => setShowPreview(false)}
        />
      )}
    </div>
  );
};

export default SitemapEditorTab;
