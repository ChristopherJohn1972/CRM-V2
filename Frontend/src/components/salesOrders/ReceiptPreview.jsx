import { useState, useEffect } from 'react';
import QRCode from 'qrcode';
import { formatCurrency, formatDate } from '../../utils/format';
import { PAYMENT_METHOD_LABELS } from '../../utils/salesOrders';

function cleanEnum(value) {
  if (!value || typeof value !== 'string') return value;
  const dotIndex = value.lastIndexOf('.');
  return dotIndex >= 0 ? value.slice(dotIndex + 1) : value;
}

function SimpleQR({ value, size = 120 }) {
  const [svg, setSvg] = useState('');

  useEffect(() => {
    if (!value) return;
    QRCode.toString(value, {
      type: 'svg',
      width: size,
      margin: 1,
      color: { dark: '#1a1a1a', light: '#ffffff' },
    }).then(setSvg).catch(() => setSvg(''));
  }, [value, size]);

  if (!svg) {
    return (
      <div className="receipt-qr" style={{ width: size, height: size, background: '#f5f5f5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: '#999' }}>
        QR
      </div>
    );
  }

  return (
    <div className="receipt-qr" dangerouslySetInnerHTML={{ __html: svg }} />
  );
}

export function ReceiptPreview({ receipt, order }) {
  const verificationUrl = receipt.verification_token
    ? `${window.location.origin}/verify/receipt/${receipt.verification_token}`
    : '';

  return (
    <div className="thermal-receipt">
      <div className="thermal-receipt__inner">
        {/* Header */}
        <div className="thermal-receipt__header">
          <img src="/curl-stack-logo.jpg" alt="Curl Stack" className="thermal-receipt__logo" />
        </div>

        {/* Receipt title */}
        <div className="thermal-receipt__title">SALES RECEIPT</div>

        {/* Receipt info */}
        <div className="thermal-receipt__info">
          <div className="thermal-receipt__info-row">
            <span>Receipt No.</span>
            <span className="thermal-receipt__info-value">{receipt.receipt_number}</span>
          </div>
          <div className="thermal-receipt__info-row">
            <span>Order</span>
            <span className="thermal-receipt__info-value">{order?.order_number || '—'}</span>
          </div>
        </div>

        <div className="thermal-receipt__divider" />

        {/* Customer */}
        <div className="thermal-receipt__section">
          <div className="thermal-receipt__label">Customer</div>
          <div className="thermal-receipt__value">{order?.customer_name || `Customer #${order?.customer_id}`}</div>
        </div>

        {/* Payment info */}
        <div className="thermal-receipt__info">
          <div className="thermal-receipt__info-row">
            <span>Date</span>
            <span>{formatDate(receipt.issued_at)}</span>
          </div>
          <div className="thermal-receipt__info-row">
            <span>Payment</span>
            <span>{PAYMENT_METHOD_LABELS[cleanEnum(receipt.payment_method)] || cleanEnum(receipt.payment_method)}</span>
          </div>
          {receipt.payment_reference && (
            <div className="thermal-receipt__info-row">
              <span>Reference</span>
              <span>{receipt.payment_reference}</span>
            </div>
          )}
        </div>

        <div className="thermal-receipt__divider" />

        {/* Items */}
        <div className="thermal-receipt__items">
          {(order?.items || []).map((item, idx) => (
            <div key={idx} className="thermal-receipt__item">
              <span className="thermal-receipt__item-desc">{item.description}</span>
              <span className="thermal-receipt__item-amount">{formatCurrency(item.line_total, receipt.currency)}</span>
            </div>
          ))}
        </div>

        <div className="thermal-receipt__divider" />

        {/* Totals */}
        <div className="thermal-receipt__totals">
          <div className="thermal-receipt__total-row">
            <span>Subtotal</span>
            <span>{formatCurrency(order?.subtotal, receipt.currency)}</span>
          </div>
          {order?.discount_amount > 0 && (
            <div className="thermal-receipt__total-row">
              <span>Discount</span>
              <span>-{formatCurrency(order.discount_amount, receipt.currency)}</span>
            </div>
          )}
          {order?.tax_amount > 0 && (
            <div className="thermal-receipt__total-row">
              <span>Tax</span>
              <span>{formatCurrency(order.tax_amount, receipt.currency)}</span>
            </div>
          )}
        </div>

        <div className="thermal-receipt__divider thermal-receipt__divider--thick" />

        <div className="thermal-receipt__grand-total">
          <span>TOTAL</span>
          <span>{formatCurrency(receipt.amount, receipt.currency)}</span>
        </div>

        <div className="thermal-receipt__divider thermal-receipt__divider--thick" />

        {/* QR Code */}
        {verificationUrl && (
          <div className="thermal-receipt__qr-section">
            <SimpleQR value={verificationUrl} size={100} />
            <div className="thermal-receipt__qr-text">Scan to verify receipt</div>
          </div>
        )}

        {/* Footer */}
        <div className="thermal-receipt__footer">
          <div>Thank you for your business</div>
          <div className="thermal-receipt__footer-url">{verificationUrl}</div>
        </div>
      </div>
    </div>
  );
}

export default ReceiptPreview;
