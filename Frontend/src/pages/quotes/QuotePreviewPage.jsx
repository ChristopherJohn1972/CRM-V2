import { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { getQuote, cancelQuote, generateQuotePdf } from '../../api/quotes';
import { convertQuoteToOrder } from '../../api/salesOrders';
import Button from '../../components/Button';
import QuoteA4Preview from '../../components/quotes/QuoteA4Preview';
import StatusBadge from '../../components/StatusBadge';
import { useToast } from '../../components/Toast';
import { getQuoteStatusLabel, getQuoteStatusColor, getQuoteTypeLabel, getQuoteTypeColor } from '../../utils/quotes';
export function QuotePreviewPage() {
  const { quoteId } = useParams();
  const navigate = useNavigate();
  const { notify } = useToast();
  const { user: staff } = useAuth();
  const [quote, setQuote] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [generating, setGenerating] = useState(false);
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { const data = await getQuote(quoteId); setQuote(data); }
    catch (err) { setError(err); }
    finally { setLoading(false); }
  }, [quoteId]);
  useEffect(() => { load(); }, [load]);
  const handleDelete = async () => {
    if (!window.confirm(`Cancel ${quote.quote_number}? This action cannot be undone.`)) return;
    try { await cancelQuote(quote.quote_id); notify('Quote cancelled', { variant: 'success' }); navigate('/quotes'); }
    catch (err) { notify('Cancel failed', { message: err.message, variant: 'error' }); }
  };
  const handleConvertToOrder = async () => {
    if (!window.confirm(`Convert ${quote.quote_number} to a sales order?`)) return;
    try {
      const result = await convertQuoteToOrder(quote.quote_id);
      notify('Sales order created', { variant: 'success' });
      navigate(`/sales-orders/${result.sales_order_id}`);
    } catch (err) { notify('Conversion failed', { message: err.message, variant: 'error' }); }
  };
  const handleDownload = async () => {
    if (!quote) return;
    setGenerating(true);
    try {
      const result = await generateQuotePdf(quote.quote_id);
      notify('PDF generated', { variant: 'success' });
      if (result.download_url) window.open(result.download_url, '_blank');
    } catch (err) { notify('Download failed', { message: err.message, variant: 'error' }); }
    finally { setGenerating(false); }
  };
  const handlePrint = () => { window.print(); };
  if (loading) return <div className="page-loading">Loading quote...</div>;
  if (error) return (
    <div>
      <div className="form-error-banner" role="alert">{error.message}</div>
      <Button variant="secondary" onClick={() => navigate('/quotes')}>Back to Quotes</Button>
    </div>
  );
  if (!quote) return null;
  const statusColors = getQuoteStatusColor(quote.status);
  return (
    <div className="quote-preview-page">
      <div className="quote-preview-toolbar no-print">
        <Link to="/quotes" className="quote-preview-toolbar__back">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 12L6 8l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
          Back to Quotes
        </Link>
        <div className="quote-preview-toolbar__center">
          <span className="quote-preview-toolbar__number">{quote.quote_number}</span>
          <span className="badge" style={{ background: getQuoteTypeColor(quote.quote_type).bg, color: getQuoteTypeColor(quote.quote_type).text }}>{getQuoteTypeLabel(quote.quote_type)}</span>
          <StatusBadge label={getQuoteStatusLabel(quote.status)} style={{ background: statusColors.bg, color: statusColors.text }} />
        </div>
        <div className="quote-preview-toolbar__actions">
          <Button variant="ghost" size="sm" onClick={handlePrint}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ marginRight: 6 }}><path d="M4 6V1h8v5M4 12H2.667A1.333 1.333 0 011.333 10.667v-4A1.333 1.333 0 012.667 5.333h10.666A1.333 1.333 0 0114.667 6.667v4A1.333 1.333 0 0113.333 12H12M4 9h8v6H4V9z" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>
            Print
          </Button>
          <Button variant="ghost" size="sm" onClick={handleDownload} loading={generating}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ marginRight: 6 }}><path d="M8 1v10M4.5 7.5L8 11l3.5-3.5M2 13h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
            Download PDF
          </Button>
          <Button variant="primary" size="sm" onClick={() => navigate(`/quotes/${quote.quote_id}`)}>Edit Quote</Button>
          {quote.status === 'ACCEPTED' && (
            <Button variant="success" size="sm" onClick={handleConvertToOrder}>Create Sales Order</Button>
          )}
          <button type="button" className="icon-btn icon-btn--delete" title="Cancel quote" onClick={handleDelete}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M5.333 4V2.667a1.333 1.333 0 011.334-1.334h2.666a1.333 1.333 0 011.334 1.334V4m2 0v9.333a1.333 1.333 0 01-1.334 1.334H4.667a1.333 1.333 0 01-1.334-1.334V4h9.334z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
        </div>
      </div>
      <div className="quote-preview-page__document">
        <QuoteA4Preview quote={quote} customer={quote.customer} staff={staff} currency={quote.currency} />
      </div>
    </div>
  );
}
export default QuotePreviewPage;
