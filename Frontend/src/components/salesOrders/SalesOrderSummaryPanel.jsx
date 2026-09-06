import { formatCurrency } from '../../utils/format';

export function SalesOrderSummaryPanel({
  currency = 'KES',
  subtotal = 0,
  discountAmount = 0,
  taxAmount = 0,
  additionalCharges = 0,
  grandTotal = 0,
  amountPaid = 0,
  balanceDue = 0,
  itemCount = 0,
}) {
  return (
    <div className="quote-summary">
      <h4 className="quote-summary__title">Order Summary</h4>
      <div className="quote-summary__rows">
        <div className="quote-summary__row">
          <span>Items</span>
          <span>{itemCount}</span>
        </div>
        <div className="quote-summary__row">
          <span>Subtotal</span>
          <span>{formatCurrency(subtotal, currency)}</span>
        </div>
        {discountAmount > 0 && (
          <div className="quote-summary__row quote-summary__row--discount">
            <span>Discount</span>
            <span>-{formatCurrency(discountAmount, currency)}</span>
          </div>
        )}
        {taxAmount > 0 && (
          <div className="quote-summary__row">
            <span>Tax</span>
            <span>{formatCurrency(taxAmount, currency)}</span>
          </div>
        )}
        {additionalCharges > 0 && (
          <div className="quote-summary__row">
            <span>Additional Charges</span>
            <span>{formatCurrency(additionalCharges, currency)}</span>
          </div>
        )}
        <div className="quote-summary__row quote-summary__row--total">
          <span>Grand Total</span>
          <span>{formatCurrency(grandTotal, currency)}</span>
        </div>
        <div className="quote-summary__row">
          <span>Amount Paid</span>
          <span style={{ color: 'var(--color-success)' }}>{formatCurrency(amountPaid, currency)}</span>
        </div>
        <div className="quote-summary__row quote-summary__row--balance">
          <span>Balance Due</span>
          <span style={{ color: balanceDue > 0 ? 'var(--color-warning)' : 'var(--color-text-muted)' }}>
            {formatCurrency(balanceDue, currency)}
          </span>
        </div>
      </div>
    </div>
  );
}

export default SalesOrderSummaryPanel;
