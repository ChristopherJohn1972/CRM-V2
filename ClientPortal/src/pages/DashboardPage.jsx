import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { fetchDashboard } from '../api/portal';
import { formatCurrency, formatDate } from '../utils/format';
import { SkeletonCards } from '../components/Skeleton';
import { ErrorState } from '../components/States';

export function DashboardPage() {
  const { user, hasPermission } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const d = await fetchDashboard();
      setData(d);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <SkeletonCards />;
  if (error) return <ErrorState detail={error} onRetry={load} />;
  if (!data) return null;

  return (
    <div>
      {/* Welcome */}
      <div style={{ marginBottom: 'var(--space-6)' }}>
        <h1 style={{ fontSize: 'var(--text-2xl)', fontWeight: 600 }}>
          Welcome, {data.customer_name}
        </h1>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-sm)', marginTop: 'var(--space-1)' }}>
          Account Number: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-primary)' }}>{data.account_number}</span>
          {' '}&bull;{' '}
          Status: <span className={`badge badge--${data.account_status === 'Active' ? 'success' : 'warning'}`}>{data.account_status}</span>
        </p>
      </div>

      {/* Health Strip */}
      <div className="health-strip">
        <div className="health-strip__item">
          <span className={`health-strip__dot health-strip__dot--${data.account_status === 'Active' ? 'green' : 'yellow'}`} />
          <span>Account: {data.account_status}</span>
        </div>
        <div className="health-strip__item">
          <span className={`health-strip__dot health-strip__dot--${data.open_complaints > 0 ? 'yellow' : 'green'}`} />
          <span>Service: {data.open_complaints > 0 ? `${data.open_complaints} open` : 'All clear'}</span>
        </div>
        <div className="health-strip__item">
          <span className="health-strip__dot health-strip__dot--green" />
          <span>Rewards: {data.momentum.balance} Momentum</span>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="dashboard-grid">
        <div className="dashboard-card">
          <span className="dashboard-card__label">Outstanding Balance</span>
          <span className="dashboard-card__value" style={{ color: data.outstanding_balance > 0 ? 'var(--color-danger)' : 'var(--color-success)' }}>
            KES {formatCurrency(data.outstanding_balance)}
          </span>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            as of {formatDate(data.balance_date)}
          </span>
          <div className="dashboard-card__action">
            <Link to="/payments">View Payments</Link>
          </div>
        </div>

        <div className="dashboard-card">
          <span className="dashboard-card__label">Momentum</span>
          <span className="dashboard-card__value" style={{ color: 'var(--color-momentum)' }}>
            {formatCurrency(data.momentum.balance)}
          </span>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            +{data.momentum.earned_this_month} this month
          </span>
          <div className="dashboard-card__action">
            <Link to="/momentum">View Momentum</Link>
          </div>
        </div>

        <div className="dashboard-card">
          <span className="dashboard-card__label">Open Complaints</span>
          <span className="dashboard-card__value">{data.open_complaints}</span>
          <div className="dashboard-card__action">
            <Link to="/complaints">View Complaints</Link>
          </div>
        </div>

        <div className="dashboard-card">
          <span className="dashboard-card__label">Unread Notifications</span>
          <span className="dashboard-card__value">{data.unread_notifications}</span>
          <div className="dashboard-card__action">
            <Link to="/notifications">View Notifications</Link>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="activity-section">
        {/* Recent Payments */}
        <div className="card">
          <div className="card__header">
            <h2 className="card__title">Recent Payments</h2>
            <Link to="/payments" className="btn btn--ghost btn--sm">View All</Link>
          </div>
          <div className="card__body" style={{ padding: 0 }}>
            <div className="list-strip">
              {data.recent_payments.map((p) => (
                <div key={p.id} className="list-strip__item" style={{ padding: 'var(--space-4) var(--space-5)' }}>
                  <div>
                    <div style={{ fontWeight: 500 }}>{formatDate(p.date)}</div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>{p.reference}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 500 }}>KES {formatCurrency(p.amount)}</div>
                    <span className={`badge badge--${p.status === 'Confirmed' ? 'success' : 'warning'}`} style={{ marginTop: 4 }}>
                      {p.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Recent Notifications */}
        <div className="card">
          <div className="card__header">
            <h2 className="card__title">Recent Notifications</h2>
            <Link to="/notifications" className="btn btn--ghost btn--sm">View All</Link>
          </div>
          <div className="card__body" style={{ padding: 0 }}>
            <div className="list-strip">
              {data.recent_notifications.map((n) => (
                <div key={n.id} className={`list-strip__item${n.unread ? ' is-unread' : ''}`} style={{ padding: 'var(--space-4) var(--space-5)', background: n.unread ? 'var(--color-primary-subtle)' : undefined }}>
                  <div>
                    <div style={{ fontWeight: 500, fontSize: 'var(--text-sm)' }}>{n.title}</div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>{n.text}</div>
                  </div>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>{n.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions">
        {hasPermission('VIEW_PAYMENTS') && <Link to="/payments" className="btn btn--primary">Make Payment</Link>}
        {hasPermission('RAISE_COMPLAINT') && <Link to="/complaints" className="btn btn--secondary">Raise Complaint</Link>}
        {hasPermission('VIEW_DOCUMENTS') && <Link to="/documents" className="btn btn--secondary">View Documents</Link>}
        {hasPermission('REDEEM_REWARD') && <Link to="/rewards" className="btn btn--secondary">View Rewards</Link>}
        <Link to="/support" className="btn btn--secondary">Contact Support</Link>
      </div>
    </div>
  );
}

export default DashboardPage;
