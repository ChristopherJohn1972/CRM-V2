import { TOKEN_STORAGE_KEY, getStoredToken, clearStoredSession } from '../auth/tokenStore';
import { getPortalToken, clearPortalSession } from '../auth/portalTokenStore';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, { status = 0, code = null, fieldErrors = null, detail = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.fieldErrors = fieldErrors;
    this.detail = detail;
  }
}

/**
 * Normalize a DRF-style error payload into a message + per-field errors.
 * Backend never sends stack traces; the UI never prints raw internals either.
 */
function normalizeErrorPayload(payload, status) {
  if (!payload || typeof payload !== 'object') {
    return { message: 'Request failed. Please try again.', detail: null, fieldErrors: null };
  }
  // Backend APIError -> { detail, code, field_errors: { field: "msg" } }
  if (payload.field_errors && typeof payload.field_errors === 'object' && !Array.isArray(payload.field_errors)) {
    return {
      message: typeof payload.detail === 'string' && payload.detail !== 'Not found.' ? payload.detail : 'Please correct the highlighted fields.',
      detail: payload.detail || null,
      fieldErrors: payload.field_errors,
    };
  }
  if (typeof payload.detail === 'string' && payload.detail !== 'Not found.') {
    return { message: payload.detail, detail: payload.detail, fieldErrors: null };
  }
  if (typeof payload.message === 'string') {
    return { message: payload.message, detail: payload.detail || null, fieldErrors: null };
  }
  if (Array.isArray(payload.field_errors)) {
    const fieldErrors = {};
    for (const fe of payload.field_errors) {
      fieldErrors[fe.field] = fe.message;
    }
    return { message: 'Please correct the highlighted fields.', detail: null, fieldErrors };
  }
  // DRF validation -> {"field": ["msg"]}
  const nonField = payload.non_field_errors;
  if (nonField && Array.isArray(nonField)) {
    return { message: nonField.join(' '), detail: null, fieldErrors: null };
  }
  const fieldErrors = {};
  let firstMessage = null;
  for (const [field, errors] of Object.entries(payload)) {
    if (Array.isArray(errors) && errors.length > 0) {
      fieldErrors[field] = errors.join(' ');
      if (!firstMessage) firstMessage = `${field}: ${errors.join(' ')}`;
    }
  }
  return {
    message: firstMessage || mapServerStatus(status),
    detail: null,
    fieldErrors,
  };
}

export function mapServerStatus(status) {
  switch (status) {
    case 400:
      return 'The request could not be completed. Check the highlighted fields.';
    case 401:
      return 'Your session has expired. Please sign in again.';
    case 403:
      return 'You do not have permission to perform this action.';
    case 404:
      return 'The requested record could not be found.';
    case 409:
      return 'This record was changed by someone else. Reload and try again.';
    case 422:
      return 'The request could not be validated.';
    case 429:
      return 'Too many requests. Please wait a moment and try again.';
    case 503:
      return 'A required service is temporarily unavailable. Please retry shortly.';
    default:
      return 'Something went wrong. Please try again.';
  }
}

export async function apiRequest(path, { method = 'GET', body, headers = {}, raw = false, portal = false } = {}) {
  const token = portal ? getPortalToken() : getStoredToken();
  const init = { method, headers: { ...headers } };
  if (token) init.headers.Authorization = `Bearer ${token}`;

  let payload;
  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }
  init.body = payload;

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError('Could not reach the server. Check your connection and try again.', { status: 0 });
  }

  const contentType = res.headers.get('content-type') || '';
  const data = contentType.includes('application/json') && !raw ? await res.json() : null;

  if (res.status === 401) {
    if (portal) {
      clearPortalSession();
    } else {
      clearStoredSession();
    }
  }

  if (!res.ok) {
    const { message, detail, fieldErrors } = normalizeErrorPayload(data, res.status);
    throw new ApiError(message, {
      status: res.status,
      code: data && data.code,
      detail,
      fieldErrors,
    });
  }

  if (res.status === 204 || data === null) return null;
  return data;
}

export const get = (path, options) => apiRequest(path, { ...options, method: 'GET' });
export const post = (path, body, options) => apiRequest(path, { ...options, method: 'POST', body });
export const put = (path, body, options) => apiRequest(path, { ...options, method: 'PUT', body });
export const patch = (path, body, options) => apiRequest(path, { ...options, method: 'PATCH', body });
export const del = (path, options) => apiRequest(path, { ...options, method: 'DELETE' });

export default apiRequest;

export { TOKEN_STORAGE_KEY };