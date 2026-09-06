import { formatCurrency, formatDate } from './format';

// ---------------------------------------------------------------------------
// Order Status
// ---------------------------------------------------------------------------

export const ORDER_STATUS = {
  DRAFT: 'DRAFT',
  PENDING_APPROVAL: 'PENDING_APPROVAL',
  APPROVED: 'APPROVED',
  CONFIRMED: 'CONFIRMED',
  PROCESSING: 'PROCESSING',
  FULFILLED: 'FULFILLED',
  CANCELLED: 'CANCELLED',
  ON_HOLD: 'ON_HOLD',
};

export const ORDER_STATUS_LABELS = {
  DRAFT: 'Draft',
  PENDING_APPROVAL: 'Pending Approval',
  APPROVED: 'Approved',
  CONFIRMED: 'Confirmed',
  PROCESSING: 'Processing',
  FULFILLED: 'Fulfilled',
  CANCELLED: 'Cancelled',
  ON_HOLD: 'On Hold',
};

export const ORDER_STATUS_COLORS = {
  DRAFT: { bg: '#F1F5F9', text: '#475569', dot: '#64748B' },
  PENDING_APPROVAL: { bg: '#FEF3C7', text: '#92400E', dot: '#F59E0B' },
  APPROVED: { bg: '#DBEAFE', text: '#1E40AF', dot: '#3B82F6' },
  CONFIRMED: { bg: '#D1FAE5', text: '#065F46', dot: '#10B981' },
  PROCESSING: { bg: '#E0E7FF', text: '#3730A3', dot: '#6366F1' },
  FULFILLED: { bg: '#D1FAE5', text: '#065F46', dot: '#10B981' },
  CANCELLED: { bg: '#F3F4F6', text: '#6B7280', dot: '#9CA3AF' },
  ON_HOLD: { bg: '#FEF3C7', text: '#92400E', dot: '#F59E0B' },
};

// ---------------------------------------------------------------------------
// Order Source
// ---------------------------------------------------------------------------

export const ORDER_SOURCE = {
  DIRECT: 'DIRECT',
  QUOTE: 'QUOTE',
};

export const ORDER_SOURCE_LABELS = {
  DIRECT: 'Direct',
  QUOTE: 'From Quote',
};

// ---------------------------------------------------------------------------
// Payment Method
// ---------------------------------------------------------------------------

export const PAYMENT_METHOD = {
  MPESA: 'MPESA',
  BANK_TRANSFER: 'BANK_TRANSFER',
  CARD: 'CARD',
  CASH: 'CASH',
  CHEQUE: 'CHEQUE',
  OTHER: 'OTHER',
};

export const PAYMENT_METHOD_LABELS = {
  MPESA: 'M-Pesa',
  BANK_TRANSFER: 'Bank Transfer',
  CARD: 'Card',
  CASH: 'Cash',
  CHEQUE: 'Cheque',
  OTHER: 'Other',
};

// ---------------------------------------------------------------------------
// Payment Status
// ---------------------------------------------------------------------------

export const PAYMENT_STATUS = {
  PENDING: 'PENDING',
  CONFIRMED: 'CONFIRMED',
  FAILED: 'FAILED',
  REVERSED: 'REVERSED',
};

export const PAYMENT_STATUS_LABELS = {
  PENDING: 'Pending',
  CONFIRMED: 'Confirmed',
  FAILED: 'Failed',
  REVERSED: 'Reversed',
};

export const PAYMENT_STATUS_COLORS = {
  PENDING: { bg: '#FEF3C7', text: '#92400E', dot: '#F59E0B' },
  CONFIRMED: { bg: '#D1FAE5', text: '#065F46', dot: '#10B981' },
  FAILED: { bg: '#FEE2E2', text: '#991B1B', dot: '#EF4444' },
  REVERSED: { bg: '#F3F4F6', text: '#6B7280', dot: '#9CA3AF' },
};

// ---------------------------------------------------------------------------
// Receipt Status
// ---------------------------------------------------------------------------

export const RECEIPT_STATUS = {
  VALID: 'VALID',
  VOIDED: 'VOIDED',
  REVERSED: 'REVERSED',
};

export const RECEIPT_STATUS_LABELS = {
  VALID: 'Valid',
  VOIDED: 'Voided',
  REVERSED: 'Reversed',
};

export const RECEIPT_STATUS_COLORS = {
  VALID: { bg: '#D1FAE5', text: '#065F46', dot: '#10B981' },
  VOIDED: { bg: '#F3F4F6', text: '#6B7280', dot: '#9CA3AF' },
  REVERSED: { bg: '#FEE2E2', text: '#991B1B', dot: '#EF4444' },
};

