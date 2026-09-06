import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { fetchPayments } from '../api/portal';
import { formatCurrency, formatDate } from '../utils/format';
import PageHeader from '../components/PageHeader';
import { SkeletonTable } from '../components/Skeleton';
import { ErrorState } from '../components/States';
import { EmptyState } from '../components/States';

export function PaymentsPage() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPayments();
      setPayments(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const totalConfirmed = payments.filter((p) => p.status === 'Confirmed').reduce((s, p) => s + p.amount, 0);

  return (
    <div>
      <PageHeader title="Payments" subtitle="View your payment history and receipts" />

      {/* Summary */}
      <div className="dashboard-grid" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="dashboard-card">
          <span className="dashboard-card__label">Total Payments</span>
          <span className="dashboard-card__value">{payments.length}</span>
        </div>
        <div className="dashboard-card">
          <span className="dashboard-card__label">Total Confirmed</span>
          <span className="dashboard-card__value" style={{ color: 'var(--color-success)' }}>KES {formatCurrency(totalConfirmed)}</span>
        </div>
      </div>

      {loading && <SkeletonTable rows={5} cols={5} />}
      {error && <ErrorState detail={error} onRetry={load} />}
      {!loading && !error && payments.length === 0 && (
        <EmptyState title="No payments yet" body="Your payment history will appear here once payments are made." />
      )}
      {!loading && !error && payments.length > 0 && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Reference</th>
                <th>Description</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Receipt</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((p) => (
                <tr key={p.id}>
                  <td className="cell-nowrap">{formatDate(p.date)}</td>
                  <td className="cell-monospace">{p.reference}</td>
                  <td className="cell-secondary">{p.description}</td>
                  <td style={{ fontWeight: 500, fontVariantNumeric: 'tabular-nums' }}>KES {formatCurrency(p.amount)}</td>
                  <td>
                    <span className={`badge badge--${p.status === 'Confirmed' ? 'success' : 'warning'}`}>
                      {p.status}
                    </span>
                  </td>
                  <td>
                    {p.has_receipt ? (
                      <Link to={`/payments/${p.id}`} className="btn btn--ghost btn--sm">View</Link>
                    ) : (
                      <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>N/A</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default PaymentsPage;
