import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getMomentumBalance } from '../../api/momentum';
import { listCampaigns } from '../../api/campaigns';
import { portalMe } from '../../api/portal';
import { listLeads } from '../../api/leads';
import { listReferralCodes, listReferralEvents } from '../../api/referrals';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';
import { formatEnumLabel } from '../../utils/format';
import { CAMPAIGN_TYPE_LABELS } from '../../utils/constants';

const LEAD_STATUS_LABELS = {
  NEW: 'Received',
  QUALIFIED: 'Being reviewed',
  CONTACTED: 'Our team is in touch',
  CONVERTED: 'Purchase completed',
  LOST: 'Closed',
  SUPPRESSED: 'Communication unavailable',
};

function leadStatusLabel(status) {
  const key = cleanEnum(status);
  return LEAD_STATUS_LABELS[key] || key;
}

const LEAD_STATUS_VARIANT = {
  NEW: 'info',
  QUALIFIED: 'warning',
  CONTACTED: 'info',
  CONVERTED: 'success',
  LOST: 'muted',
  SUPPRESSED: 'muted',
};

function leadStatusVariant(status) {
  const key = cleanEnum(status);
  return LEAD_STATUS_VARIANT[key] || 'neutral';
}

export default function PortalHomeDashboard() {
  const [profile, setProfile] = useState(null);
  const [momentum, setMomentum] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [leads, setLeads] = useState([]);
  const [referralCodes, setReferralCodes] = useState([]);
  const [referralEvents, setReferralEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [p, m, c, l, rc, re] = await Promise.all([
          portalMe().catch(() => null),
          getMomentumBalance().catch(() => null),
          listCampaigns({ status: 'ACTIVE', page_size: 3 }).catch(() => ({ results: [] })),
          listLeads({ page_size: 5 }).catch(() => ({ results: [] })),
          listReferralCodes().catch(() => ({ results: [] })),
          listReferralEvents().catch(() => ({ results: [] })),
        ]);
        setProfile(p);
        setMomentum(m);
        setCampaigns(c.results || []);
        setLeads(l.results || []);
        setReferralCodes(rc.results || []);
        setReferralEvents(re.results || []);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="portal-page">
        <div className="loading-spinner">Loading...</div>
      </div>
    );
  }

  const firstName = profile?.first_name || '';
  const invited = referralEvents.filter(e => cleanEnum(e.event_type) === 'INVITED').length;
  const qualified = referralEvents.filter(e => cleanEnum(e.event_type) === 'QUALIFIED').length;
  const earned = referralCodes.reduce((sum, c) => sum + (c.earnings || 0), 0);

  return (
    <div className="portal-page">
      <PageHeader
        title={`Welcome${firstName ? `, ${firstName}` : ''}`}
        subtitle="Your portal dashboard"
      />

      <div className="portal-home">
        {/* Momentum Hero Card */}
        <div className="portal-card portal-card--momentum hero-card">
          <div className="hero-card__content">
            <h3>Momentum Balance</h3>
            <div className="hero-card__value">{momentum?.balance ?? 0} pts</div>
            <p className="hero-card__info">
              Total earned: {momentum?.total_earned ?? 0} pts
            </p>
          </div>
          <Link to="/portal/momentum" className="btn btn--primary btn--sm">
            View Wallet
          </Link>
        </div>

        {/* Quick Actions Grid */}
        <div className="portal-home__section">
          <h3>Quick Actions</h3>
          <div className="portal-home__actions">
            <Link to="/portal/campaigns" className="btn btn--secondary">
              Browse Campaigns
            </Link>
            <Link to="/portal/referrals" className="btn btn--secondary">
              Refer a Friend
            </Link>
            <Link to="/portal/momentum" className="btn btn--secondary">
              View Momentum
            </Link>
            <Link to="/portal/leads/new" className="btn btn--secondary">
              Register Interest
            </Link>
          </div>
        </div>

        {/* Featured Campaigns */}
        <div className="portal-home__section">
          <h3>Featured Campaigns</h3>
          {campaigns.length === 0 ? (
            <EmptyState
              title="No active campaigns"
              body="Check back later for new offers."
            />
          ) : (
            <div className="portal-campaign-grid">
              {campaigns.map(c => (
                <Link
                  key={c.campaign_id}
                  to={`/portal/campaigns/${c.campaign_id}`}
                  className="portal-campaign-card"
                >
                  <div className="portal-campaign-card__header">
                    <span className="portal-campaign-card__name">{c.name}</span>
                    <span className="portal-campaign-card__type">
                      {CAMPAIGN_TYPE_LABELS[c.campaign_type] || formatEnumLabel(c.campaign_type)}
                    </span>
                  </div>
                  <div className="portal-campaign-card__body">
                    <p>{c.description || 'No description available'}</p>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* My Interests */}
        <div className="portal-home__section">
          <h3>My Interests</h3>
          {leads.length === 0 ? (
            <EmptyState
              title="No interests submitted yet"
              body="Register your interest in a campaign to get started."
              action={
                <Link to="/portal/leads/new" className="btn btn--primary btn--sm">
                  Register Interest
                </Link>
              }
            />
          ) : (
            <div className="portal-interests-list">
              {leads.map(lead => (
                <Link
                  key={lead.id}
                  to={`/portal/interests/${lead.id}`}
                  className="portal-interest-row"
                >
                  <div className="portal-interest-row__name">
                    {lead.campaign_name || lead.source_campaign_name || 'General Interest'}
                  </div>
                  <div className="portal-interest-row__meta">
                    {lead.product_interests?.length > 0 && (
                      <span className="text-muted">
                        {lead.product_interests.join(', ')}
                      </span>
                    )}
                  </div>
                  <span className={`badge badge--${leadStatusVariant(cleanEnum(lead.status))}`}>
                    {leadStatusLabel(lead.status)}
                  </span>
                </Link>
              ))}
              <Link to="/portal/interests" className="btn btn--secondary btn--sm" style={{ marginTop: '0.75rem' }}>
                View All
              </Link>
            </div>
          )}
        </div>

        {/* Referral Snapshot */}
        <div className="portal-home__section">
          <h3>Referral Snapshot</h3>
          <div className="portal-home__actions">
            <div className="portal-stat-card">
              <div className="portal-stat-card__value">{invited}</div>
              <div className="portal-stat-card__label">Invited</div>
            </div>
            <div className="portal-stat-card">
              <div className="portal-stat-card__value">{qualified}</div>
              <div className="portal-stat-card__label">Qualified</div>
            </div>
            <div className="portal-stat-card">
              <div className="portal-stat-card__value">{earned} pts</div>
              <div className="portal-stat-card__label">Earned</div>
            </div>
          </div>
          <Link to="/portal/referrals" className="btn btn--secondary btn--sm" style={{ marginTop: '0.75rem' }}>
            Refer & Earn
          </Link>
        </div>
      </div>
    </div>
  );
}
