/**
 * Tree Visualization Configuration Constants
 * Centralized configuration for SubdomainTreeV2 component
 */

/**
 * Node Layout Configuration
 * Controls the size and spacing of nodes in the tree visualization
 */
export const NODE_LAYOUT = {
  // Individual node dimensions
  WIDTH: 320,
  HEIGHT: 240,

  // Dagre layout spacing
  NODE_SEPARATION: 200,    // Horizontal spacing between nodes at same level
  RANK_SEPARATION: 300,    // Vertical spacing between different levels
  MARGIN_X: 100,           // Left/right canvas margins
  MARGIN_Y: 100,           // Top/bottom canvas margins
};

/**
 * Interaction Configuration
 * Controls user interaction behavior
 */
export const INTERACTION = {
  // Auto-connect snap distance (pixels)
  SNAP_DISTANCE: 150,      // Maximum distance to snap to nearest node when dragging

  // Drag & drop
  ENABLE_DRAG_IN_AUTO_LAYOUT: false,  // Disable drag when auto-layout is active
};

/**
 * Zoom & Viewport Configuration
 * Controls zoom levels and initial viewport
 */
export const VIEWPORT = {
  MIN_ZOOM: 0.05,          // Minimum zoom level (5%)
  MAX_ZOOM: 1.5,           // Maximum zoom level (150%)
  DEFAULT_ZOOM: 0.5,       // Initial zoom level (50%)

  // Initial viewport position
  DEFAULT_X: 0,
  DEFAULT_Y: 0,
};

/**
 * Default Layout Direction
 * TB = Top to Bottom, LR = Left to Right
 */
export const DEFAULT_DIRECTION = 'TB';

/**
 * LocalStorage Keys
 * Keys for persisting user preferences
 */
export const STORAGE_KEYS = {
  LAYOUT_DIRECTION: 'tree_layout_direction',
  USE_AUTO_LAYOUT: 'tree_use_auto_layout',
  FILTER_MODE: 'tree_filter_mode',
  SHOW_HIDDEN_NODES: 'tree_show_hidden_nodes',
  AUTO_CONNECT_ENABLED: 'tree_auto_connect_enabled',
  EDGE_STYLE: 'tree_edge_style',
};

/**
 * Edge Style Options
 */
export const EDGE_STYLES = {
  SMOOTH_STEP: 'smoothstep',
  STRAIGHT: 'straight',
  BEZIER: 'default',
};

/**
 * Filter Modes
 */
export const FILTER_MODES = {
  ALL: 'all',
  SUBDOMAIN_ONLY: 'subdomain',
  CUSTOM: 'custom',
};

export default {
  NODE_LAYOUT,
  INTERACTION,
  VIEWPORT,
  DEFAULT_DIRECTION,
  STORAGE_KEYS,
  EDGE_STYLES,
  FILTER_MODES,
};
