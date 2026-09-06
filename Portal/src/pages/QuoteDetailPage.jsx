import { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getPortalQuote, acceptQuote, declineQuote, acknowledgeQuote, requestChanges, getPortalQuoteDocument } from '../api/portal';
import { formatDate, formatCurrency } from '../utils/format';

const STATUS_LABELS = {
  SENT: 'Awaiting your response',
  VIEWED: 'Viewed',
  ACCEPTED: 'Accepted',
  REJECTED: 'Declined',
  EXPIRED: 'Expired',
};

function ConfirmDialog({ open, title, children, onConfirm, onCancel, confirmLabel = 'Confirm', variant = 'primary' }) {
  if (!open) return null;
  return (
    <div className="portal-modal-overlay" onClick={onCancel}>
      <div className="portal-modal" onClick={(e) => e.stopPropagation()}>
        <h3>{title}</h3>
        <div className="portal-modal__body">{children}</div>
        <div className="portal-modal__footer">
          <button type="button" className="portal-btn portal-btn--ghost" onClick={onCancel}>Cancel</button>
          <button type="button" className={`portal-btn portal-btn--${variant}`} onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}

export function QuoteDetailPage() {
  const { quoteId } = useParams();
  const [quote, setQuote] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [dialog, setDialog] = useState(null); // 'accept' | 'decline' | 'acknowledge' | 'changes'
  const [comment, setComment] = useState('');
  const [success, setSuccess] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPortalQuote(quoteId);
      setQuote(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [quoteId]);

  useEffect(() => { load(); }, [load]);

  const handleAction = async (action) => {
    setActionLoading(true);
    try {
      switch (action) {
        case 'accept':
          await acceptQuote(quoteId, comment || undefined);
          setSuccess('Quote accepted successfully.');
          break;
        case 'decline':
          await declineQuote(quoteId, comment || undefined);
          setSuccess('Quote declined.');
          break;
        case 'acknowledge':
          await acknowledgeQuote(quoteId, comment || undefined);
          setSuccess('Quote acknowledged.');
          break;
        case 'changes':
          if (!comment.trim()) {
            alert('Please describe the changes you want.');
            setActionLoading(false);
            return;
          }
          await requestChanges(quoteId, comment);
          setSuccess('Change request submitted. Our team will review and respond.');
          break;
      }
      setDialog(null);
      setComment('');
      load();
    } catch (err) {
      alert(err.message || 'Action failed. Please try again.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDownload = async () => {
    try {
      const doc = await getPortalQuoteDocument(quoteId);
      alert(`Document available: ${doc.file_name}\n\nPDF download will be available once the document worker processes it.`);
    } catch (err) {
      alert(err.message || 'No document available for this quote.');
    }
  };

  if (loading) return <div className="portal-loading">Loading quote...</div>;
  if (error) return (
    <div className="portal-page">
      <div className="portal-alert portal-alert--error">{error.message}</div>
      <Link to="/quotes" className="portal-btn portal-btn--ghost">← Back to Quotes</Link>
    </div>
  );
  if (!quote) return null;

  const isExpired = quote.status === 'EXPIRED';
  const isTerminal = ['ACCEPTED', 'REJECTED', 'EXPIRED'].includes(quote.status);
  const canRespond = ['SENT', 'VIEWED'].includes(quote.status) && !isExpired;

  return (
    <div className="portal-page">
      <Link to="/quotes" className="portal-back-link">← Back to Quotes</Link>

      {success && (
        <div className="portal-alert portal-alert--success">
          {success}
          <button onClick={() => setSuccess(null)}>Dismiss</button>
        </div>
      )}

      <div className="portal-quote-detail">
        <div className="portal-quote-detail__header">
          <div>
            <h1>{quote.title || `${quote.quote_type} Quote`}</h1>
            <div className="portal-quote-detail__meta">
              <span className="portal-quote-detail__number">{quote.quote_number}</span>
              <span className="portal-quote-detail__status">{STATUS_LABELS[quote.status] || quote.status}</span>
            </div>
          </div>
          <div className="portal-quote-detail__dates">
            <div>Issued: {formatDate(quote.quote_date)}</div>
            {quote.valid_until && <div>Valid until: {formatDate(quote.valid_until)}</div>}
          </div>
        </div>

        {isExpired && (
          <div className="portal-alert portal-alert--warning">
            This quotation has expired and is no longer available for acceptance.
          </div>
        )}

        {/* Items Table */}
        <div className="portal-quote-items">
          <table className="portal-table">
            <thead>
              <tr>
                <th>Description</th>
                <th style={{ textAlign: 'right' }}>Qty</th>
                <th style={{ textAlign: 'right' }}>Price</th>
                <th style={{ textAlign: 'right' }}>Total</th>
              </tr>
            </thead>
            <tbody>
              {(quote.items || []).map((item) => (
                <tr key={item.item_id}>
                  <td>{item.description}</td>
                  <td style={{ textAlign: 'right' }}>{item.quantity}</td>
                  <td style={{ textAlign: 'right' }}>{formatCurrency(item.unit_price, quote.currency)}</td>
                  <td style={{ textAlign: 'right', fontWeight: 600 }}>{formatCurrency(item.line_total, quote.currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Totals */}
        <div className="portal-quote-totals">
          <div className="portal-quote-totals__row">
            <span>Subtotal</span>
            <span>{formatCurrency(quote.subtotal, quote.currency)}</span>
          </div>
          {quote.discount_amount > 0 && (
            <div className="portal-quote-totals__row portal-quote-totals__row--discount">
              <span>Discount</span>
              <span>− {formatCurrency(quote.discount_amount, quote.currency)}</span>
            </div>
          )}
          {quote.tax_amount > 0 && (
            <div className="portal-quote-totals__row">
              <span>Tax</span>
              <span>+ {formatCurrency(quote.tax_amount, quote.currency)}</span>
            </div>
          )}
          <div className="portal-quote-totals__row portal-quote-totals__row--total">
            <span>Total</span>
            <span>{formatCurrency(quote.grand_total, quote.currency)}</span>
          </div>
        </div>

        {/* Terms */}
        {quote.terms_and_conditions && (
          <div className="portal-quote-terms">
            <h3>Terms & Conditions</h3>
            <p>{quote.terms_and_conditions}</p>
          </div>
        )}

        {/* Notes */}
        {quote.notes && (
          <div className="portal-quote-notes">
            <h3>Notes</h3>
            <p>{quote.notes}</p>
          </div>
        )}

        {/* Actions */}
        <div className="portal-quote-actions">
          <button type="button" className="portal-btn portal-btn--secondary" onClick={handleDownload}>
            Download Quote
          </button>

          {canRespond && (
            <>
              <button type="button" className="portal-btn portal-btn--ghost" onClick={() => setDialog('acknowledge')}>
                Acknowledge
              </button>
              <button type="button" className="portal-btn portal-btn--primary" onClick={() => setDialog('accept')}>
                Accept Quote
              </button>
              <button type="button" className="portal-btn portal-btn--secondary" onClick={() => setDialog('changes')}>
                Request Changes
              </button>
              <button type="button" className="portal-btn portal-btn--danger" onClick={() => setDialog('decline')}>
                Decline
              </button>
            </>
          )}
        </div>
      </div>

      {/* Dialogs */}
      <ConfirmDialog
        open={dialog === 'acknowledge'}
        title="Acknowledge Quote"
        onConfirm={() => handleAction('acknowledge')}
        onCancel={() => { setDialog(null); setComment(''); }}
        confirmLabel="Acknowledge"
      >
        <p>You are confirming that you have received and reviewed this quotation.</p>
        <p>Acknowledging a quote does not mean you have accepted it.</p>
      </ConfirmDialog>

      <ConfirmDialog
        open={dialog === 'accept'}
        title="Accept Quote"
        onConfirm={() => handleAction('accept')}
        onCancel={() => { setDialog(null); setComment(''); }}
        confirmLabel="Accept Quote"
      >
        <p>You are about to accept:</p>
        <p><strong>{quote.quote_number}</strong> — Total: {formatCurrency(quote.grand_total, quote.currency)}</p>
        {quote.valid_until && <p>Valid until: {formatDate(quote.valid_until)}</p>}
      </ConfirmDialog>

      <ConfirmDialog
        open={dialog === 'decline'}
        title="Decline Quote"
        onConfirm={() => handleAction('decline')}
        onCancel={() => { setDialog(null); setComment(''); }}
        confirmLabel="Decline"
        variant="danger"
      >
        <p>Are you sure you want to decline this quotation?</p>
        <div className="portal-field">
          <label htmlFor="decline-comment">Reason (optional)</label>
          <textarea id="decline-comment" className="portal-input" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Optional reason..." />
        </div>
      </ConfirmDialog>

      <ConfirmDialog
        open={dialog === 'changes'}
        title="Request Changes"
        onConfirm={() => handleAction('changes')}
        onCancel={() => { setDialog(null); setComment(''); }}
        confirmLabel="Send Request"
      >
        <p>What would you like us to change or clarify?</p>
        <div className="portal-field">
          <label htmlFor="changes-comment">Details</label>
          <textarea id="changes-comment" className="portal-input" rows={4} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Describe the changes you need..." />
        </div>
      </ConfirmDialog>
    </div>
  );
}

export default QuoteDetailPage;
