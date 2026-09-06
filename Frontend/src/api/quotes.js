import { get, post, patch, del } from './client';

// ---------------------------------------------------------------------------
// Quotes CRUD
// ---------------------------------------------------------------------------

export function listQuotes(params = {}) {
  const qs = new URLSearchParams();
  if (params.search) qs.set('search', params.search);
  if (params.quote_type) qs.set('quote_type', params.quote_type);
  if (params.status) qs.set('status', params.status);
  if (params.customer_id) qs.set('customer_id', params.customer_id);
  if (params.owner_user_id) qs.set('owner_user_id', params.owner_user_id);
  if (params.page) qs.set('page', params.page);
  if (params.page_size) qs.set('page_size', params.page_size);
  const query = qs.toString();
  return get(`/api/quotes${query ? `?${query}` : ''}`);
}

export function getQuote(quoteId) {
  return get(`/api/quotes/${quoteId}`);
}

export function createQuote(payload) {
  return post('/api/quotes', payload);
}

export function updateQuote(quoteId, payload) {
  return patch(`/api/quotes/${quoteId}`, payload);
}

// ---------------------------------------------------------------------------
// Quote Items
// ---------------------------------------------------------------------------

export function addQuoteItem(quoteId, payload) {
  return post(`/api/quotes/${quoteId}/items`, payload);
}

export function updateQuoteItem(quoteId, itemId, payload) {
  return patch(`/api/quotes/${quoteId}/items/${itemId}`, payload);
}

export function removeQuoteItem(quoteId, itemId) {
  return del(`/api/quotes/${quoteId}/items/${itemId}`);
}

// ---------------------------------------------------------------------------
// Calculations
// ---------------------------------------------------------------------------

export function calculateQuote(payload) {
  return post('/api/quotes/calculate', payload);
}

export function recalculateQuote(quoteId) {
  return post(`/api/quotes/${quoteId}/recalculate`);
}

// ---------------------------------------------------------------------------
// Workflow Actions
// ---------------------------------------------------------------------------

export function submitForApproval(quoteId) {
  return post(`/api/quotes/${quoteId}/submit-approval`);
}

export function approveQuote(quoteId, payload = {}) {
  return post(`/api/quotes/${quoteId}/approve`, payload);
}

export function rejectQuote(quoteId, payload = {}) {
  return post(`/api/quotes/${quoteId}/reject`, payload);
}

export function sendQuote(quoteId, payload = {}) {
  return post(`/api/quotes/${quoteId}/send`, payload);
}

export function cancelQuote(quoteId, payload = {}) {
  return post(`/api/quotes/${quoteId}/cancel`, payload);
}

export function deleteQuote(quoteId) {
  return del(`/api/quotes/${quoteId}`);
}

export function duplicateQuote(quoteId) {
  return post(`/api/quotes/${quoteId}/duplicate`);
}

// ---------------------------------------------------------------------------
// Documents / Preview
// ---------------------------------------------------------------------------

export function getQuotePreview(quoteId) {
  return get(`/api/quotes/${quoteId}/preview`);
}

export function generateQuotePdf(quoteId) {
  return post(`/api/quotes/${quoteId}/pdf`);
}

export function getQuoteActivity(quoteId) {
  return get(`/api/quotes/${quoteId}/activity`);
}

export function getQuoteApprovals(quoteId) {
  return get(`/api/quotes/${quoteId}/approvals`);
}

export function getQuoteDocuments(quoteId) {
  return get(`/api/quotes/${quoteId}/documents`);
}

// ---------------------------------------------------------------------------
// Templates
// ---------------------------------------------------------------------------

export function listTemplates(params = {}) {
  const qs = new URLSearchParams();
  if (params.template_type) qs.set('template_type', params.template_type);
  if (params.status) qs.set('status', params.status);
  const query = qs.toString();
  return get(`/api/quote-templates${query ? `?${query}` : ''}`);
}

export function getTemplate(templateId) {
  return get(`/api/quote-templates/${templateId}`);
}

export function createTemplate(payload) {
  return post('/api/quote-templates', payload);
}

export function updateTemplate(templateId, payload) {
  return patch(`/api/quote-templates/${templateId}`, payload);
}

export function activateTemplate(templateId) {
  return post(`/api/quote-templates/${templateId}/activate`);
}

export function deactivateTemplate(templateId) {
  return post(`/api/quote-templates/${templateId}/deactivate`);
}

// ---------------------------------------------------------------------------
// Tax Rules
// ---------------------------------------------------------------------------

export function listTaxRules() {
  return get('/api/tax-rules');
}

export function createTaxRule(payload) {
  return post('/api/tax-rules', payload);
}
