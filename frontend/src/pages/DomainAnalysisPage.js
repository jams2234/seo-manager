/**
 * Domain Analysis Page
 * Main page showing tree visualization and metrics
 */
import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import useDomainStore from '../store/domainStore';
import SubdomainTreeWithControls from '../components/tree/SubdomainTreeWithControls';
import Dashboard from '../components/dashboard/Dashboard';
import PageDetails from '../components/dashboard/PageDetails';
import ProgressModal from '../components/common/ProgressModal';
import SitemapEditorTab from '../components/sitemap-editor/SitemapEditorTab';
import { AILearningDashboard } from '../components/ai';
import { domainService } from '../services/domainService';
import './DomainAnalysisPage.css';

const DomainAnalysisPage = () => {
  const { domainId } = useParams();
  const navigate = useNavigate();
  const {
    currentDomain,
    treeData,
    selectedPage,
    loading,
    error,
    fetchDomainWithTree,
    refreshDomain,
    refreshSearchConsole,
    scanDomain,
    setSelectedPage,
    deleteDomain,
    clearError
  } = useDomainStore();

  const [activeTab, setActiveTab] = useState('tree'); // 'tree', 'sitemap', or 'dashboard'
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isRefreshingSC, setIsRefreshingSC] = useState(false);
  const [isScanning, setIsScanning] = useState(false);

  // Task progress tracking
  const [showProgressModal, setShowProgressModal] = useState(false);
  const [taskProgress, setTaskProgress] = useState({
    state: 'PENDING',
    percent: 0,
    status: '',
    current: 0,
    total: 100,
    error: null
  });
  const pollingIntervalRef = useRef(null);

  useEffect(() => {
    if (domainId) {
      // Optimized: Fetch domain and tree in a single parallel request
      fetchDomainWithTree(domainId);
    }
  }, [domainId, fetchDomainWithTree]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    setShowProgressModal(true);
    setTaskProgress({
      state: 'PROGRESS',
      percent: 50,
      status: '전체 스캔 중... (PageSpeed + 색인)',
      current: 50,
      total: 100,
      error: null
    });

    try {
      await refreshDomain(domainId);
      setTaskProgress({
        state: 'SUCCESS',
        percent: 100,
        status: '전체 스캔 완료!',
        current: 100,
        total: 100,
        error: null
      });
      setTimeout(() => setShowProgressModal(false), 1500);
    } catch (err) {
      setTaskProgress({
        state: 'FAILURE',
        percent: 0,
        status: '스캔 실패',
        current: 0,
        total: 100,
        error: err.message
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleRefreshSearchConsole = async () => {
    setIsRefreshingSC(true);
    setShowProgressModal(true);
    setTaskProgress({
      state: 'PROGRESS',
      percent: 50,
      status: '색인 상태 업데이트 중...',
      current: 50,
      total: 100,
      error: null
    });

    try {
      await refreshSearchConsole(domainId);
      setTaskProgress({
        state: 'SUCCESS',
        percent: 100,
        status: '색인 상태 업데이트 완료!',
        current: 100,
        total: 100,
        error: null
      });
      setTimeout(() => setShowProgressModal(false), 1500);
    } catch (err) {
      setTaskProgress({
        state: 'FAILURE',
        percent: 0,
        status: '업데이트 실패',
        current: 0,
        total: 100,
        error: err.message
      });
    } finally {
      setIsRefreshingSC(false);
    }
  };

  const handleScan = async () => {
    setIsScanning(true);
    try {
      const result = await scanDomain(domainId);

      // Show progress modal and start polling
      setShowProgressModal(true);
      setTaskProgress({
        state: 'PENDING',
        percent: 0,
        status: 'Starting scan...',
        current: 0,
        total: 100,
        error: null
      });

      // Start polling task status
      startTaskPolling(result.task_id);
    } catch (err) {
      console.error('Scan failed:', err);
      setIsScanning(false);
    }
  };

  const startTaskPolling = (taskId) => {
    // Clear existing interval if any
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    // Poll every 2 seconds
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const response = await domainService.getTaskStatus(taskId);
        const status = response.data;

        setTaskProgress({
          state: status.state,
          percent: status.percent || 0,
          status: status.status || '',
          current: status.current || 0,
          total: status.total || 100,
          error: status.error || null
        });

        // Stop polling if task is complete or failed
        if (status.ready) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
          setIsScanning(false);

          // Refresh domain data on success
          if (status.state === 'SUCCESS') {
            setTimeout(() => {
              fetchDomainWithTree(domainId);
            }, 1000);
          }
        }
      } catch (err) {
        console.error('Failed to poll task status:', err);
      }
    }, 2000);
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const handleDelete = async () => {
    if (window.confirm(`Are you sure you want to delete ${currentDomain?.domain_name}?`)) {
      try {
        await deleteDomain(domainId);
        navigate('/');
      } catch (err) {
        console.error('Delete failed:', err);
      }
    }
  };

  const handleNodeClick = (pageId) => {
    setSelectedPage(pageId);
  };

  if (loading && !currentDomain) {
    return (
      <div className="analysis-page">
        <div className="container">
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Loading domain...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error && !currentDomain) {
    return (
      <div className="analysis-page">
        <div className="container">
          <div className="error-message">
            <span>⚠️</span>
            <span>{error}</span>
            <button onClick={() => navigate('/')} className="btn btn-secondary">
              Back to Home
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="analysis-page">
      {/* Progress Modal */}
      <ProgressModal
        isOpen={showProgressModal}
        progress={taskProgress}
        onClose={() => setShowProgressModal(false)}
        onComplete={() => {
          setShowProgressModal(false);
          setActiveTab('dashboard');
        }}
      />

      <div className="container">
        {/* Header */}
        <div className="page-header">
          <div className="header-content">
            <div>
              <button onClick={() => navigate('/')} className="back-button">
                ← Back
              </button>
              <h1 className="page-title">
                {currentDomain?.protocol}://{currentDomain?.domain_name}
              </h1>
              <p className="page-subtitle">
                {currentDomain?.total_pages || 0} pages • {currentDomain?.total_subdomains || 0} subdomains
              </p>
            </div>
            <div className="header-actions">
              <button
                onClick={handleRefreshSearchConsole}
                className="btn btn-secondary"
                disabled={isRefreshingSC || loading}
                title="색인 상태만 빠르게 업데이트 (PageSpeed 스캔 없음)"
              >
                {isRefreshingSC ? (
                  <>
                    <span className="loading-spinner"></span>
                    업데이트 중...
                  </>
                ) : (
                  '⚡ 빠른 업데이트'
                )}
              </button>
              <button
                onClick={handleRefresh}
                className="btn btn-secondary"
                disabled={isRefreshing || loading}
                title="전체 스캔: PageSpeed + 색인 상태 (느림, 완전한 재분석)"
              >
                {isRefreshing ? (
                  <>
                    <span className="loading-spinner"></span>
                    스캔 중...
                  </>
                ) : (
                  '🔄 전체 스캔'
                )}
              </button>
              <button
                onClick={handleScan}
                className="btn btn-primary"
                disabled={isScanning || loading}
                title="백그라운드 풀스캔 (새 페이지 발견 + 메트릭 수집)"
              >
                {isScanning ? (
                  <>
                    <span className="loading-spinner"></span>
                    스캔 중...
                  </>
                ) : (
                  '🔍 풀스캔 (백그라운드)'
                )}
              </button>
              <button
                onClick={handleDelete}
                className="btn btn-danger"
                disabled={loading}
              >
                🗑️ Delete
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="error-message">
            <span>⚠️</span>
            <span>{error}</span>
            <button onClick={clearError} className="error-close">×</button>
          </div>
        )}

        {/* Tabs */}
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'tree' ? 'active' : ''}`}
            onClick={() => setActiveTab('tree')}
          >
            🌳 Tree View
          </button>
          <button
            className={`tab ${activeTab === 'sitemap' ? 'active' : ''}`}
            onClick={() => setActiveTab('sitemap')}
          >
            🗺️ Sitemap Editor
          </button>
          <button
            className={`tab ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            📊 Dashboard
          </button>
          <button
            className={`tab ${activeTab === 'ai' ? 'active' : ''}`}
            onClick={() => setActiveTab('ai')}
          >
            🧠 AI 학습
          </button>
        </div>

        {/* Content */}
        <div className="content-area">
          {activeTab === 'tree' && (
            <div className="tree-container">
              {treeData ? (
                <SubdomainTreeWithControls
                  treeData={treeData}
                  onNodeClick={handleNodeClick}
                  selectedPageId={selectedPage?.id}
                  domainId={domainId}
                />
              ) : (
                <div className="loading-container">
                  <div className="loading-spinner"></div>
                  <p>Loading tree...</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'sitemap' && currentDomain && (
            <SitemapEditorTab
              domainId={domainId}
              domain={currentDomain}
            />
          )}

          {activeTab === 'dashboard' && (
            <Dashboard domain={currentDomain} />
          )}

          {activeTab === 'ai' && currentDomain && (
            <AILearningDashboard
              domainId={domainId}
              domainName={currentDomain.domain_name}
            />
          )}

          {/* Page Details Sidebar */}
          {selectedPage && activeTab === 'tree' && (
            <div className="details-sidebar">
              <PageDetails
                page={selectedPage}
                onClose={() => setSelectedPage(null)}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DomainAnalysisPage;
