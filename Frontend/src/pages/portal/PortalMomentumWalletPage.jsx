import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getMomentumBalance, getMomentumLedger } from '../../api/momentum';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';
import { formatDate } from '../../utils/format';

function cleanEnum(value) {
  if (!value || typeof value !== 'string') return value;
  const dotIndex = value.lastIndexOf('.');
  return dotIndex >= 0 ? value.slice(dotIndex + 1) : value;
}

function PointsBadge({ points }) {
  const isPositive = points > 0;
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 10,
      fontSize: 12, fontWeight: 600,
      background: isPositive ? '#d1fae5' : '#fee2e2',
      color: isPositive ? '#065f46' : '#991b1b',
    }}>
      {isPositive ? '+' : ''}{points}
    </span>
  );
}

export default function PortalMomentumWalletPage() {
  const [balance, setBalance] = useState(null);
  const [ledger, setLedger] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [b, l] = await Promise.all([
          getMomentumBalance().catch(() => null),
          getMomentumLedger().catch(() => ({ results: [] })),
        ]);
        setBalance(b);
        setLedger(l.results || []);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="portal-page"><div className="loading-spinner">Loading...</div></div>;

  const totalEarned = balance?.total_earned ?? 0;
  const totalRedeemed = balance?.total_redeemed ?? 0;
  const pending = balance?.pending ?? 0;
  const available = balance?.balance ?? 0;

  return (
    <div className="portal-page">
      <PageHeader title="Momentum Wallet" subtitle="Your rewards at a glance" />

      <div className="portal-momentum-balance-card">
        <div className="portal-momentum-balance-card__label">Available Balance</div>
        <div className="portal-momentum-balance-card__value">{available}</div>
        <div className="portal-momentum-balance-card__breakdown">
          <div className="portal-momentum-balance-card__stat">
            <div className="portal-momentum-balance-card__stat-value">{pending}</div>
            <div className="portal-momentum-balance-card__stat-label">Pending</div>
          </div>
          <div className="portal-momentum-balance-card__stat">
            <div className="portal-momentum-balance-card__stat-value">{totalEarned}</div>
            <div className="portal-momentum-balance-card__stat-label">Total Earned</div>
          </div>
          <div className="portal-momentum-balance-card__stat">
            <div className="portal-momentum-balance-card__stat-value">{totalRedeemed}</div>
            <div className="portal-momentum-balance-card__stat-label">Total Redeemed</div>
          </div>
        </div>
      </div>

      <div className="portal-section">
        <h3 className="portal-section__title">How to Earn</h3>
        <ul className="portal-rules-list">
          <li><strong>50 points</strong> on purchases of KES 5,000 or more</li>
          <li><strong>30 points</strong> on purchases under KES 5,000</li>
          <li>Points are credited after payment confirmation</li>
        </ul>
      </div>

      <div className="portal-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 className="portal-section__title" style={{ marginBottom: 0 }}>Recent Transactions</h3>
          <Link to="/portal/momentum/transactions" style={{ fontSize: 13, color: '#1565C0', textDecoration: 'none' }}>View All →</Link>
        </div>
        {ledger.length === 0 ? (
          <EmptyState title="No transactions yet" description="Earn points on every purchase and referral!" />
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr><th>Date</th><th>Event</th><th>Points</th><th>Description</th></tr></thead>
              <tbody>
                {ledger.slice(0, 10).map((entry) => (
                  <tr key={entry.id}>
                    <td className="cell-secondary cell-nowrap">{formatDate(entry.created_at)}</td>
                    <td>{cleanEnum(entry.event_type)}</td>
                    <td><PointsBadge points={entry.points} /></td>
                    <td className="cell-secondary">{entry.description || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
        <Link to="/portal/referrals" className="btn btn--secondary">Refer a Friend</Link>
        <Link to="/portal/campaigns" className="btn btn--primary">Explore Offers</Link>
      </div>
    </div>
  );
}
