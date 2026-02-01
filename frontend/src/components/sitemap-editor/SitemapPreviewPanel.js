/**
 * Sitemap Preview Panel Component
 * Shows XML preview of the sitemap
 */
import React, { useState } from 'react';
import './SitemapPreviewPanel.css';

const SitemapPreviewPanel = ({ previewData, onClose }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(previewData.xml_content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([previewData.xml_content], { type: 'application/xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sitemap.xml';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="preview-panel-overlay" onClick={onClose}>
      <div className="preview-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="preview-header">
          <div className="preview-title">
            <h3>📋 Sitemap Preview</h3>
            <div className="preview-stats">
              <span>{previewData.url_count} URLs</span>
              <span>•</span>
              <span>{formatFileSize(previewData.size_bytes)}</span>
            </div>
          </div>
          <div className="preview-actions">
            <button onClick={handleCopy} className="btn btn-secondary">
              {copied ? '✓ Copied!' : '📋 Copy'}
            </button>
            <button onClick={handleDownload} className="btn btn-secondary">
              ⬇️ Download
            </button>
            <button onClick={onClose} className="btn-close">
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="preview-content">
          <pre className="xml-preview">
            <code>{previewData.xml_content}</code>
          </pre>
        </div>

        {/* Footer */}
        <div className="preview-footer">
          <span>Generated at: {new Date(previewData.generated_at).toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
};

export default SitemapPreviewPanel;