// ---------------------------------------------------------------------------
// Discount Type
// ---------------------------------------------------------------------------

export const DISCOUNT_TYPE = {
  PERCENTAGE: 'PERCENTAGE',
  FIXED: 'FIXED',
};

export const DISCOUNT_TYPE_LABELS = {
  PERCENTAGE: '%',
  FIXED: 'Fixed',
};

// ---------------------------------------------------------------------------
// Payment Overall Status (order-level summary)
// ---------------------------------------------------------------------------

export const PAYMENT_OVERALL_STATUS_LABELS = {
  UNPAID: 'Unpaid',
  PARTIALLY_PAID: 'Partially Paid',
  PAID: 'Paid',
  OVERPAID: 'Overpaid',
  REFUNDED: 'Refunded',
};

export const PAYMENT_OVERALL_STATUS_VARIANTS = {
  UNPAID: 'muted',
  PARTIALLY_PAID: 'warning',
  PAID: 'success',
  OVERPAID: 'info',
  REFUNDED: 'muted',
};

export function getPaymentOverallStatusLabel(status) {
  return PAYMENT_OVERALL_STATUS_LABELS[cleanEnum(status)] || cleanEnum(status);
}

export function getPaymentOverallStatusVariant(status) {
  return PAYMENT_OVERALL_STATUS_VARIANTS[cleanEnum(status)] || 'muted';
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function cleanEnum(value) {
  if (!value || typeof value !== 'string') return value;
  const dotIndex = value.lastIndexOf('.');
  return dotIndex >= 0 ? value.slice(dotIndex + 1) : value;
}

export function getOrderStatusLabel(status) {
  return ORDER_STATUS_LABELS[cleanEnum(status)] || cleanEnum(status);
}

export function getOrderStatusColor(status) {
  return ORDER_STATUS_COLORS[cleanEnum(status)] || ORDER_STATUS_COLORS.DRAFT;
}

export function getSourceLabel(source) {
  return ORDER_SOURCE_LABELS[cleanEnum(source)] || cleanEnum(source);
}

export function getPaymentStatusLabel(status) {
  return PAYMENT_STATUS_LABELS[cleanEnum(status)] || cleanEnum(status);
}

export function getPaymentStatusColor(status) {
  return PAYMENT_STATUS_COLORS[cleanEnum(status)] || PAYMENT_STATUS_COLORS.PENDING;
}

export function getReceiptStatusLabel(status) {
  return RECEIPT_STATUS_LABELS[cleanEnum(status)] || cleanEnum(status);
}

export function getReceiptStatusColor(status) {
  return RECEIPT_STATUS_COLORS[cleanEnum(status)] || RECEIPT_STATUS_COLORS.VALID;
}

export function isTerminalOrderStatus(status) {
  return ['FULFILLED', 'CANCELLED'].includes(cleanEnum(status));
}

export function canEditOrder(status) {
  return ['DRAFT'].includes(cleanEnum(status));
}

export function canSubmitForApproval(status) {
  return ['DRAFT'].includes(cleanEnum(status));
}

export function canApproveOrder(status) {
  return ['PENDING_APPROVAL'].includes(cleanEnum(status));
}

export function canConfirmOrder(status) {
  return ['DRAFT', 'APPROVED'].includes(cleanEnum(status));
}

export function canCancelOrder(status) {
  return ['DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'CONFIRMED', 'PROCESSING', 'ON_HOLD'].includes(cleanEnum(status));
}

export function canProcessOrder(status) {
  return ['CONFIRMED'].includes(cleanEnum(status));
}

export function canFulfillOrder(status) {
  return ['PROCESSING'].includes(cleanEnum(status));
}

export function canOnHoldOrder(status) {
  return ['CONFIRMED', 'PROCESSING'].includes(cleanEnum(status));
}

export function formatOrderAmount(amount, currency = 'KES') {
  return formatCurrency(amount, currency);
}

export function formatOrderDate(dateStr) {
  return formatDate(dateStr);
}

export function getOrderSummaryCounts(orders) {
  const counts = {
    total: orders.length,
    drafts: 0,
    confirmed: 0,
    processing: 0,
    fulfilled: 0,
    cancelled: 0,
  };

  for (const order of orders) {
    if (order.status === 'DRAFT') counts.drafts++;
    if (order.status === 'CONFIRMED') counts.confirmed++;
    if (order.status === 'PROCESSING') counts.processing++;
    if (order.status === 'FULFILLED') counts.fulfilled++;
    if (order.status === 'CANCELLED') counts.cancelled++;
  }

  return counts;
}
