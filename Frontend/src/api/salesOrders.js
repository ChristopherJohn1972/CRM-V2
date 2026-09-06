import { get, post, patch, del } from './client';

// ---------------------------------------------------------------------------
// Sales Orders CRUD
// ---------------------------------------------------------------------------

export function listSalesOrders(params = {}) {
  const qs = new URLSearchParams();
  if (params.search) qs.set('search', params.search);
  if (params.status) qs.set('status', params.status);
  if (params.customer_id) qs.set('customer_id', params.customer_id);
  if (params.source) qs.set('source', params.source);
  if (params.page) qs.set('page', params.page);
  if (params.page_size) qs.set('page_size', params.page_size);
  const query = qs.toString();
  return get(`/api/sales-orders/${query ? `?${query}` : ''}`);
}

export function getSalesOrder(orderId) {
  return get(`/api/sales-orders/${orderId}/`);
}

export function createSalesOrder(payload) {
  return post('/api/sales-orders/', payload);
}

export function updateSalesOrder(orderId, payload) {
  return patch(`/api/sales-orders/${orderId}/`, payload);
}

export function deleteSalesOrder(orderId) {
  return del(`/api/sales-orders/${orderId}/`);
}

// ---------------------------------------------------------------------------
// Sales Order Items
// ---------------------------------------------------------------------------

export function addSalesOrderItem(orderId, payload) {
  return post(`/api/sales-orders/${orderId}/items/`, payload);
}

export function updateSalesOrderItem(orderId, itemId, payload) {
  return patch(`/api/sales-orders/${orderId}/items/${itemId}/`, payload);
}

export function removeSalesOrderItem(orderId, itemId) {
  return del(`/api/sales-orders/${orderId}/items/${itemId}/`);
}

// ---------------------------------------------------------------------------
// Calculations
// ---------------------------------------------------------------------------

export function calculateSalesOrder(payload) {
  return post('/api/sales-orders/calculate/', payload);
}

// ---------------------------------------------------------------------------
// Workflow Actions
// ---------------------------------------------------------------------------

export function confirmSalesOrder(orderId) {
  return post(`/api/sales-orders/${orderId}/confirm/`);
}

export function cancelSalesOrder(orderId, payload = {}) {
  return post(`/api/sales-orders/${orderId}/cancel/`, payload);
}

export function submitForApprovalSO(orderId) {
  return post(`/api/sales-orders/${orderId}/submit-approval/`);
}

export function approveSalesOrder(orderId) {
  return post(`/api/sales-orders/${orderId}/approve/`);
}

export function markProcessingSO(orderId) {
  return post(`/api/sales-orders/${orderId}/processing/`);
}

export function markFulfilledSO(orderId) {
  return post(`/api/sales-orders/${orderId}/fulfilled/`);
}

// ---------------------------------------------------------------------------
// Activity
// ---------------------------------------------------------------------------

export function getSalesOrderActivity(orderId) {
  return get(`/api/sales-orders/${orderId}/activity/`);
}

// ---------------------------------------------------------------------------
// Payments
// ---------------------------------------------------------------------------

export function listPayments(orderId) {
  return get(`/api/sales-orders/${orderId}/payments/`);
}

export function listAllPayments(params = {}) {
  const qs = new URLSearchParams();
  if (params.order_id) qs.set('order_id', params.order_id);
  if (params.customer_id) qs.set('customer_id', params.customer_id);
  if (params.page) qs.set('page', params.page);
  if (params.page_size) qs.set('page_size', params.page_size);
  const query = qs.toString();
  return get(`/api/sales-orders/payments/${query ? `?${query}` : ''}`);
}

export function recordPayment(payload) {
  return post('/api/sales-orders/payments/', payload);
}

export function confirmPayment(paymentId) {
  return post(`/api/sales-orders/payments/${paymentId}/confirm/`);
}

export function reversePayment(paymentId, payload = {}) {
  return post(`/api/sales-orders/payments/${paymentId}/reverse/`, payload);
}

// ---------------------------------------------------------------------------
// Receipts
// ---------------------------------------------------------------------------

export function listReceipts(orderId) {
  return get(`/api/sales-orders/${orderId}/receipts/`);
}

export function getReceipt(receiptId) {
  return get(`/api/sales-orders/receipts/${receiptId}/`);
}

export function voidReceipt(receiptId, payload = {}) {
  return post(`/api/sales-orders/receipts/${receiptId}/void/`, payload);
}

export function getReceiptPdfUrl(receiptId) {
  return `/api/sales-orders/receipts/${receiptId}/pdf/`;
}

export function verifyReceipt(token) {
  return get(`/api/sales-orders/receipts/verify/?token=${encodeURIComponent(token)}`);
}

// ---------------------------------------------------------------------------
// Quote Conversion
// ---------------------------------------------------------------------------

export function convertQuoteToOrder(quoteId) {
  return post(`/api/sales-orders/convert-quote/${quoteId}/`);
}
