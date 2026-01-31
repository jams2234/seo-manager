/**
 * TreeLegend Component
 * Displays SEO score legend with color codes
 */
import React from 'react';
import './SubdomainTree.css';

/**
 * TreeLegend - Shows SEO score color legend
 *
 * @param {Object} props - Component props
 * @returns {JSX.Element} Legend UI
 */
const TreeLegend = ({ autoConnectEnabled, editMode }) => {
  return (
    <div className="tree-legend">
      <div className="legend-title">SEO Score</div>
      <div className="legend-item">
        <div className="legend-color good"></div>
        <span>Good (≥90)</span>
      </div>
      <div className="legend-item">
        <div className="legend-color medium"></div>
        <span>Medium (70-89)</span>
      </div>
      <div className="legend-item">
        <div className="legend-color poor"></div>
        <span>Poor (&lt;70)</span>
      </div>
      <div className="legend-item">
        <div className="legend-color unknown"></div>
        <span>Unknown</span>
      </div>
      {autoConnectEnabled && editMode && (
        <div className="legend-note" style={{ marginTop: '8px', fontSize: '11px', color: '#6B7280' }}>
          💡 노드를 다른 노드 근처로 드래그하면 자동 연결됩니다
        </div>
      )}
    </div>
  );
};

export default TreeLegend;
