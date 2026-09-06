import { useState, useEffect } from 'react';
import { fetchMomentum } from '../api/portal';
import { formatCurrency, formatDate, formatNumber } from '../utils/format';
import PageHeader from '../components/PageHeader';
import { SkeletonCards } from '../components/Skeleton';
import { ErrorState } from '../components/States';

export function MomentumPage() {
  const [momentum, setMomentum] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMomentum();
      setMomentum(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <SkeletonCards />;
  if (error) return <ErrorState detail={error} onRetry={load} />;
  if (!momentum) return null;

  return (
    <div>
      <PageHeader title="Momentum" subtitle="Your accumulated customer benefit" />

      {/* Momentum Hero Card */}
      <div className="momentum-card" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="momentum-card__label">Your Momentum</div>
        <div className="momentum-card__value">{formatNumber(momentum.balance)}</div>
        <div className="momentum-card__meta">+{momentum.earned_this_month} earned this month</div>
        <div className="momentum-card__next">
          Next reward: {momentum.next_reward_distance} Momentum away
        </div>
      </div>

      <div className="grid-2">
        {/* How it works */}
        <div className="card">
          <div className="card__header"><h2 className="card__title">How Momentum Works</h2></div>
          <div className="card__body">
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 1.7 }}>
              <p style={{ marginBottom: 'var(--space-4)' }}>
                <strong style={{ color: 'var(--color-text)' }}>Simple and rewarding.</strong> You earn 1 Momentum for every KES 1,000 of qualifying confirmed payments.
              </p>
              <p style={{ marginBottom: 'var(--space-4)' }}>
                <strong style={{ color: 'var(--color-text)' }}>Never expires.</strong> Your Momentum balance is permanent and grows with every qualifying payment.
              </p>
              <p>
                <strong style={{ color: 'var(--color-text)' }}>Use it for rewards.</strong> Once you reach a reward threshold, you can redeem Momentum for valuable benefits.
              </p>
            </div>

            <div style={{ marginTop: 'var(--space-6)', padding: 'var(--space-4)', background: 'var(--color-surface-muted)', borderRadius: 'var(--radius-md)' }}>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginBottom: 'var(--space-2)' }}>Calculation</div>
              <div style={{ fontSize: 'var(--text-sm)', fontFamily: 'var(--font-mono)' }}>
                Momentum = FLOOR(Qualifying Payments / 1,000)
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-2)' }}>
                Total qualifying payments: KES {formatCurrency(momentum.qualifying_payments_total)}
              </div>
            </div>
          </div>
        </div>

        {/* Recent Earnings */}
        <div className="card">
          <div className="card__header"><h2 className="card__title">Recent Earnings</h2></div>
          <div className="card__body" style={{ padding: 0 }}>
            <div className="list-strip">
              {momentum.recent_earnings.map((e, i) => (
                <div key={i} className="list-strip__item" style={{ padding: 'var(--space-4) var(--space-5)' }}>
                  <div>
                    <div style={{ fontWeight: 500, fontSize: 'var(--text-sm)' }}>{e.reference}</div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>{formatDate(e.date)}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>KES {formatCurrency(e.amount)}</div>
                    <div style={{ color: 'var(--color-momentum)', fontWeight: 600, fontSize: 'var(--text-sm)' }}>+{e.momentum_earned}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Examples Table */}
      <div className="card" style={{ marginTop: 'var(--space-6)' }}>
        <div className="card__header"><h2 className="card__title">Momentum Earning Examples</h2></div>
        <div className="card__body" style={{ padding: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Qualifying Payment</th>
                <th>Momentum Earned</th>
              </tr>
            </thead>
            <tbody>
              {[{ amt: 500, m: 0 }, { amt: 999, m: 0 }, { amt: 1000, m: 1 }, { amt: 1500, m: 1 }, { amt: 2000, m: 2 }, { amt: 5000, m: 5 }, { amt: 10000, m: 10 }].map((row) => (
                <tr key={row.amt}>
                  <td>KES {formatCurrency(row.amt)}</td>
                  <td style={{ fontWeight: 500, color: row.m > 0 ? 'var(--color-momentum)' : 'var(--color-text-muted)' }}>{row.m}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default MomentumPage;
