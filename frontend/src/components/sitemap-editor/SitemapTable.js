/**
 * Sitemap Table Component
 * Displays and edits sitemap entries with AI analysis selection
 */
import React, { useState, useMemo } from 'react';
import './SitemapTable.css';

const SitemapTable = ({
  entries,
  onAddEntry,
  onUpdateEntry,
  onDeleteEntry,
  onCheckStatus,
  onToggleAI,
  onBulkToggleAI,
}) => {
  const [editingId, setEditingId] = useState(null);
  const [editValues, setEditValues] = useState({});
  const [showAddForm, setShowAddForm] = useState(false);
  const [newEntry, setNewEntry] = useState({
    loc: '',
    lastmod: '',
    changefreq: '',
    priority: '',
  });

  const changefreqOptions = [
    { value: '', label: '선택 안함' },
    { value: 'always', label: 'Always' },
    { value: 'hourly', label: 'Hourly' },
    { value: 'daily', label: 'Daily' },
    { value: 'weekly', label: 'Weekly' },
    { value: 'monthly', label: 'Monthly' },
    { value: 'yearly', label: 'Yearly' },
    { value: 'never', label: 'Never' },
  ];

  // Calculate AI selection stats
  const aiStats = useMemo(() => {
    const enabled = entries.filter(e => e.ai_analysis_enabled).length;
    const total = entries.length;
    return { enabled, total, allSelected: total > 0 && enabled === total };
  }, [entries]);

  const getStatusBadge = (status) => {
    const badges = {
      active: { text: 'Active', class: 'badge-success' },
      pending_add: { text: '+Add', class: 'badge-info' },
      pending_modify: { text: '~Edit', class: 'badge-warning' },
      pending_remove: { text: '-Remove', class: 'badge-danger' },
    };
    const badge = badges[status] || { text: status, class: 'badge-default' };
    return <span className={`status-badge ${badge.class}`}>{badge.text}</span>;
  };

  const getHttpStatusBadge = (code) => {
    if (!code) return null;
    const isOk = code >= 200 && code < 400;
    return (
      <span className={`http-badge ${isOk ? 'http-ok' : 'http-error'}`}>
        {code}
      </span>
    );
  };

  const handleStartEdit = (entry) => {
    setEditingId(entry.id);
    setEditValues({
      loc: entry.loc,
      lastmod: entry.lastmod || '',
      changefreq: entry.changefreq || '',
      priority: entry.priority !== null ? entry.priority : '',
    });
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditValues({});
  };

  const handleSaveEdit = async (entryId) => {
    const updates = {};
    if (editValues.lastmod !== undefined) updates.lastmod = editValues.lastmod || null;
    if (editValues.changefreq !== undefined) updates.changefreq = editValues.changefreq || null;
    if (editValues.priority !== undefined && editValues.priority !== '') {
      updates.priority = parseFloat(editValues.priority);
    }

    await onUpdateEntry(entryId, updates);
    setEditingId(null);
    setEditValues({});
  };

  const handleAddSubmit = async (e) => {
    e.preventDefault();

    if (!newEntry.loc) {
      alert('URL is required');
      return;
    }

    const entryData = {
      loc: newEntry.loc,
      lastmod: newEntry.lastmod || null,
      changefreq: newEntry.changefreq || null,
      priority: newEntry.priority ? parseFloat(newEntry.priority) : null,
    };

    await onAddEntry(entryData);
    setNewEntry({ loc: '', lastmod: '', changefreq: '', priority: '' });
    setShowAddForm(false);
  };

  const handleSelectAll = () => {
    if (onBulkToggleAI) {
      const allIds = entries.map(e => e.id);
      onBulkToggleAI(allIds, !aiStats.allSelected);
    }
  };

  const handleToggleSingle = (entry) => {
    if (onToggleAI) {
      onToggleAI(entry.id, !entry.ai_analysis_enabled);
    }
  };

  return (
    <div className="sitemap-table-container">
      {/* Toolbar */}
      <div className="table-toolbar">
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="btn btn-add"
        >
          {showAddForm ? '취소' : '+ 새 항목 추가'}
        </button>
        {onBulkToggleAI && (
          <div className="ai-selection-info">
            <span className="ai-count">
              AI 분석 대상: <strong>{aiStats.enabled}</strong> / {aiStats.total}
            </span>
          </div>
        )}
      </div>

      {/* Add Entry Form */}
      {showAddForm && (
        <form onSubmit={handleAddSubmit} className="add-entry-form">
          <div className="form-row">
            <input
              type="url"
              placeholder="https://example.com/page"
              value={newEntry.loc}
              onChange={(e) => setNewEntry({ ...newEntry, loc: e.target.value })}
              required
              className="form-input loc-input"
            />
            <input
              type="date"
              value={newEntry.lastmod}
              onChange={(e) => setNewEntry({ ...newEntry, lastmod: e.target.value })}
              className="form-input date-input"
            />
            <select
              value={newEntry.changefreq}
              onChange={(e) => setNewEntry({ ...newEntry, changefreq: e.target.value })}
              className="form-input select-input"
            >
              {changefreqOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <input
              type="number"
              step="0.1"
              min="0"
              max="1"
              placeholder="0.5"
              value={newEntry.priority}
              onChange={(e) => setNewEntry({ ...newEntry, priority: e.target.value })}
              className="form-input priority-input"
            />
            <button type="submit" className="btn btn-primary">추가</button>
          </div>
        </form>
      )}

      {/* Table */}
      <div className="table-wrapper">
        <table className="sitemap-table">
          <thead>
            <tr>
              {onToggleAI && (
                <th className="col-ai-select">
                  <label className="checkbox-wrapper" title="전체 선택/해제">
                    <input
                      type="checkbox"
                      checked={aiStats.allSelected}
                      onChange={handleSelectAll}
                    />
                    <span className="checkmark"></span>
                  </label>
                </th>
              )}
              <th className="col-status">상태</th>
              <th className="col-url">URL</th>
              <th className="col-lastmod">Last Modified</th>
              <th className="col-changefreq">Changefreq</th>
              <th className="col-priority">Priority</th>
              <th className="col-http">HTTP</th>
              <th className="col-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 ? (
              <tr>
                <td colSpan={onToggleAI ? "8" : "7"} className="empty-message">
                  No entries found. Click "사이트맵 동기화" to load from live sitemap.
                </td>
              </tr>
            ) : (
              entries.map((entry) => (
                <tr
                  key={entry.id}
                  className={`
                    ${entry.status !== 'active' ? 'row-pending' : ''}
                    ${!entry.is_valid ? 'row-invalid' : ''}
                    ${entry.ai_analysis_enabled ? 'row-ai-enabled' : ''}
                  `}
                >
                  {onToggleAI && (
                    <td className="col-ai-select">
                      <label className="checkbox-wrapper">
                        <input
                          type="checkbox"
                          checked={entry.ai_analysis_enabled || false}
                          onChange={() => handleToggleSingle(entry)}
                        />
                        <span className="checkmark"></span>
                      </label>
                    </td>
                  )}
                  <td className="col-status">
                    {getStatusBadge(entry.status)}
                    {!entry.is_valid && (
                      <span className="invalid-badge" title={entry.validation_errors?.join(', ')}>
                        ⚠️
                      </span>
                    )}
                  </td>
                  <td className="col-url">
                    {editingId === entry.id ? (
                      <input
                        type="text"
                        value={editValues.loc}
                        disabled
                        className="edit-input"
                      />
                    ) : (
                      <a href={entry.loc} target="_blank" rel="noopener noreferrer" className="url-link">
                        {entry.loc}
                      </a>
                    )}
                    {entry.redirect_url && entry.redirect_url !== entry.loc && (
                      <div className="redirect-info">
                        → {entry.redirect_url}
                      </div>
                    )}
                  </td>
                  <td className="col-lastmod">
                    {editingId === entry.id ? (
                      <input
                        type="date"
                        value={editValues.lastmod}
                        onChange={(e) => setEditValues({ ...editValues, lastmod: e.target.value })}
                        className="edit-input"
                      />
                    ) : (
                      entry.lastmod || '-'
                    )}
                  </td>
                  <td className="col-changefreq">
                    {editingId === entry.id ? (
                      <select
                        value={editValues.changefreq}
                        onChange={(e) => setEditValues({ ...editValues, changefreq: e.target.value })}
                        className="edit-input"
                      >
                        {changefreqOptions.map((opt) => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    ) : (
                      entry.changefreq || '-'
                    )}
                  </td>
                  <td className="col-priority">
                    {editingId === entry.id ? (
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="1"
                        value={editValues.priority}
                        onChange={(e) => setEditValues({ ...editValues, priority: e.target.value })}
                        className="edit-input priority-edit"
                      />
                    ) : (
                      entry.priority != null ? Number(entry.priority).toFixed(1) : '-'
                    )}
                  </td>
                  <td className="col-http">
                    {getHttpStatusBadge(entry.http_status_code)}
                    {entry.ai_suggested && (
                      <span className="ai-badge" title={entry.ai_suggestion_reason}>
                        🤖
                      </span>
                    )}
                  </td>
                  <td className="col-actions">
                    {editingId === entry.id ? (
                      <>
                        <button
                          onClick={() => handleSaveEdit(entry.id)}
                          className="action-btn save"
                          title="저장"
                        >
                          ✓
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          className="action-btn cancel"
                          title="취소"
                        >
                          ✕
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => handleStartEdit(entry)}
                          className="action-btn edit"
                          title="편집"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={() => onCheckStatus(entry.id)}
                          className="action-btn check"
                          title="상태 확인"
                        >
                          🔍
                        </button>
                        <button
                          onClick={() => onDeleteEntry(entry.id)}
                          className="action-btn delete"
                          title="삭제"
                        >
                          🗑️
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SitemapTable;
