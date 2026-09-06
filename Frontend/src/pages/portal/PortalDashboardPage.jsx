import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { portalDashboard } from '../../api/portal';
import { usePortalAuth } from '../../auth/PortalAuthContext';
import StatusBadge from '../../components/StatusBadge';
import { getQuoteStatusLabel, getQuoteStatusColor, formatQuoteAmount, getExpiryWarning } from '../../utils/quotes';
import { formatDate } from '../../utils/format';

function StatCard({ label, value, variant = 'neutral' }) {
  return (
    <div className={`quote-stat-card quote-stat-card--${variant}`}>
      <div className="quote-stat-card__value">{value}</div>
      <div className="quote-stat-card__label">{label}</div>
    </div>
  );
}

export function PortalDashboardPage() {
  const { user } = usePortalAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await portalDashboard();
      setData(res);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="page-loading">Loading dashboard...</div>;
  if (error) return <div className="form-error-banner" role="alert">{error.message}</div>;
  if (!data) return null;

  const recentQuotes = data.recent_quotes || [];
  const summary = data.summary || {};

  return (
    <div>
      <div className="page-header">
        <div className="page-header__content">
          <h1 className="page-header__title">Welcome, {user?.first_name || 'Client'}</h1>
          <p className="page-header__subtitle">Here's an overview of your account.</p>
        </div>
      </div>

      <div className="quote-stat-grid">
        <StatCard label="Total Quotes" value={summary.total_quotes || 0} />
        <StatCard label="Pending" value={summary.pending || 0} variant="warning" />
        <StatCard label="Sent" value={summary.sent || 0} variant="info" />
        <StatCard label="Accepted" value={summary.accepted || 0} variant="success" />
      </div>

      <div className="form-section">
        <div className="form-section__header">
          <h2 className="form-section__title">Recent Quotes</h2>
          <Link to="/portal/quotes" className="btn btn--secondary btn--sm">View All</Link>
        </div>

        {recentQuotes.length === 0 ? (
          <div className="empty-state">
            <p className="empty-state__title">No quotes yet</p>
            <p className="empty-state__body">Your quotes will appear here once they are shared with you.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Quote #</th>
                  <th>Title</th>
                  <th>Date</th>
                  <th>Valid Until</th>
                  <th>Amount</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {recentQuotes.map((q) => {
                  const expiry = getExpiryWarning(q.valid_until);
                  const colors = getQuoteStatusColor(q.status);
                  return (
                    <tr key={q.quote_id}>
                      <td>
                        <Link className="data-table__accent" to={`/portal/quotes/${q.quote_id}`}>
                          {q.quote_number}
                        </Link>
                      </td>
                      <td style={{ fontWeight: 500 }}>{q.title || q.quote_number}</td>
                      <td className="cell-secondary">{formatDate(q.quote_date)}</td>
                      <td className={`cell-secondary${expiry === 'expiring-soon' ? ' text-warning' : ''}`}>
                        {formatDate(q.valid_until)}
                      </td>
                      <td style={{ fontWeight: 600 }}>{formatQuoteAmount(q.grand_total, q.currency)}</td>
                      <td>
                        <StatusBadge
                          label={getQuoteStatusLabel(q.status)}
                          style={{ background: colors.bg, color: colors.text }}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default PortalDashboardPage;
