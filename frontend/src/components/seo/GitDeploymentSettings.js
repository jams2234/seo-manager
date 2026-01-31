import React, { useState, useEffect } from 'react';
import useSEOAnalysis from '../../hooks/useSEOAnalysis';
import './GitDeploymentSettings.css';

const GitDeploymentSettings = ({ domainId, onClose }) => {
  const { fetchGitConfig, updateGitConfig, loading, error } = useSEOAnalysis();

  const [gitConfig, setGitConfig] = useState({
    git_enabled: false,
    git_repository: '',
    git_branch: 'main',
    git_token: '',
    git_target_path: 'public',
  });

  const [showToken, setShowToken] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);

  useEffect(() => {
    loadGitConfig();
  }, [domainId]);

  const loadGitConfig = async () => {
    try {
      const config = await fetchGitConfig(domainId);
      setGitConfig({
        git_enabled: config.git_enabled || false,
        git_repository: config.git_repository || '',
        git_branch: config.git_branch || 'main',
        git_token: '', // Don't show existing token
        git_target_path: config.git_target_path || 'public',
      });
    } catch (err) {
      console.error('Error loading Git config:', err);
    }
  };

  const handleInputChange = (field, value) => {
    setGitConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleToggle = () => {
    setGitConfig(prev => ({
      ...prev,
      git_enabled: !prev.git_enabled
    }));
  };

  const handleSave = async () => {
    try {
      setSaveStatus('saving');
      await updateGitConfig(domainId, gitConfig);
      setSaveStatus('success');
      setTimeout(() => {
        setSaveStatus(null);
        if (onClose) onClose();
      }, 2000);
    } catch (err) {
      setSaveStatus('error');
      console.error('Error saving Git config:', err);
    }
  };

  return (
    <div className="git-deployment-settings">
      <div className="git-settings-header">
        <h3>🚀 Git 자동 배포 설정</h3>
        <button className="close-button" onClick={onClose}>×</button>
      </div>

      <div className="git-settings-content">
        {/* Enable Toggle */}
        <div className="setting-row">
          <div className="setting-info">
            <label className="setting-label">Git 자동 배포</label>
            <p className="setting-description">
              SEO 수정 사항을 GitHub에 자동으로 커밋하고 Vercel 배포를 트리거합니다
            </p>
          </div>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={gitConfig.git_enabled}
              onChange={handleToggle}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>

        {gitConfig.git_enabled && (
          <>
            {/* Repository URL */}
            <div className="setting-row">
              <label className="setting-label">GitHub 저장소 URL *</label>
              <input
                type="text"
                className="setting-input"
                value={gitConfig.git_repository}
                onChange={(e) => handleInputChange('git_repository', e.target.value)}
                placeholder="https://github.com/username/repository.git"
              />
              <p className="setting-hint">
                HTTPS URL을 사용하세요 (SSH는 지원하지 않습니다)
              </p>
            </div>

            {/* Branch */}
            <div className="setting-row">
              <label className="setting-label">Branch</label>
              <input
                type="text"
                className="setting-input"
                value={gitConfig.git_branch}
                onChange={(e) => handleInputChange('git_branch', e.target.value)}
                placeholder="main"
              />
            </div>

            {/* GitHub Token */}
            <div className="setting-row">
              <label className="setting-label">GitHub Personal Access Token *</label>
              <div className="token-input-wrapper">
                <input
                  type={showToken ? 'text' : 'password'}
                  className="setting-input"
                  value={gitConfig.git_token}
                  onChange={(e) => handleInputChange('git_token', e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                />
                <button
                  className="toggle-visibility-btn"
                  onClick={() => setShowToken(!showToken)}
                  type="button"
                >
                  {showToken ? '👁️' : '👁️‍🗨️'}
                </button>
              </div>
              <p className="setting-hint">
                <a
                  href="https://github.com/settings/tokens/new?scopes=repo"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hint-link"
                >
                  Personal Access Token 생성하기 →
                </a>
                <br />
                필요한 권한: <code>repo</code> (Full control of private repositories)
              </p>
            </div>

            {/* Target Path (for Static HTML) */}
            <div className="setting-row">
              <label className="setting-label">대상 경로 (Static HTML 전용)</label>
              <input
                type="text"
                className="setting-input"
                value={gitConfig.git_target_path}
                onChange={(e) => handleInputChange('git_target_path', e.target.value)}
                placeholder="public"
              />
              <p className="setting-hint">
                HTML 파일이 위치한 디렉토리 (예: public, dist)<br />
                Next.js 프로젝트는 자동으로 감지됩니다
              </p>
            </div>

            {/* How it works */}
            <div className="info-box">
              <h4>💡 작동 방식</h4>
              <ol>
                <li>SEO 이슈를 자동 수정합니다</li>
                <li>GitHub 저장소에 변경사항을 커밋합니다</li>
                <li>Vercel이 자동으로 새 배포를 시작합니다</li>
                <li>웹사이트에 변경사항이 반영됩니다</li>
              </ol>
            </div>
          </>
        )}

        {/* Error Message */}
        {error && (
          <div className="error-message">
            ❌ {error}
          </div>
        )}

        {/* Save Status */}
        {saveStatus === 'success' && (
          <div className="success-message">
            ✅ 설정이 저장되었습니다!
          </div>
        )}

        {/* Action Buttons */}
        <div className="settings-actions">
          <button
            className="btn-cancel"
            onClick={onClose}
            disabled={loading}
          >
            취소
          </button>
          <button
            className="btn-save"
            onClick={handleSave}
            disabled={loading || (gitConfig.git_enabled && (!gitConfig.git_repository || !gitConfig.git_token))}
          >
            {loading ? '저장 중...' : saveStatus === 'saving' ? '저장 중...' : '저장'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default GitDeploymentSettings;
