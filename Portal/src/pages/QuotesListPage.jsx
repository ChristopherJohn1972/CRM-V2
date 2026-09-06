import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listPortalQuotes } from '../api/portal';
import { usePortalAuth } from '../auth/PortalAuth';
import { formatDate, formatCurrency } from '../utils/format';

const STATUS_LABELS = {
  SENT: 'Awaiting your response',
  VIEWED: 'Viewed',
  ACCEPTED: 'Accepted',
  REJECTED: 'Declined',
  EXPIRED: 'Expired',
};

const STATUS_COLORS = {
  SENT: { bg: '#E0E7FF', text: '#3730A3' },
  VIEWED: { bg: '#EDE9FE', text: '#5B21B6' },
  ACCEPTED: { bg: '#D1FAE5', text: '#065F46' },
  REJECTED: { bg: '#FEE2E2', text: '#991B1B' },
  EXPIRED: { bg: '#F3F4F6', text: '#6B7280' },
};

function QuoteCard({ quote }) {
  const colors = STATUS_COLORS[quote.status] || STATUS_COLORS.SENT;
  return (
    <Link to={`/quotes/${quote.quote_id}`} className="portal-quote-card">
      <div className="portal-quote-card__header">
        <span className="portal-quote-card__number">{quote.quote_number}</span>
        <span
          className="portal-quote-card__status"
          style={{ background: colors.bg, color: colors.text }}
        >
          {STATUS_LABELS[quote.status] || quote.status}
        </span>
      </div>
      <div className="portal-quote-card__title">{quote.title || `${quote.quote_type} Quote`}</div>
      <div className="portal-quote-card__meta">
        <span>{formatDate(quote.quote_date)}</span>
        {quote.valid_until && <span>Valid until {formatDate(quote.valid_until)}</span>}
      </div>
      <div className="portal-quote-card__amount">{formatCurrency(quote.grand_total, quote.currency)}</div>
    </Link>
  );
}

export function QuotesListPage() {
  const { user, logout } = usePortalAuth();
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listPortalQuotes();
      setQuotes(data.results || []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="portal-page">
      <div className="portal-page__header">
        <div>
          <h1 className="portal-page__title">My Quotes</h1>
          <p className="portal-page__subtitle">
            Welcome{user?.first_name ? `, ${user.first_name}` : ''}. View and respond to your quotations.
          </p>
        </div>
        <button type="button" className="portal-btn portal-btn--ghost" onClick={logout}>Sign Out</button>
      </div>

      {error && (
        <div className="portal-alert portal-alert--error">
          Could not load quotes: {error.message}
          <button onClick={load}>Retry</button>
        </div>
      )}

      {loading ? (
        <div className="portal-loading">Loading quotes...</div>
      ) : quotes.length === 0 ? (
        <div className="portal-empty">
          <h3>No quotes yet</h3>
          <p>When a quotation is sent to you, it will appear here.</p>
        </div>
      ) : (
        <div className="portal-quotes-grid">
          {quotes.map((q) => <QuoteCard key={q.quote_id} quote={q} />)}
        </div>
      )}
    </div>
  );
}

export default QuotesListPage;
