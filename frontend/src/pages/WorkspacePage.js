/**
 * Workspace Page
 * Full-page workspace for managing multiple tree tabs
 */
import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { TreeWorkspace } from '../components/workspace';
import './WorkspacePage.css';

const WorkspacePage = () => {
  const { workspaceId } = useParams();
  const navigate = useNavigate();

  return (
    <div className="workspace-page">
      {/* Header */}
      <header className="workspace-header">
        <div className="header-left">
          <button className="back-btn" onClick={() => navigate('/')}>
            <span className="back-icon">←</span>
            홈으로
          </button>
          <h1 className="header-title">트리 워크스페이스</h1>
        </div>
        <div className="header-right">
          <span className="header-badge">Beta</span>
        </div>
      </header>

      {/* Workspace Content */}
      <main className="workspace-main">
        <TreeWorkspace
          initialWorkspaceId={workspaceId ? parseInt(workspaceId) : null}
        />
      </main>
    </div>
  );
};

export default WorkspacePage;
