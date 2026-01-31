/**
 * Home Page - Domain List and Input
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useDomainStore from '../store/domainStore';
import DomainInput from '../components/domain/DomainInput';
import DomainCard from '../components/domain/DomainCard';
import './HomePage.css';

const HomePage = () => {
  const navigate = useNavigate();
  const { domains, loading, error, fetchDomains, clearError } = useDomainStore();
  const [showInput, setShowInput] = useState(false);

  useEffect(() => {
    fetchDomains();
  }, [fetchDomains]);

  const handleDomainCreated = (domain) => {
    setShowInput(false);
    navigate(`/domain/${domain.id}`);
  };

  const handleDomainClick = (domainId) => {
    navigate(`/domain/${domainId}`);
  };

  return (
    <div className="home-page">
      <div className="container">
        <div className="page-header">
          <h1 className="page-title">SEO Domain Analyzer</h1>
          <p className="page-subtitle">
            Analyze your domains and subdomains with Google SEO metrics
          </p>
        </div>

        {error && (
          <div className="error-message">
            <span>⚠️</span>
            <span>{error}</span>
            <button onClick={clearError} className="error-close">×</button>
          </div>
        )}

        <div className="domain-actions">
          <button
            className="btn btn-primary"
            onClick={() => setShowInput(!showInput)}
          >
            {showInput ? 'Cancel' : '+ Add New Domain'}
          </button>
        </div>

        {showInput && (
          <div className="domain-input-container">
            <DomainInput
              onSuccess={handleDomainCreated}
              onCancel={() => setShowInput(false)}
            />
          </div>
        )}

        {loading && domains.length === 0 ? (
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Loading domains...</p>
          </div>
        ) : domains.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🌐</div>
            <h2>No domains yet</h2>
            <p>Add your first domain to start analyzing SEO metrics</p>
            <button
              className="btn btn-primary"
              onClick={() => setShowInput(true)}
            >
              Add Domain
            </button>
          </div>
        ) : (
          <div className="domains-grid">
            {domains.map((domain) => (
              <DomainCard
                key={domain.id}
                domain={domain}
                onClick={() => handleDomainClick(domain.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default HomePage;
