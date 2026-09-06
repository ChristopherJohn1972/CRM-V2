import { Link } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';

export default function MomentumRulesPage() {
  return (
    <div className="portal-page">
      <PageHeader
        title="How Momentum Works"
        subtitle="Everything you need to know about earning and using your Momentum points"
        actions={
          <Link to="/portal/momentum" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
            &larr; Back to Wallet
          </Link>
        }
      />

      <div className="portal-momentum-rules">
        <div className="form-section">
          <div className="form-section__header">
            <h2 className="form-section__title">What is Momentum?</h2>
          </div>
          <p className="cell-secondary" style={{ lineHeight: 1.7 }}>
            Momentum is our rewards program that gives you points every time you make a purchase.
            These points add up and can be redeemed for future benefits. The more you shop,
            the more you earn.
          </p>
        </div>

        <div className="form-section">
          <div className="form-section__header">
            <h2 className="form-section__title">Earning Rules</h2>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Purchase Amount</th>
                  <th>Points Earned</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ fontWeight: 500 }}>KES 5,000 or more</td>
                  <td><span className="points-badge points-badge--earn">+50 pts</span></td>
                  <td className="cell-secondary">You earn 50 Momentum points for every qualifying purchase of KES 5,000 and above.</td>
                </tr>
                <tr>
                  <td style={{ fontWeight: 500 }}>Under KES 5,000</td>
                  <td><span className="points-badge points-badge--earn">+30 pts</span></td>
                  <td className="cell-secondary">You earn 30 Momentum points for every purchase below KES 5,000.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div className="form-section">
          <div className="form-section__header">
            <h2 className="form-section__title">When Do Points Appear?</h2>
          </div>
          <p className="cell-secondary" style={{ lineHeight: 1.7 }}>
            Points are credited to your account after your payment is confirmed. You will see a
            &quot;Pending&quot; status until the payment clears, at which point the points become available
            for use.
          </p>
        </div>

        <div className="form-section">
          <div className="form-section__header">
            <h2 className="form-section__title">Reversals & Adjustments</h2>
          </div>
          <p className="cell-secondary" style={{ lineHeight: 1.7 }}>
            If an order is cancelled or refunded, the corresponding Momentum points will be
            reversed from your balance. Manual adjustments may also appear if our team adds or
            removes points for special cases.
          </p>
        </div>

        <div className="form-section">
          <div className="form-section__header">
            <h2 className="form-section__title">Qualification Conditions</h2>
          </div>
          <ul className="portal-rules-list">
            <li>Points are earned per completed order, not per item.</li>
            <li>Orders must be fully paid to qualify for Momentum points.</li>
            <li>Cancelled or refunded orders will not earn points (or will be reversed if already credited).</li>
            <li>Promotional or bonus points may be awarded separately and are clearly labeled.</li>
          </ul>
        </div>

        <div className="form-section">
          <div className="form-section__header">
            <h2 className="form-section__title">Need Help?</h2>
          </div>
          <p className="cell-secondary" style={{ lineHeight: 1.7 }}>
            If you have questions about your Momentum balance or a specific transaction,
            please contact our support team.
          </p>
        </div>
      </div>
    </div>
  );
}
