/**
 * Color utility functions for UI components.
 */

/**
 * Calculate the appropriate text color (black or white) for a given background color.
 * Uses luminance-based calculation to determine optimal contrast.
 *
 * @param hexColor - Hex color string (e.g., "#FF5733" or "#F53")
 * @returns "#000000" for light backgrounds, "#ffffff" for dark backgrounds
 */
export function getContrastColor(hexColor: string): string {
  if (!hexColor) {
    return '#ffffff';
  }

  const r = parseInt(hexColor.slice(1, 3), 16) || 0;
  const g = parseInt(hexColor.slice(3, 5), 16) || 0;
  const b = parseInt(hexColor.slice(5, 7), 16) || 0;

  // Calculate luminance using standard formula
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

  // Return black for light backgrounds, white for dark backgrounds
  return luminance > 0.5 ? '#000000' : '#ffffff';
}
