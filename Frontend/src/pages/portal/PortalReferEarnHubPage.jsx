import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listReferralCodes, listReferralEvents } from '../../api/referrals';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';

function cleanEnum(value) {
  if (!value || typeof value !== 'string') return value;
  const dotIndex = value.lastIndexOf('.');
  return dotIndex >= 0 ? value.slice(dotIndex + 1) : value;
}

const STATUS_LABELS = {
  LINK_OPENED: 'Link opened', FRIEND_JOINED: 'Friend joined',
  PURCHASE_DETECTED: 'Purchase detected', PENDING_CONFIRMATION: 'Pending confirmation',
  MOMENTUM_AWARDED: 'Momentum awarded', NOT_QUALIFIED: 'Not qualified', REWARD_REVERSED: 'Reward reversed',
};

function referralStatusLabel(status) {
  return STATUS_LABELS[cleanEnum(status)] || cleanEnum(status);
}

export default function PortalReferEarnHubPage() {
  const [codes, setCodes] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const [c, e] = await Promise.all([
          listReferralCodes().catch(() => ({ results: [] })),
          listReferralEvents().catch(() => ({ results: [] })),
        ]);
        setCodes(c.results || []); setEvents(e.results || []);
      } finally { setLoading(false); }
    }
    load();
  }, []);

  const stats = {
    invited: events.filter(e => ['LINK_OPENED', 'FRIEND_JOINED'].includes(cleanEnum(e.event_type))).length,
    registered: events.filter(e => cleanEnum(e.event_type) === 'FRIEND_JOINED').length,
    purchased: events.filter(e => cleanEnum(e.event_type) === 'PURCHASE_DETECTED').length,
    rewarded: events.filter(e => cleanEnum(e.event_type) === 'MOMENTUM_AWARDED').length,
  };

  function handleCopy(code) {
    navigator.clipboard?.writeText(code);
    setCopied(code);
    setTimeout(() => setCopied(null), 2000);
  }

  function handleShare() {
    const code = codes[0]?.code;
    const text = `Use my referral code ${code || ''} to get started!`;
    if (navigator.share) {
      navigator.share({ title: 'Refer & Earn', text });
    } else {
      navigator.clipboard?.writeText(text);
      setCopied('link');
      setTimeout(() => setCopied(null), 2000);
    }
  }

  if (loading) return <div className="portal-page"><div className="loading-spinner">Loading...</div></div>;

  return (
    <div className="portal-page">
      <div className="portal-refer-hero">
        <h1 className="portal-refer-hero__title">Refer a friend. Earn Momentum.</h1>
        <p className="portal-refer-hero__desc">Share your unique code. When friends make a qualifying purchase, you both earn rewards.</p>
        <button className="portal-referral-share-btn" onClick={handleShare}>
          {copied === 'link' ? '✓ Copied!' : 'Share Referral Link'}
        </button>
      </div>

      <div className="portal-section">
        <h3 className="portal-section__title">Your Referral Codes</h3>
        {codes.length === 0 ? (
          <EmptyState title="No referral codes yet" description="You'll receive a referral code once your account is active." />
        ) : (
          <div className="portal-referral-codes">
            {codes.map(c => (
              <div key={c.id || c.code} className="portal-referral-code-card">
                <div className="portal-referral-code-card__code">{c.code}</div>
                <div className="portal-referral-code-card__stats">
                  <span>{c.use_count || 0} uses</span>
                  {c.max_uses && <span>Max: {c.max_uses}</span>}
                  {c.expires_at && <span>Expires: {new Date(c.expires_at).toLocaleDateString()}</span>}
                </div>
                <button className="btn btn--secondary btn--sm" onClick={() => handleCopy(c.code)}>
                  {copied === c.code ? '✓ Copied!' : 'Copy Code'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="portal-section">
        <h3 className="portal-section__title">Your Stats</h3>
        <div className="portal-referral-stats">
          <div className="portal-referral-stat">
            <div className="portal-referral-stat__value">{stats.invited}</div>
            <div className="portal-referral-stat__label">Invited</div>
          </div>
          <div className="portal-referral-stat">
            <div className="portal-referral-stat__value">{stats.registered}</div>
            <div className="portal-referral-stat__label">Registered</div>
          </div>
          <div className="portal-referral-stat">
            <div className="portal-referral-stat__value">{stats.purchased}</div>
            <div className="portal-referral-stat__label">Purchased</div>
          </div>
          <div className="portal-referral-stat">
            <div className="portal-referral-stat__value">{stats.rewarded}</div>
            <div className="portal-referral-stat__label">Rewarded</div>
          </div>
        </div>
      </div>

      {events.length > 0 && (
        <div className="portal-section">
          <h3 className="portal-section__title">Referral History</h3>
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr><th>Date</th><th>Event</th><th>Status</th><th>Description</th></tr></thead>
              <tbody>
                {events.map(ev => (
                  <tr key={ev.id || ev.event_id}>
                    <td className="cell-secondary cell-nowrap">{new Date(ev.created_at).toLocaleDateString()}</td>
                    <td>{cleanEnum(ev.event_type)}</td>
                    <td><span className={`portal-referral-status portal-referral-status--${cleanEnum(ev.status)?.toLowerCase()}`}>{referralStatusLabel(ev.status)}</span></td>
                    <td className="cell-secondary">{ev.description || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="portal-section">
        <h3 className="portal-section__title">How it works</h3>
        <ol className="portal-how-to">
          <li>Share your unique referral code with friends and colleagues</li>
          <li>When they sign up using your code, you both earn Momentum rewards</li>
          <li>Track your referrals and earnings right here in real time</li>
        </ol>
      </div>

      <div className="portal-section">
        <h3 className="portal-section__title">FAQ</h3>
        <div className="portal-profile-section">
          <dl className="detail-list">
            <dt>How much can I earn?</dt>
            <dd>Earn 50 Momentum for qualifying purchases over KES 5,000, or 30 Momentum for smaller purchases.</dd>
            <dt>When are rewards credited?</dt>
            <dd>Rewards are confirmed after the referred friend's purchase is verified.</dd>
            <dt>Can rewards be reversed?</dt>
            <dd>Yes, if a qualifying purchase is refunded or reversed, the associated Momentum reward will also be reversed.</dd>
          </dl>
        </div>
      </div>
    </div>
  );
}
