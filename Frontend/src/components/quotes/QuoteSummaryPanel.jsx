import { formatCurrency } from '../../utils/format';

function SummaryRow({ label, value, variant = 'default', strong = false }) {
  return (
    <div className={`quote-summary__row${strong ? ' quote-summary__row--strong' : ''} quote-summary__row--${variant}`}>
      <span className="quote-summary__label">{label}</span>
      <span className="quote-summary__value">{value}</span>
    </div>
  );
}

export function QuoteSummaryPanel({
  currency = 'KES',
  subtotal = 0,
  discountAmount = 0,
  taxAmount = 0,
  additionalCharges = 0,
  grandTotal = 0,
  itemCount = 0,
  discountType,
  discountValue,
  taxRate,
}) {
  const fmt = (amount) => formatCurrency(amount, currency);

  return (
    <div className="quote-summary">
      <div className="quote-summary__header">
        <h3 className="quote-summary__title">Summary</h3>
        <span className="quote-summary__item-count">{itemCount} {itemCount === 1 ? 'item' : 'items'}</span>
      </div>

      <div className="quote-summary__body">
        <SummaryRow label="Subtotal" value={fmt(subtotal)} />

        {discountAmount > 0 && (
          <SummaryRow
            label={`Discount${discountType === 'PERCENTAGE' && discountValue ? ` (${discountValue}%)` : ''}`}
            value={`− ${fmt(discountAmount)}`}
            variant="discount"
          />
        )}

        {taxAmount > 0 && (
          <SummaryRow
            label={`Tax${taxRate ? ` (${taxRate}%)` : ''}`}
            value={`+ ${fmt(taxAmount)}`}
            variant="tax"
          />
        )}

        {additionalCharges > 0 && (
          <SummaryRow
            label="Additional Charges"
            value={`+ ${fmt(additionalCharges)}`}
            variant="charges"
          />
        )}

        <div className="quote-summary__divider" />

        <SummaryRow label="Grand Total" value={fmt(grandTotal)} strong />
      </div>

      <div className="quote-summary__footer">
        <span className="quote-summary__currency">{currency}</span>
      </div>
    </div>
  );
}

export default QuoteSummaryPanel;
