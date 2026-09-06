import { get, post, patch } from './client';

const PORTAL_BASE = '/api/portal';

const portalGet = (path, opts) => get(path, { ...opts, portal: true });
const portalPost = (path, body, opts) => post(path, body, { ...opts, portal: true });
const portalPatch = (path, body, opts) => patch(path, body, { ...opts, portal: true });

export async function portalLogin(email, accountNumber, password) {
  const data = await portalPost(`${PORTAL_BASE}/auth/login`, { email, account_number: accountNumber, password });
  return {
    token: data.token,
    expiresIn: data.expires_in,
    mustChangePassword: data.must_change_password,
    portalUser: data.portal_user,
  };
}

export async function portalLogout() {
  try {
    await portalPost(`${PORTAL_BASE}/auth/logout`);
  } catch {
    // Even if the token is already invalid we clear the local session.
  }
}

export async function portalMe() {
  return portalGet(`${PORTAL_BASE}/me`);
}

export async function portalChangePassword(currentPassword, newPassword) {
  return portalPost(`${PORTAL_BASE}/auth/change-password`, { current_password: currentPassword, new_password: newPassword });
}

export async function portalSetupPassword(password) {
  return portalPost(`${PORTAL_BASE}/auth/setup-password`, { password });
}

export async function portalForgotPassword(email, accountNumber) {
  return portalPost(`${PORTAL_BASE}/auth/forgot-password`, { email, account_number: accountNumber });
}

export async function portalResetPassword(token, newPassword) {
  return portalPost(`${PORTAL_BASE}/auth/reset-password`, { token, new_password: newPassword });
}

export async function portalListAccounts() {
  return portalGet(`${PORTAL_BASE}/accounts`);
}

export async function portalGetAccount(accountId) {
  return portalGet(`${PORTAL_BASE}/accounts/${accountId}`);
}

export async function portalDashboard() {
  return portalGet(`${PORTAL_BASE}/dashboard`);
}

// Quotes
export async function portalListQuotes(params = {}) {
  const qs = new URLSearchParams();
  if (params.search) qs.set('search', params.search);
  if (params.status) qs.set('status', params.status);
  if (params.quote_type) qs.set('quote_type', params.quote_type);
  if (params.customer_account_id) qs.set('customer_account_id', params.customer_account_id);
  if (params.page) qs.set('page', params.page);
  if (params.page_size) qs.set('page_size', params.page_size);
  const query = qs.toString();
  return portalGet(`${PORTAL_BASE}/quotes${query ? `?${query}` : ''}`);
}

export async function portalGetQuote(quoteId) {
  return portalGet(`${PORTAL_BASE}/quotes/${quoteId}`);
}

export async function portalGetQuoteDocument(quoteId) {
  return portalGet(`${PORTAL_BASE}/quotes/${quoteId}/document`);
}

export async function portalAcceptQuote(quoteId, payload = {}) {
  return portalPost(`${PORTAL_BASE}/quotes/${quoteId}/accept`, payload);
}

export async function portalDeclineQuote(quoteId, payload = {}) {
  return portalPost(`${PORTAL_BASE}/quotes/${quoteId}/reject`, payload);
}

export async function portalAcknowledgeQuote(quoteId) {
  return portalPost(`${PORTAL_BASE}/quotes/${quoteId}/acknowledge`);
}

export async function portalChangeRequestQuote(quoteId, payload) {
  return portalPost(`${PORTAL_BASE}/quotes/${quoteId}/change-request`, payload);
}

export async function portalGetQuoteEvents(quoteId) {
  return portalGet(`${PORTAL_BASE}/quotes/${quoteId}/events`);
}

// Notifications
export async function portalListNotifications(params = {}) {
  const qs = new URLSearchParams();
  if (params.unread_only) qs.set('unread_only', 'true');
  if (params.customer_id) qs.set('customer_id', params.customer_id);
  const query = qs.toString();
  return portalGet(`${PORTAL_BASE}/notifications${query ? `?${query}` : ''}`);
}

export async function portalMarkNotificationRead(notificationId) {
  return portalPost(`${PORTAL_BASE}/notifications/${notificationId}/read`);
}

export async function portalMarkAllNotificationsRead() {
  return portalPost(`${PORTAL_BASE}/notifications/read-all`);
}
