/**
 * Canonical customer-name model. Mirrors the backend Customer.get_display_name():
 * individuals show First Middle Last; businesses show the legal name.
 * The backend read serializer no longer returns `display_name`, so the frontend
 * computes the same value from the returned fields.
 */
export function customerDisplayName(c) {
  if (!c) return '—';
  if (c.customer_type === 'INDIVIDUAL') {
    const parts = [c.first_name, c.middle_name, c.last_name].filter(Boolean);
    return parts.join(' ') || c.legal_name || '—';
  }
  return c.legal_name || [c.first_name, c.last_name].filter(Boolean).join(' ') || '—';
}

export function initialsFor(c) {
  const name = customerDisplayName(c);
  if (!name || name === '—') return '?';
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('');
}