/**
 * Domain Input Component
 * Form for adding new domains
 */
import React, { useState } from 'react';
import useDomainStore from '../../store/domainStore';
import './DomainInput.css';

const DomainInput = ({ onSuccess, onCancel }) => {
  const { createDomain, loading, error } = useDomainStore();
  const [formData, setFormData] = useState({
    domain_name: '',
    protocol: 'https'
  });
  const [validationError, setValidationError] = useState('');

  const validateDomain = (domain) => {
    // Remove protocol if included
    const cleanDomain = domain.replace(/^(https?:\/\/)?(www\.)?/, '');

    // Basic domain validation
    const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?(\.[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?)*\.[a-zA-Z]{2,}$/;

    if (!cleanDomain) {
      return 'Please enter a domain name';
    }

    if (!domainRegex.test(cleanDomain)) {
      return 'Please enter a valid domain name (e.g., example.com)';
    }

    return '';
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    // Clear validation error when user types
    if (validationError) {
      setValidationError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate domain
    const error = validateDomain(formData.domain_name);
    if (error) {
      setValidationError(error);
      return;
    }

    // Clean domain name (remove protocol and www)
    const cleanDomain = formData.domain_name
      .replace(/^(https?:\/\/)?(www\.)?/, '')
      .toLowerCase()
      .trim();

    try {
      const domain = await createDomain({
        domain_name: cleanDomain,
        protocol: formData.protocol
      });

      if (onSuccess) {
        onSuccess(domain);
      }
    } catch (err) {
      // Error is handled by store
      console.error('Failed to create domain:', err);
    }
  };

  return (
    <div className="domain-input card">
      <h3 className="input-title">Add New Domain</h3>
      <form onSubmit={handleSubmit} className="domain-form">
        <div className="form-row">
          <div className="form-group protocol-group">
            <label htmlFor="protocol">Protocol</label>
            <select
              id="protocol"
              name="protocol"
              value={formData.protocol}
              onChange={handleChange}
              className="form-select"
              disabled={loading}
            >
              <option value="https">HTTPS</option>
              <option value="http">HTTP</option>
            </select>
          </div>

          <div className="form-group domain-group">
            <label htmlFor="domain_name">Domain Name</label>
            <input
              id="domain_name"
              name="domain_name"
              type="text"
              value={formData.domain_name}
              onChange={handleChange}
              placeholder="example.com"
              className={`form-input ${validationError || error ? 'error' : ''}`}
              disabled={loading}
              autoFocus
            />
          </div>
        </div>

        {(validationError || error) && (
          <div className="form-error">
            {validationError || error}
          </div>
        )}

        <div className="form-actions">
          <button
            type="button"
            onClick={onCancel}
            className="btn btn-secondary"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="loading-spinner"></span>
                Adding...
              </>
            ) : (
              'Add Domain'
            )}
          </button>
        </div>
      </form>

      <div className="input-hint">
        <p>
          <strong>Tip:</strong> Enter just the domain name (e.g., example.com).
          We'll automatically discover all subdomains and analyze their SEO metrics.
        </p>
      </div>
    </div>
  );
};

export default DomainInput;
