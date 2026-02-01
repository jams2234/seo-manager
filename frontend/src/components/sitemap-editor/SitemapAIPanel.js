/**
 * Sitemap AI Panel Component
 * Shows AI analysis, conversation history, and chat interface
 */
import React, { useState, useEffect, useRef } from 'react';
import { sitemapAIService, aiChatService } from '../../services/sitemapEditorService';
import { domainService } from '../../services/domainService';
import './SitemapAIPanel.css';

const SitemapAIPanel = ({
  domainId,
  entries,
  session,
  onApplySuggestions,
  onClose,
}) => {
  // State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat', 'history', 'analysis'

  // Conversations
  const [conversations, setConversations] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [loadingConversations, setLoadingConversations] = useState(false);

  // Chat
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const chatEndRef = useRef(null);

  // Domain selection
  const [domains, setDomains] = useState([]);
  const [selectedDomainId, setSelectedDomainId] = useState(domainId);

  // Analysis results (for backwards compatibility)
  const [analysis, setAnalysis] = useState(null);

  // Load domains
  useEffect(() => {
    loadDomains();
  }, []);

  // Load conversations when domain changes
  useEffect(() => {
    if (selectedDomainId) {
      loadConversations();
    }
  }, [selectedDomainId]);

  // Auto scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentConversation?.messages]);

  const loadDomains = async () => {
    try {
      const response = await domainService.getDomains();
      setDomains(response.data.results || response.data || []);
    } catch (err) {
      console.error('Failed to load domains:', err);
    }
  };

  const loadConversations = async () => {
    setLoadingConversations(true);
    try {
      const response = await aiChatService.listConversations({
        domain: selectedDomainId,
        status: 'active',
      });
      setConversations(response.data.results || response.data || []);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    } finally {
      setLoadingConversations(false);
    }
  };

  const loadConversation = async (conversationId) => {
    setLoading(true);
    try {
      const response = await aiChatService.getConversation(conversationId);
      setCurrentConversation(response.data);
      setActiveTab('chat');
    } catch (err) {
      setError('대화를 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const createNewConversation = async (type = 'general') => {
    setLoading(true);
    setError(null);
    try {
      const response = await aiChatService.createConversation({
        domain_id: selectedDomainId,
        conversation_type: type,
      });
      setCurrentConversation(response.data);
      loadConversations(); // Refresh list
      setActiveTab('chat');
    } catch (err) {
      setError('새 대화를 시작하는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!message.trim() || !currentConversation || sending) return;

    setSending(true);
    setError(null);

    try {
      const response = await aiChatService.sendMessage(
        currentConversation.id,
        message.trim()
      );

      // Update conversation with new messages
      setCurrentConversation(response.data.conversation);
      setMessage('');
    } catch (err) {
      setError('메시지 전송에 실패했습니다.');
    } finally {
      setSending(false);
    }
  };

  const handleRunAnalysis = async (analysisType) => {
    if (!currentConversation) {
      // Create new conversation first
      await createNewConversation(analysisType === 'sitemap' ? 'sitemap_analysis' :
        analysisType === 'seo_issues' ? 'seo_issues' : 'full_report');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await aiChatService.runAnalysis(
        currentConversation.id,
        analysisType
      );

      setCurrentConversation(response.data.conversation);
      setAnalysis(response.data.analysis);
    } catch (err) {
      setError(`${analysisType} 분석에 실패했습니다.`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteConversation = async (conversationId) => {
    if (!window.confirm('이 대화를 삭제하시겠습니까?')) return;

    try {
      await aiChatService.deleteConversation(conversationId);
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(null);
      }
      loadConversations();
    } catch (err) {
      setError('대화 삭제에 실패했습니다.');
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const renderMessage = (msg) => {
    const isUser = msg.role === 'user';
    const isSystem = msg.role === 'system';

    return (
      <div
        key={msg.id}
        className={`chat-message ${isUser ? 'user' : isSystem ? 'system' : 'assistant'}`}
      >
        <div className="message-header">
          <span className="message-role">
            {isUser ? '👤 나' : isSystem ? '⚙️ 시스템' : '🤖 AI'}
          </span>
          <span className="message-time">{formatDate(msg.created_at)}</span>
        </div>
        <div className="message-content">
          {msg.content}
          {msg.structured_data && msg.message_type === 'analysis' && (
            <div className="analysis-result">
              {renderAnalysisData(msg.structured_data)}
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderAnalysisData = (data) => {
    if (!data) return null;

    return (
      <div className="analysis-summary">
        {data.overall_health_score !== undefined && (
          <div className="score-badge">
            건강 점수: <strong>{data.overall_health_score}</strong>/100
          </div>
        )}
        {data.issues && data.issues.length > 0 && (
          <div className="issues-preview">
            <strong>발견된 이슈: {data.issues.length}개</strong>
            <ul>
              {data.issues.slice(0, 3).map((issue, idx) => (
                <li key={idx} className={`issue-${issue.severity}`}>
                  [{issue.severity}] {issue.type}: {issue.description?.slice(0, 100)}...
                </li>
              ))}
            </ul>
          </div>
        )}
        {data.suggestions && data.suggestions.length > 0 && (
          <div className="suggestions-preview">
            <strong>제안: {data.suggestions.length}개</strong>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="ai-panel-container">
      {/* Header */}
      <div className="ai-panel-header">
        <div className="header-left">
          <h3>🤖 AI SEO 분석</h3>
          <select
            value={selectedDomainId || ''}
            onChange={(e) => setSelectedDomainId(e.target.value ? parseInt(e.target.value) : null)}
            className="domain-select"
          >
            <option value="">도메인 선택...</option>
            {domains.map((d) => (
              <option key={d.id} value={d.id}>
                {d.domain_name}
              </option>
            ))}
          </select>
        </div>
        <button onClick={onClose} className="btn-close">×</button>
      </div>

      {/* Tabs */}
      <div className="ai-tabs">
        <button
          className={`ai-tab ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          💬 대화
        </button>
        <button
          className={`ai-tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          📜 기록 ({conversations.length})
        </button>
        <button
          className={`ai-tab ${activeTab === 'analysis' ? 'active' : ''}`}
          onClick={() => setActiveTab('analysis')}
        >
          📊 분석
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="ai-error-banner">
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* Content */}
      <div className="ai-content">
        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <div className="chat-container">
            {!currentConversation ? (
              <div className="chat-welcome">
                <h4>새 대화 시작하기</h4>
                <p>AI에게 SEO 관련 질문을 하거나 분석을 요청하세요.</p>
                <div className="quick-actions">
                  <button
                    onClick={() => createNewConversation('sitemap_analysis')}
                    disabled={!selectedDomainId || loading}
                  >
                    🗺️ 사이트맵 분석
                  </button>
                  <button
                    onClick={() => createNewConversation('seo_issues')}
                    disabled={!selectedDomainId || loading}
                  >
                    🔍 SEO 이슈 분석
                  </button>
                  <button
                    onClick={() => createNewConversation('general')}
                    disabled={loading}
                  >
                    💬 일반 질문
                  </button>
                </div>
              </div>
            ) : (
              <>
                {/* Chat Messages */}
                <div className="chat-messages">
                  {currentConversation.messages?.map(renderMessage)}
                  {sending && (
                    <div className="chat-message assistant loading">
                      <div className="typing-indicator">
                        <span></span><span></span><span></span>
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                {/* Quick Analysis Buttons */}
                <div className="analysis-buttons">
                  <button
                    onClick={() => handleRunAnalysis('sitemap')}
                    disabled={loading || !selectedDomainId}
                    title="사이트맵 분석"
                  >
                    🗺️
                  </button>
                  <button
                    onClick={() => handleRunAnalysis('seo_issues')}
                    disabled={loading || !selectedDomainId}
                    title="SEO 이슈 분석"
                  >
                    🔍
                  </button>
                  <button
                    onClick={() => handleRunAnalysis('full_report')}
                    disabled={loading || !selectedDomainId}
                    title="전체 리포트"
                  >
                    📊
                  </button>
                </div>

                {/* Chat Input */}
                <form onSubmit={handleSendMessage} className="chat-input-form">
                  <input
                    type="text"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="AI에게 질문하세요..."
                    disabled={sending}
                    className="chat-input"
                  />
                  <button
                    type="submit"
                    disabled={!message.trim() || sending}
                    className="btn-send"
                  >
                    {sending ? '...' : '전송'}
                  </button>
                </form>
              </>
            )}
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="history-container">
            <div className="history-header">
              <h4>대화 기록</h4>
              <button
                onClick={() => createNewConversation('general')}
                className="btn-new-chat"
              >
                + 새 대화
              </button>
            </div>
            {loadingConversations ? (
              <div className="loading-spinner">불러오는 중...</div>
            ) : conversations.length === 0 ? (
              <div className="empty-state">
                <p>아직 대화 기록이 없습니다.</p>
                <button onClick={() => createNewConversation('general')}>
                  첫 대화 시작하기
                </button>
              </div>
            ) : (
              <div className="conversation-list">
                {conversations.map((conv) => (
                  <div
                    key={conv.id}
                    className={`conversation-item ${currentConversation?.id === conv.id ? 'active' : ''}`}
                    onClick={() => loadConversation(conv.id)}
                  >
                    <div className="conv-header">
                      <span className="conv-title">{conv.title}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteConversation(conv.id);
                        }}
                        className="btn-delete"
                      >
                        🗑️
                      </button>
                    </div>
                    <div className="conv-meta">
                      <span className="conv-type">{conv.conversation_type}</span>
                      <span className="conv-date">{formatDate(conv.updated_at)}</span>
                    </div>
                    {conv.last_message_preview && (
                      <div className="conv-preview">{conv.last_message_preview}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Analysis Tab (Legacy) */}
        {activeTab === 'analysis' && (
          <div className="analysis-container">
            <div className="analysis-actions">
              <button
                onClick={() => handleRunAnalysis('sitemap')}
                disabled={loading || !selectedDomainId}
              >
                🗺️ 사이트맵 분석
              </button>
              <button
                onClick={() => handleRunAnalysis('seo_issues')}
                disabled={loading || !selectedDomainId}
              >
                🔍 SEO 이슈 분석
              </button>
              <button
                onClick={() => handleRunAnalysis('full_report')}
                disabled={loading || !selectedDomainId}
              >
                📊 전체 리포트
              </button>
            </div>
            {loading && (
              <div className="analysis-loading">
                <div className="spinner"></div>
                <p>분석 중...</p>
              </div>
            )}
            {analysis && (
              <div className="analysis-result-full">
                {renderAnalysisData(analysis)}
                {analysis.summary && (
                  <div className="analysis-summary-text">
                    <h5>요약</h5>
                    <p>{analysis.summary}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SitemapAIPanel;
