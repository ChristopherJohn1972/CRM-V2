const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, { status = 0, fieldErrors = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

function normalizeError(payload, status) {
  if (!payload || typeof payload !== 'object') {
    return { message: 'Request failed. Please try again.', fieldErrors: null };
  }
  if (typeof payload.detail === 'string') {
    return { message: payload.detail, fieldErrors: null };
  }
  if (payload.field_errors && typeof payload.field_errors === 'object') {
    return { message: payload.detail || 'Please correct the highlighted fields.', fieldErrors: payload.field_errors };
  }
  const fieldErrors = {};
  let firstMessage = null;
  for (const [field, errors] of Object.entries(payload)) {
    if (Array.isArray(errors) && errors.length > 0) {
      fieldErrors[field] = errors.join(' ');
      if (!firstMessage) firstMessage = `${field}: ${errors.join(' ')}`;
    }
  }
  return { message: firstMessage || 'Something went wrong.', fieldErrors };
}

export async function apiRequest(path, { method = 'GET', body, headers = {} } = {}) {
  const token = localStorage.getItem('portal_token');
  const init = { method, headers: { ...headers } };
  if (token) init.headers.Authorization = `Bearer ${token}`;

  if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError('Could not reach the server. Check your connection and try again.', { status: 0 });
  }

  const contentType = res.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await res.json() : null;

  if (res.status === 401) {
    localStorage.removeItem('portal_token');
    localStorage.removeItem('portal_user');
    window.location.href = '/login';
    throw new ApiError('Session expired.', { status: 401 });
  }

  if (!res.ok) {
    const { message, fieldErrors } = normalizeError(data, res.status);
    throw new ApiError(message, { status: res.status, fieldErrors });
  }

  if (res.status === 204 || data === null) return null;
  return data;
}

export const get = (path) => apiRequest(path);
export const post = (path, body) => apiRequest(path, { method: 'POST', body });

// Portal Auth
export const portalLogin = (email, password) => post('/api/portal/auth/login', { email, password });
export const portalLogout = () => post('/api/portal/auth/logout');
export const portalMe = () => get('/api/portal/me');

// Portal Quotes
export const listPortalQuotes = () => get('/api/portal/quotes');
export const getPortalQuote = (id) => get(`/api/portal/quotes/${id}`);
export const getPortalQuoteDocument = (id) => get(`/api/portal/quotes/${id}/document`);
export const acceptQuote = (id, comment) => post(`/api/portal/quotes/${id}/accept`, { comment });
export const declineQuote = (id, comment) => post(`/api/portal/quotes/${id}/reject`, { comment });
export const acknowledgeQuote = (id, comment) => post(`/api/portal/quotes/${id}/acknowledge`, { comment });
export const requestChanges = (id, comment) => post(`/api/portal/quotes/${id}/change-request`, { comment });
export const getPortalQuoteEvents = (id) => get(`/api/portal/quotes/${id}/events`);
