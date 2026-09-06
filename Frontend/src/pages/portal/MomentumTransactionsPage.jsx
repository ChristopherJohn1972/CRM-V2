import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { getMomentumLedger } from '../../api/momentum';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import Pagination from '../../components/Pagination';
import { formatDate } from '../../utils/format';

function cleanEnum(value) {
  if (!value) return '';
  return value
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const TYPE_LABELS = {
  PURCHASE: 'Purchase reward',
  REFERRAL: 'Referral reward',
  REVERSAL: 'Reversal',
  MANUAL: 'Manual adjustment',
  REDEMPTION: 'Redemption',
  BONUS: 'Bonus',
  SIGNUP: 'Sign-up bonus',
};

function typeLabel(raw) {
  if (!raw) return 'Transaction';
  return TYPE_LABELS[raw] || cleanEnum(raw);
}

function StatusChip({ status }) {
  const map = {
    PENDING: { label: 'Pending', variant: 'warning' },
    CONFIRMED: { label: 'Confirmed', variant: 'success' },
    CANCELLED: { label: 'Cancelled', variant: 'danger' },
    REVERSED: { label: 'Reversed', variant: 'danger' },
  };
  const cfg = map[status] || { label: cleanEnum(status) || 'Unknown', variant: 'neutral' };
  return <span className={`badge badge--${cfg.variant}`}>{cfg.label}</span>;
}

function PointsBadge({ points }) {
  const isPositive = points > 0;
  return (
    <span className={`points-badge points-badge--${isPositive ? 'earn' : 'redeem'}`}>
      {isPositive ? '+' : ''}{points}
    </span>
  );
}

function StatCard({ label, value, variant = 'neutral' }) {
  return (
    <div className={`quote-stat-card quote-stat-card--${variant}`}>
      <div className="quote-stat-card__value">{value}</div>
      <div className="quote-stat-card__label">{label}</div>
    </div>
  );
}

export default function MomentumTransactionsPage() {
  const [data, setData] = useState({ count: 0, results: [] });
  const [summary, setSummary] = useState({ total_earned: 0, total_redeemed: 0, pending: 0 });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const abortRef = useRef(null);

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const res = await getMomentumLedger(undefined, { page, page_size: pageSize });
      setData(res);
      setSummary({
        total_earned: res.total_earned ?? 0,
        total_redeemed: res.total_redeemed ?? 0,
        pending: res.pending ?? 0,
      });
    } catch (err) {
      if (err.name !== 'AbortError') setError(err);
    } finally {
      if (!abortRef.current || abortRef.current.signal === controller.signal) setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    load();
    return () => abortRef.current?.abort();
  }, [load]);

  const resetPage = (updater) => {
    setPage(1);
    updater();
  };

  return (
    <div className="portal-page">
      <PageHeader
        title="Momentum Transactions"
        subtitle="Your complete Momentum points history"
        actions={
          <Link to="/portal/momentum" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
            &larr; Back to Wallet
          </Link>
        }
      />

      <div className="quote-stat-grid">
        <StatCard label="Total Earned" value={summary.total_earned} variant="success" />
        <StatCard label="Total Redeemed" value={summary.total_redeemed} variant="info" />
        <StatCard label="Pending" value={summary.pending} variant="warning" />
      </div>

      {error ? (
        <ErrorState title="Could not load transactions" body={error.message} onRetry={load} />
      ) : loading && data.results.length === 0 ? (
        <div className="table-wrap">
          <table className="data-table">
            <tbody>
              <tr><td colSpan={5} className="cell-secondary">Loading transactions...</td></tr>
            </tbody>
          </table>
        </div>
      ) : data.results.length === 0 ? (
        <EmptyState
          title="No transactions yet"
          body="Your Momentum points activity will appear here once you start earning."
        />
      ) : (
        <>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Points</th>
                  <th>Status</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((entry) => (
                  <tr key={entry.id}>
                    <td className="cell-secondary cell-nowrap">{formatDate(entry.created_at)}</td>
                    <td>{typeLabel(entry.event_type)}</td>
                    <td><PointsBadge points={entry.points} /></td>
                    <td><StatusChip status={entry.status} /></td>
                    <td className="cell-secondary">{entry.description || '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: 16 }}>
            <Pagination
              page={page}
              pageSize={pageSize}
              count={data.count}
              onPageChange={setPage}
              pageSizeOptions={[10, 20, 50]}
              onPageSizeChange={(n) => resetPage(() => setPageSize(n))}
            />
          </div>
        </>
      )}
    </div>
  );
}
