const MASTER_SESSION_TOKEN_KEY = 'wmm.master_session_token';
const CSRF_COOKIE_NAME = 'csrf_token';

export function getMasterSessionToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const sessionToken = window.sessionStorage.getItem(MASTER_SESSION_TOKEN_KEY);
  if (sessionToken) {
    return sessionToken;
  }
  const legacyToken = window.localStorage.getItem(MASTER_SESSION_TOKEN_KEY);
  if (legacyToken) {
    window.sessionStorage.setItem(MASTER_SESSION_TOKEN_KEY, legacyToken);
    window.localStorage.removeItem(MASTER_SESSION_TOKEN_KEY);
    return legacyToken;
  }
  return null;
}

export function setMasterSessionToken(token: string): void {
  if (typeof window === 'undefined') {
    return;
  }
  window.sessionStorage.setItem(MASTER_SESSION_TOKEN_KEY, token);
}

export function clearMasterSessionToken(): void {
  if (typeof window === 'undefined') {
    return;
  }
  window.sessionStorage.removeItem(MASTER_SESSION_TOKEN_KEY);
  window.localStorage.removeItem(MASTER_SESSION_TOKEN_KEY);
}

export function getCsrfToken(): string | null {
  if (typeof document === 'undefined') {
    return null;
  }

  const match = document.cookie.match(
    new RegExp(`(?:^|; )${CSRF_COOKIE_NAME}=([^;]*)`)
  );
  return match ? decodeURIComponent(match[1]) : null;
}

export async function ensureCsrfToken(forceRefresh = false): Promise<void> {
  if (typeof window === 'undefined') {
    return;
  }

  if (!forceRefresh && getCsrfToken()) {
    return;
  }

  await fetch('/api/csrf/token', {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
  });
}
