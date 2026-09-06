import { formatCurrency, formatDate } from './format';

// ---------------------------------------------------------------------------
// Quote Status
// ---------------------------------------------------------------------------

export const QUOTE_STATUS = {
  DRAFT: 'DRAFT',
  PENDING_APPROVAL: 'PENDING_APPROVAL',
  APPROVED: 'APPROVED',
  SENT: 'SENT',
  VIEWED: 'VIEWED',
  ACCEPTED: 'ACCEPTED',
  REJECTED: 'REJECTED',
  EXPIRED: 'EXPIRED',
  CANCELLED: 'CANCELLED',
};

export const QUOTE_STATUS_LABELS = {
  DRAFT: 'Draft',
  PENDING_APPROVAL: 'Pending Approval',
  APPROVED: 'Approved',
  SENT: 'Sent',
  VIEWED: 'Viewed',
  ACCEPTED: 'Accepted',
  REJECTED: 'Rejected',
  EXPIRED: 'Expired',
  CANCELLED: 'Cancelled',
};

export const QUOTE_STATUS_COLORS = {
  DRAFT: { bg: '#F3F4F6', text: '#374151', dot: '#6B7280' },
  PENDING_APPROVAL: { bg: '#FEF3C7', text: '#92400E', dot: '#F59E0B' },
  APPROVED: { bg: '#DCFCE7', text: '#166534', dot: '#16A34A' },
  SENT: { bg: '#DBEAFE', text: '#1E40AF', dot: '#2563EB' },
  VIEWED: { bg: '#EDE9FE', text: '#5B21B6', dot: '#7C3AED' },
  ACCEPTED: { bg: '#D1FAE5', text: '#065F46', dot: '#059669' },
  REJECTED: { bg: '#FEE2E2', text: '#991B1B', dot: '#DC2626' },
  EXPIRED: { bg: '#FFF7ED', text: '#9A3412', dot: '#EA580C' },
  CANCELLED: { bg: '#F3F4F6', text: '#374151', dot: '#4B5563' },
};

// ---------------------------------------------------------------------------
// Quote Type
// ---------------------------------------------------------------------------

export const QUOTE_TYPE = {
  PRODUCT: 'PRODUCT',
  SERVICE: 'SERVICE',
  PROJECT: 'PROJECT',
};

export const QUOTE_TYPE_LABELS = {
  PRODUCT: 'Product',
  SERVICE: 'Service',
  PROJECT: 'Project',
};

export const QUOTE_TYPE_COLORS = {
  PRODUCT: { bg: '#DBEAFE', text: '#1E40AF', dot: '#2563EB' },
  SERVICE: { bg: '#EDE9FE', text: '#5B21B6', dot: '#7C3AED' },
  PROJECT: { bg: '#CCFBF1', text: '#115E59', dot: '#0F766E' },
};

export function getQuoteTypeColor(type) {
  return QUOTE_TYPE_COLORS[normalizeEnum(type)] || QUOTE_TYPE_COLORS.PRODUCT;
}

export const QUOTE_TYPE_DESCRIPTIONS = {
  PRODUCT: 'Quote physical products, equipment or goods.',
  SERVICE: 'Quote professional, technical or recurring services.',
  PROJECT: 'Quote a larger engagement, project, milestone or custom scope.',
};

export const QUOTE_TYPE_ICONS = {
  PRODUCT: 'box',
  SERVICE: 'briefcase',
  PROJECT: 'folder',
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
// Helpers
// ---------------------------------------------------------------------------

function normalizeEnum(value) {
  if (!value) return '';
  // Handle Python enum repr like "QuoteType.PRODUCT" → "PRODUCT"
  const dotIndex = value.lastIndexOf('.');
  return dotIndex >= 0 ? value.slice(dotIndex + 1) : value;
}

export function getQuoteStatusLabel(status) {
  return QUOTE_STATUS_LABELS[normalizeEnum(status)] || status;
}

export function getQuoteStatusColor(status) {
  return QUOTE_STATUS_COLORS[normalizeEnum(status)] || QUOTE_STATUS_COLORS.DRAFT;
}

export function getQuoteTypeLabel(type) {
  return QUOTE_TYPE_LABELS[normalizeEnum(type)] || type;
}

export function isTerminalStatus(status) {
  const s = normalizeEnum(status);
  return ['ACCEPTED', 'REJECTED', 'EXPIRED', 'CANCELLED'].includes(s);
}

export function canEdit(status) {
  return normalizeEnum(status) === 'DRAFT';
}

export function canSubmitForApproval(status) {
  return normalizeEnum(status) === 'DRAFT';
}

export function canApprove(status) {
  return normalizeEnum(status) === 'PENDING_APPROVAL';
}

export function canSend(status) {
  return normalizeEnum(status) === 'APPROVED';
}

export function canCancel(status) {
  const s = normalizeEnum(status);
  return ['DRAFT', 'PENDING_APPROVAL', 'APPROVED'].includes(s);
}

export function getExpiryWarning(validUntil) {
  if (!validUntil) return null;
  const now = new Date();
  const expiry = new Date(validUntil);
  const diffDays = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return 'expired';
  if (diffDays <= 3) return 'expiring-soon';
  return null;
}

export function formatQuoteAmount(amount, currency = 'KES') {
  return formatCurrency(amount, currency);
}

export function formatQuoteDate(dateStr) {
  return formatDate(dateStr);
}

export function getQuoteSummaryCounts(quotes) {
  const counts = {
    total: quotes.length,
    drafts: 0,
    pendingApproval: 0,
    sent: 0,
    accepted: 0,
    expiringSoon: 0,
  };

  for (const quote of quotes) {
    if (quote.status === 'DRAFT') counts.drafts++;
    if (quote.status === 'PENDING_APPROVAL') counts.pendingApproval++;
    if (quote.status === 'SENT' || quote.status === 'VIEWED') counts.sent++;
    if (quote.status === 'ACCEPTED') counts.accepted++;
    if (getExpiryWarning(quote.valid_until) === 'expiring-soon') counts.expiringSoon++;
  }

  return counts;
}
