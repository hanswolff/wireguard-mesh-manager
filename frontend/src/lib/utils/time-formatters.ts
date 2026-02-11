/**
 * Formats time remaining until expiration
 * @param expiresAt - ISO string date of expiration
 * @returns Formatted time string (e.g., "2h 30m", "5m 30s", "30s")
 */
export function formatTimeRemaining(expiresAt: string | null | undefined): string {
  if (!expiresAt) return '';

  const now = new Date();
  const expires = new Date(expiresAt);
  const diffMs = expires.getTime() - now.getTime();

  if (diffMs <= 0) return 'Expired';

  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);

  if (diffHours > 0) {
    const remainingMinutes = diffMinutes % 60;
    return remainingMinutes > 0 ? `${diffHours}h ${remainingMinutes}m` : `${diffHours}h`;
  }

  if (diffMinutes > 0) {
    const remainingSeconds = diffSeconds % 60;
    return remainingSeconds > 0 ? `${diffMinutes}m ${remainingSeconds}s` : `${diffMinutes}m`;
  }

  return `${diffSeconds}s`;
}

/**
 * Calculates TTL progress as a percentage (0-100)
 * @param expiresAt - ISO string date of expiration
 * @param ttlSeconds - Total TTL in seconds
 * @returns Progress percentage (0-100)
 */
export function calculateTtlProgress(
  expiresAt: string | null | undefined,
  ttlSeconds: number
): number {
  if (!expiresAt || ttlSeconds <= 0) return 0;

  const now = new Date();
  const expires = new Date(expiresAt);
  const diffMs = expires.getTime() - now.getTime();

  if (diffMs <= 0) return 100; // Expired

  const elapsedMs = ttlSeconds * 1000 - diffMs;
  const progress = (elapsedMs / (ttlSeconds * 1000)) * 100;

  return Math.min(Math.max(progress, 0), 100);
}
