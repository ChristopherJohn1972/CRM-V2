import { useState, useEffect } from 'react';
import { fetchRewards, fetchRedemptions, redeemReward } from '../api/portal';
import { formatNumber, formatDate } from '../utils/format';
import PageHeader from '../components/PageHeader';
import Button from '../components/Button';
import { SkeletonCards } from '../components/Skeleton';
import { ErrorState, EmptyState } from '../components/States';
import { useToast } from '../components/Toast';
import { useAuth } from '../auth/AuthContext';

export function RewardsPage() {
  const { user } = useAuth();
  const [rewards, setRewards] = useState([]);
  const [redemptions, setRedemptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState('available');
  const [redeeming, setRedeeming] = useState(null);
  const toast = useToast();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [r, red] = await Promise.all([fetchRewards(), fetchRedemptions()]);
      setRewards(r);
      setRedemptions(red);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleRedeem = async (rewardId) => {
    setRedeeming(rewardId);
    try {
      await redeemReward(rewardId);
      toast.success('Reward redeemed successfully!');
      load();
    } catch (err) {
      toast.error(err.message || 'Failed to redeem reward.');
    } finally {
      setRedeeming(null);
    }
  };

  const momentumBalance = user?.momentum_balance || 1240;

  return (
    <div>
      <PageHeader title="Rewards" subtitle="Turn your Momentum into valuable benefits" />

      {/* Momentum balance */}
      <div className="momentum-card" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="momentum-card__label">Available Momentum</div>
        <div className="momentum-card__value">{formatNumber(momentumBalance)}</div>
      </div>

      {/* Tabs */}
      <div className="tabs" style={{ marginBottom: 'var(--space-6)' }}>
        <button className={`tab${tab === 'available' ? ' is-active' : ''}`} onClick={() => setTab('available')}>
          Available Rewards <span className="tab__count">{rewards.length}</span>
        </button>
        <button className={`tab${tab === 'history' ? ' is-active' : ''}`} onClick={() => setTab('history')}>
          Redemption History <span className="tab__count">{redemptions.length}</span>
        </button>
      </div>

      {loading && <SkeletonCards count={4} />}
      {error && <ErrorState detail={error} onRetry={load} />}

      {!loading && !error && tab === 'available' && (
        <>
          {rewards.length === 0 ? (
            <EmptyState title="No rewards available" body="Rewards will appear here once configured." />
          ) : (
            <div className="dashboard-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
              {rewards.map((r) => (
                <div key={r.id} className="reward-card">
                  <span className="reward-card__tier">{r.tier}</span>
                  <span className="reward-card__name">{r.name}</span>
                  <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)' }}>{r.description}</span>
                  <span className="reward-card__cost">
                    <strong>{formatNumber(r.momentum_required)}</strong> Momentum required
                  </span>
                  <Button
                    variant={r.available && momentumBalance >= r.momentum_required ? 'primary' : 'secondary'}
                    size="sm"
                    disabled={!r.available || momentumBalance < r.momentum_required || redeeming === r.id}
                    loading={redeeming === r.id}
                    onClick={() => handleRedeem(r.id)}
                  >
                    {!r.available ? 'Coming Soon' : momentumBalance < r.momentum_required ? `Need ${formatNumber(r.momentum_required - momentumBalance)} more` : 'Redeem'}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {!loading && !error && tab === 'history' && (
        <>
          {redemptions.length === 0 ? (
            <EmptyState title="No redemptions yet" body="Your redemption history will appear here." />
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Reward</th>
                    <th>Date</th>
                    <th>Momentum Used</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {redemptions.map((r) => (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 500 }}>{r.reward}</td>
                      <td className="cell-nowrap">{formatDate(r.date)}</td>
                      <td>{formatNumber(r.momentum_used)}</td>
                      <td><span className="badge badge--success">{r.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default RewardsPage;
