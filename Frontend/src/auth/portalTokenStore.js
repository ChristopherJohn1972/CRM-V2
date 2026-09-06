const PORTAL_TOKEN_KEY = 'portal_token';
const PORTAL_USER_KEY = 'portal_user';

export function getPortalToken() {
  try {
    return localStorage.getItem(PORTAL_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getPortalUser() {
  try {
    const raw = localStorage.getItem(PORTAL_USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function storePortalSession(token, user) {
  try {
    if (token) localStorage.setItem(PORTAL_TOKEN_KEY, token);
    if (user) localStorage.setItem(PORTAL_USER_KEY, JSON.stringify(user));
  } catch {
    // Storage full or blocked — silently fail.
  }
}

export function clearPortalSession() {
  try {
    localStorage.removeItem(PORTAL_TOKEN_KEY);
    localStorage.removeItem(PORTAL_USER_KEY);
  } catch {
    // Silently fail.
  }
}
