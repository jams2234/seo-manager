/**
 * Color Utility Functions
 * Shared color helpers for group styling and contrast calculations
 */

// Predefined vibrant colors that are visually distinct
export const GROUP_COLORS = [
  '#EF4444', // Red
  '#F97316', // Orange
  '#F59E0B', // Amber
  '#84CC16', // Lime
  '#22C55E', // Green
  '#14B8A6', // Teal
  '#06B6D4', // Cyan
  '#3B82F6', // Blue
  '#6366F1', // Indigo
  '#8B5CF6', // Violet
  '#A855F7', // Purple
  '#D946EF', // Fuchsia
  '#EC4899', // Pink
  '#F43F5E', // Rose
];

/**
 * Get a random color from the predefined list
 * @returns {string} Hex color code
 */
export const getRandomGroupColor = () => {
  return GROUP_COLORS[Math.floor(Math.random() * GROUP_COLORS.length)];
};

/**
 * Calculate contrasting text color based on background brightness
 * Uses relative luminance formula for accessibility
 * @param {string} hexColor - Background color in hex format (#RRGGBB)
 * @returns {string} '#1F2937' for light backgrounds, '#FFFFFF' for dark
 */
export const getContrastTextColor = (hexColor) => {
  if (!hexColor) return '#FFFFFF';

  const hex = hexColor.replace('#', '');
  const r = parseInt(hex.substr(0, 2), 16);
  const g = parseInt(hex.substr(2, 2), 16);
  const b = parseInt(hex.substr(4, 2), 16);

  // Calculate relative luminance (ITU-R BT.709)
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

  return luminance > 0.5 ? '#1F2937' : '#FFFFFF';
};
