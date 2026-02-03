/**
 * Main App Component with Routing
 */
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ToastProvider } from './contexts/ToastContext';
import Toast from './components/common/Toast';
import HomePage from './pages/HomePage';
import DomainAnalysisPage from './pages/DomainAnalysisPage';
import WorkspacePage from './pages/WorkspacePage';
import './App.css';

function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <div className="App">
          <Toast />
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/domain/:domainId" element={<DomainAnalysisPage />} />
            <Route path="/workspace" element={<WorkspacePage />} />
            <Route path="/workspace/:workspaceId" element={<WorkspacePage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </BrowserRouter>
    </ToastProvider>
  );
}

export default App;
