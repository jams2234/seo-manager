/**
 * Add Tab Modal Component
 * Modal for selecting a domain to add as a new tab
 */
import React, { useState } from 'react';
import './AddTabModal.css';

const AddTabModal = ({ domains, existingDomainIds, onAdd, onClose }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDomainId, setSelectedDomainId] = useState(null);

  // Filter domains
  const filteredDomains = domains.filter((domain) => {
    const matchesSearch = domain.domain_name
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  // Check if domain is already in workspace
  const isDomainInWorkspace = (domainId) => existingDomainIds.includes(domainId);

  // Handle add
  const handleAdd = () => {
    if (selectedDomainId) {
      onAdd(selectedDomainId);
    }
  };

  // Handle domain double click
  const handleDomainDoubleClick = (domainId) => {
    if (!isDomainInWorkspace(domainId)) {
      onAdd(domainId);
    }
  };

  return (
    <div className="add-tab-modal-overlay" onClick={onClose}>
      <div className="add-tab-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>도메인 추가</h3>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          {/* Search */}
          <div className="search-box">
            <input
              type="text"
              placeholder="도메인 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoFocus
            />
          </div>

          {/* Domain list */}
          <div className="domain-list">
            {filteredDomains.length === 0 ? (
              <div className="empty-message">
                {searchQuery ? '검색 결과가 없습니다' : '등록된 도메인이 없습니다'}
              </div>
            ) : (
              filteredDomains.map((domain) => {
                const isInWorkspace = isDomainInWorkspace(domain.id);
                const isSelected = domain.id === selectedDomainId;

                return (
                  <div
                    key={domain.id}
                    className={`domain-item ${isSelected ? 'selected' : ''} ${isInWorkspace ? 'in-workspace' : ''}`}
                    onClick={() => !isInWorkspace && setSelectedDomainId(domain.id)}
                    onDoubleClick={() => handleDomainDoubleClick(domain.id)}
                  >
                    <div className="domain-info">
                      <span className="domain-name">{domain.domain_name}</span>
                      {domain.avg_seo_score && (
                        <span className="domain-score">
                          SEO: {domain.avg_seo_score.toFixed(0)}
                        </span>
                      )}
                    </div>
                    <div className="domain-meta">
                      <span className="page-count">
                        {domain.total_pages || 0} 페이지
                      </span>
                      {isInWorkspace && (
                        <span className="in-workspace-badge">이미 추가됨</span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="modal-footer">
          <button className="cancel-btn" onClick={onClose}>
            취소
          </button>
          <button
            className="add-btn"
            onClick={handleAdd}
            disabled={!selectedDomainId}
          >
            추가
          </button>
        </div>
      </div>
    </div>
  );
};

export default AddTabModal;
