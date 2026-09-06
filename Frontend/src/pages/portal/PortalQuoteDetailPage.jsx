import { useCallback, useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { portalGetQuote, portalGetQuoteDocument, portalAcceptQuote, portalDeclineQuote, portalAcknowledgeQuote, portalChangeRequestQuote, portalGetQuoteEvents } from '../../api/portal';
import PageHeader from '../../components/PageHeader';
import Button from '../../components/Button';
import Field from '../../components/Field';
import StatusBadge from '../../components/StatusBadge';
import { useToast } from '../../components/Toast';
import { formatDate } from '../../utils/format';
import { getQuoteStatusLabel, getQuoteStatusColor, getQuoteTypeLabel, getQuoteTypeColor, formatQuoteAmount } from '../../utils/quotes';

function QuoteDocumentView({ document }) {
  if (!document) return <p className="cell-secondary">No document preview available.</p>;

  return (
    <div className="quote-document">
      <div className="quote-document__header">
        <h3>{document.company_name || 'Our Company'}</h3>
        <div className="quote-document__meta">
          <div><strong>Quote:</strong> {document.quote_number}</div>
          <div><strong>Date:</strong> {formatDate(document.quote_date)}</div>
          <div><strong>Valid Until:</strong> {formatDate(document.valid_until)}</div>
        </div>
      </div>

      <div className="quote-document__recipient">
        <strong>Prepared for:</strong>
        <div>{document.customer_name}</div>
        {document.customer_email && <div>{document.customer_email}</div>}
      </div>

      {document.items && document.items.length > 0 && (
        <table className="data-table data-table--compact">
          <thead>
            <tr>
              <th>#</th>
              <th>Description</th>
              <th>Qty</th>
              <th>Unit Price</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            {document.items.map((item, idx) => (
              <tr key={item.item_id || idx}>
                <td>{idx + 1}</td>
                <td>
                  <div style={{ fontWeight: 500 }}>{item.description}</div>
                  {item.sku && <div className="cell-secondary">{item.sku}</div>}
                </td>
                <td>{item.quantity}</td>
                <td>{formatQuoteAmount(item.unit_price, document.currency)}</td>
                <td style={{ fontWeight: 600 }}>{formatQuoteAmount(item.line_total, document.currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="quote-document__totals">
        <div className="quote-document__totals-row">
          <span>Subtotal</span>
          <span>{formatQuoteAmount(document.subtotal, document.currency)}</span>
        </div>
        {document.discount_amount > 0 && (
          <div className="quote-document__totals-row">
            <span>Discount</span>
            <span>-{formatQuoteAmount(document.discount_amount, document.currency)}</span>
          </div>
        )}
        {document.tax_amount > 0 && (
          <div className="quote-document__totals-row">
            <span>Tax</span>
            <span>{formatQuoteAmount(document.tax_amount, document.currency)}</span>
          </div>
        )}
        {document.additional_charges > 0 && (
          <div className="quote-document__totals-row">
            <span>Additional Charges</span>
            <span>{formatQuoteAmount(document.additional_charges, document.currency)}</span>
          </div>
        )}
        <div className="quote-document__totals-row quote-document__totals-row--grand">
          <span>Total</span>
          <span>{formatQuoteAmount(document.grand_total, document.currency)}</span>
        </div>
      </div>

      {document.notes && (
        <div className="quote-document__section">
          <h4>Notes</h4>
          <p>{document.notes}</p>
        </div>
      )}

      {document.terms_and_conditions && (
        <div className="quote-document__section">
          <h4>Terms & Conditions</h4>
          <p>{document.terms_and_conditions}</p>
        </div>
      )}
    </div>
  );
}

export function PortalQuoteDetailPage() {
  const { quoteId } = useParams();
  const navigate = useNavigate();
  const { notify } = useToast();

  const [quote, setQuote] = useState(null);
  const [document, setDocument] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showChangeRequest, setShowChangeRequest] = useState(false);
  const [changeMessage, setChangeMessage] = useState('');
  const [declineReason, setDeclineReason] = useState('');
  const [showDecline, setShowDecline] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [quoteData, docData, eventsData] = await Promise.all([
        portalGetQuote(quoteId),
        portalGetQuoteDocument(quoteId).catch(() => null),
        portalGetQuoteEvents(quoteId).catch(() => []),
      ]);
      setQuote(quoteData);
      setDocument(docData);
      setEvents(eventsData);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [quoteId]);

  useEffect(() => { load(); }, [load]);

  const handleAccept = async () => {
    try {
      const result = await portalAcceptQuote(quoteId);
      setQuote(result);
      notify('Quote accepted', { variant: 'success' });
      load();
    } catch (err) {
      notify('Failed to accept quote', { message: err.message, variant: 'error' });
    }
  };

  const handleDecline = async () => {
    try {
      const result = await portalDeclineQuote(quoteId, { reason: declineReason });
      setQuote(result);
      setShowDecline(false);
      notify('Quote declined', { variant: 'success' });
      load();
    } catch (err) {
      notify('Failed to decline quote', { message: err.message, variant: 'error' });
    }
  };

  const handleAcknowledge = async () => {
    try {
      const result = await portalAcknowledgeQuote(quoteId);
      setQuote(result);
      notify('Quote acknowledged', { variant: 'success' });
      load();
    } catch (err) {
      notify('Failed to acknowledge quote', { message: err.message, variant: 'error' });
    }
  };

  const handleChangeRequest = async () => {
    if (!changeMessage.trim()) return;
    try {
      const result = await portalChangeRequestQuote(quoteId, { message: changeMessage });
      setQuote(result);
      setShowChangeRequest(false);
      setChangeMessage('');
      notify('Change request submitted', { variant: 'success' });
      load();
    } catch (err) {
      notify('Failed to submit change request', { message: err.message, variant: 'error' });
    }
  };

  if (loading) return <div className="page-loading">Loading quote...</div>;
  if (error) return (
    <div>
      <PageHeader title="Quote" subtitle="Could not load quote" />
      <div className="form-error-banner" role="alert">{error.message}</div>
      <Button variant="secondary" onClick={() => navigate('/portal/quotes')}>Back to Quotes</Button>
    </div>
  );
  if (!quote) return null;

  const statusColors = getQuoteStatusColor(quote.status);
  const canRespond = ['SENT', 'VIEWED'].includes(quote.status);

  return (
    <div>
      <PageHeader
        title={quote.title || quote.quote_number}
        subtitle={
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <span className="badge" style={{ background: getQuoteTypeColor(quote.quote_type).bg, color: getQuoteTypeColor(quote.quote_type).text }}>{getQuoteTypeLabel(quote.quote_type)}</span>
            <StatusBadge
              label={getQuoteStatusLabel(quote.status)}
              style={{ background: statusColors.bg, color: statusColors.text }}
            />
          </span>
        }
        actions={
          <Link to="/portal/quotes" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
            &larr; Back to Quotes
          </Link>
        }
      />

      <div className="quote-workspace__layout">
        <div className="quote-workspace__main">
          {/* Quote Info */}
          <div className="form-section">
            <div className="form-section__header">
              <h2 className="form-section__title">Quote Details</h2>
            </div>
            <div className="quote-detail__info">
              <div className="field-display">
                <span className="field-display__label">Quote Number</span>
                <span className="field-display__value">{quote.quote_number}</span>
              </div>
              <div className="field-display">
                <span className="field-display__label">Date</span>
                <span className="field-display__value">{formatDate(quote.quote_date)}</span>
              </div>
              <div className="field-display">
                <span className="field-display__label">Valid Until</span>
                <span className="field-display__value">{formatDate(quote.valid_until)}</span>
              </div>
              <div className="field-display">
                <span className="field-display__label">Currency</span>
                <span className="field-display__value">{quote.currency}</span>
              </div>
            </div>
          </div>

          {/* Document */}
          <div className="form-section">
            <div className="form-section__header">
              <h2 className="form-section__title">Quotation Document</h2>
            </div>
            <QuoteDocumentView document={document} />
          </div>

          {/* Activity */}
          {events.length > 0 && (
            <div className="form-section">
              <div className="form-section__header">
                <h2 className="form-section__title">Activity</h2>
              </div>
              <div className="quote-activity-timeline">
                {events.map((evt, idx) => (
                  <div key={idx} className="timeline-item">
                    <div className="timeline-item__dot" />
                    <div className="timeline-item__content">
                      <div className="timeline-item__text">{evt.description || evt.action}</div>
                      <div className="timeline-item__date">{formatDate(evt.created_at)}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="quote-workspace__sidebar">
          <div className="quote-summary-panel">
            <div className="quote-summary-panel__row">
              <span className="quote-summary-panel__label">Subtotal</span>
              <span className="quote-summary-panel__value">{formatQuoteAmount(quote.subtotal, quote.currency)}</span>
            </div>
            {quote.discount_amount > 0 && (
              <div className="quote-summary-panel__row">
                <span className="quote-summary-panel__label">Discount</span>
                <span className="quote-summary-panel__value quote-summary-panel__value--discount">
                  -{formatQuoteAmount(quote.discount_amount, quote.currency)}
                </span>
              </div>
            )}
            {quote.tax_amount > 0 && (
              <div className="quote-summary-panel__row">
                <span className="quote-summary-panel__label">Tax</span>
                <span className="quote-summary-panel__value">{formatQuoteAmount(quote.tax_amount, quote.currency)}</span>
              </div>
            )}
            {quote.additional_charges > 0 && (
              <div className="quote-summary-panel__row">
                <span className="quote-summary-panel__label">Additional Charges</span>
                <span className="quote-summary-panel__value">{formatQuoteAmount(quote.additional_charges, quote.currency)}</span>
              </div>
            )}
            <div className="quote-summary-panel__row quote-summary-panel__row--total">
              <span className="quote-summary-panel__label">Total</span>
              <span className="quote-summary-panel__value">{formatQuoteAmount(quote.grand_total, quote.currency)}</span>
            </div>
          </div>

          {/* Actions */}
          {canRespond && (
            <div className="quote-detail__actions">
              <Button variant="primary" block onClick={handleAccept}>Accept Quote</Button>
              <Button variant="secondary" block onClick={handleAcknowledge}>Acknowledge</Button>
              <Button variant="secondary" block onClick={() => setShowChangeRequest(true)}>Request Changes</Button>
              <Button variant="danger" block onClick={() => setShowDecline(true)}>Decline</Button>
            </div>
          )}

          {/* Change Request Modal */}
          {showChangeRequest && (
            <div className="form-section">
              <div className="form-section__header">
                <h2 className="form-section__title">Request Changes</h2>
              </div>
              <Field label="Message" htmlFor="change-message">
                <textarea
                  id="change-message"
                  className="field__input field__input--textarea"
                  value={changeMessage}
                  onChange={(e) => setChangeMessage(e.target.value)}
                  rows={4}
                  placeholder="Describe the changes you'd like..."
                />
              </Field>
              <div style={{ display: 'flex', gap: 8 }}>
                <Button variant="primary" size="sm" onClick={handleChangeRequest}>Submit</Button>
                <Button variant="secondary" size="sm" onClick={() => { setShowChangeRequest(false); setChangeMessage(''); }}>Cancel</Button>
              </div>
            </div>
          )}

          {/* Decline Modal */}
          {showDecline && (
            <div className="form-section">
              <div className="form-section__header">
                <h2 className="form-section__title">Decline Quote</h2>
              </div>
              <Field label="Reason (optional)" htmlFor="decline-reason">
                <textarea
                  id="decline-reason"
                  className="field__input field__input--textarea"
                  value={declineReason}
                  onChange={(e) => setDeclineReason(e.target.value)}
                  rows={3}
                  placeholder="Optional reason for declining..."
                />
              </Field>
              <div style={{ display: 'flex', gap: 8 }}>
                <Button variant="danger" size="sm" onClick={handleDecline}>Confirm Decline</Button>
                <Button variant="secondary" size="sm" onClick={() => { setShowDecline(false); setDeclineReason(''); }}>Cancel</Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PortalQuoteDetailPage;
