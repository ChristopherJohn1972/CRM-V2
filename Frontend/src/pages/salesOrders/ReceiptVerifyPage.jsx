import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { verifyReceipt } from '../../api/salesOrders';
import { formatCurrency, formatDate } from '../../utils/format';
import { PAYMENT_METHOD_LABELS } from '../../utils/salesOrders';

export default function ReceiptVerifyPage() {
  const { token } = useParams();
  const [receipt, setReceipt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await verifyReceipt(token);
        setReceipt(data);
      } catch (err) {
        setError(err.message || 'Receipt not found');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [token]);

  if (loading) {
    return (
      <div className="verify-page">
        <div className="verify-card">
          <div className="verify-loading">Verifying receipt...</div>
        </div>
      </div>
    );
  }

  if (error || !receipt) {
    return (
      <div className="verify-page">
        <div className="verify-card verify-card--invalid">
          <img src="/curl-stack-logo.jpg" alt="Curl Stack" className="verify-logo" />
          <div className="verify-status verify-status--invalid">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <circle cx="24" cy="24" r="22" stroke="#EF4444" strokeWidth="3" fill="#FEE2E2"/>
              <path d="M16 16L32 32M32 16L16 32" stroke="#EF4444" strokeWidth="3" strokeLinecap="round"/>
            </svg>
          </div>
          <h2>Receipt Not Found</h2>
          <p className="verify-message">{error || 'This receipt could not be verified.'}</p>
        </div>
      </div>
    );
  }

  const isValid = receipt.status === 'VALID';
  const isVoided = receipt.status === 'VOIDED';
  const isReversed = receipt.status === 'REVERSED';

  return (
    <div className="verify-page">
      <div className={`verify-card ${isValid ? 'verify-card--valid' : 'verify-card--invalid'}`}>
        <img src="/curl-stack-logo.jpg" alt="Curl Stack" className="verify-logo" />

        <div className={`verify-status ${isValid ? 'verify-status--valid' : 'verify-status--invalid'}`}>
          {isValid ? (
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
              <circle cx="32" cy="32" r="30" stroke="#10B981" strokeWidth="3" fill="#D1FAE5"/>
              <path d="M20 32L28 40L44 24" stroke="#10B981" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          ) : (
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
              <circle cx="32" cy="32" r="30" stroke="#EF4444" strokeWidth="3" fill="#FEE2E2"/>
              <path d="M22 22L42 42M42 22L22 42" stroke="#EF4444" strokeWidth="3" strokeLinecap="round"/>
            </svg>
          )}
        </div>

        <h1 className="verify-title">{isValid ? 'RECEIPT VERIFIED' : `RECEIPT ${receipt.status}`}</h1>

        <div className="verify-details">
          <div className="verify-row">
            <span className="verify-label">Receipt</span>
            <span className="verify-value verify-value--mono">{receipt.receipt_number}</span>
          </div>
          <div className="verify-row">
            <span className="verify-label">Order</span>
            <span className="verify-value verify-value--mono">{receipt.order_number || '—'}</span>
          </div>
          <div className="verify-row">
            <span className="verify-label">Date</span>
            <span className="verify-value">{formatDate(receipt.issued_at)}</span>
          </div>
          <div className="verify-row">
            <span className="verify-label">Payment</span>
            <span className="verify-value">{PAYMENT_METHOD_LABELS[receipt.payment_method] || receipt.payment_method}</span>
          </div>
        </div>

        <div className="verify-amount">
          <div className="verify-amount__label">Amount Paid</div>
          <div className="verify-amount__value">{formatCurrency(receipt.amount, receipt.currency)}</div>
        </div>

        {isVoided && (
          <div className="verify-notice verify-notice--warning">
            This receipt has been voided and is no longer valid.
          </div>
        )}
        {isReversed && (
          <div className="verify-notice verify-notice--warning">
            This receipt has been reversed and is no longer valid.
          </div>
        )}

        <div className="verify-footer">
          <img src="/curl-stack-logo.jpg" alt="Curl Stack" className="verify-footer-logo" />
          <div className="verify-footer-text">Curl Stack — Decoded Simplicity, Scalable Solutions.</div>
        </div>
      </div>
    </div>
  );
}
