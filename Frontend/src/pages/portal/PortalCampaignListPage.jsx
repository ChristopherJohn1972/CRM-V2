import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { listCampaigns } from '../../api/campaigns';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';
import { formatEnumLabel } from '../../utils/format';
import { CAMPAIGN_TYPE_LABELS } from '../../utils/constants';

function CampaignBadge({ campaign }) {
  const now = new Date();
  const endDate = campaign.end_date ? new Date(campaign.end_date) : null;
  const daysLeft = endDate ? Math.ceil((endDate - now) / (1000 * 60 * 60 * 24)) : null;

  if (daysLeft !== null && daysLeft <= 7 && daysLeft > 0) {
    return <span className="portal-campaign-card__badge portal-campaign-card__badge--ending">Ending Soon</span>;
  }
  const created = campaign.created_at ? new Date(campaign.created_at) : null;
  if (created && (now - created) < 14 * 24 * 60 * 60 * 1000) {
    return <span className="portal-campaign-card__badge portal-campaign-card__badge--new">New</span>;
  }
  return null;
}

const CATEGORY_ICONS = {
  GAMING: '🎮', SOFTWARE: '💻', HARDWARE: '🖥️', MOBILE: '📱',
  default: '📦',
};

export default function PortalCampaignListPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const data = await listCampaigns({ status: 'ACTIVE', page_size: 100 });
        setCampaigns(data.results || []);
      } finally { setLoading(false); }
    }
    load();
  }, []);

  const filtered = useMemo(() => {
    if (!search.trim()) return campaigns;
    const q = search.toLowerCase();
    return campaigns.filter(c =>
      c.name?.toLowerCase().includes(q) || c.description?.toLowerCase().includes(q)
    );
  }, [campaigns, search]);

  const featured = filtered[0];
  const rest = filtered.slice(1);

  return (
    <div className="portal-page">
      <PageHeader title="Campaigns" subtitle="Discover offers and find the right products for you" />

      <div className="toolbar" style={{ marginBottom: 20 }}>
        <div className="toolbar__search" style={{ flex: '1 1 280px' }}>
          <input
            className="field__input"
            placeholder="Search campaigns..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search campaigns"
          />
        </div>
      </div>

      {loading ? (
        <div className="portal-campaign-grid">
          <div className="portal-skeleton portal-skeleton-card" />
          <div className="portal-skeleton portal-skeleton-card" />
          <div className="portal-skeleton portal-skeleton-card" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title={search ? 'No campaigns match your search' : 'No campaigns available'}
          description={search ? 'Try adjusting your search.' : 'Check back later for new offers.'}
        />
      ) : (
        <>
          {featured && (
            <Link to={`/portal/campaigns/${featured.campaign_id}`} className="portal-campaign-card" style={{ marginBottom: 20, display: 'block' }}>
              <div className="portal-campaign-card__image">
                {CATEGORY_ICONS[featured.campaign_type] || CATEGORY_ICONS.default}
              </div>
              <div className="portal-campaign-card__body">
                <div className="portal-campaign-card__header">
                  <span className="portal-campaign-card__name">{featured.name}</span>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    <CampaignBadge campaign={featured} />
                    <span className="portal-campaign-card__type">{CAMPAIGN_TYPE_LABELS[featured.campaign_type] || formatEnumLabel(featured.campaign_type)}</span>
                  </div>
                </div>
                <div className="portal-campaign-card__desc">{featured.description || 'No description available'}</div>
                {featured.start_date && (
                  <div className="portal-campaign-card__dates">
                    {featured.start_date}{featured.end_date ? ` — ${featured.end_date}` : ''}
                  </div>
                )}
              </div>
            </Link>
          )}

          {rest.length > 0 && (
            <div className="portal-campaign-grid">
              {rest.map(c => (
                <Link key={c.campaign_id} to={`/portal/campaigns/${c.campaign_id}`} className="portal-campaign-card">
                  <div className="portal-campaign-card__image">
                    {CATEGORY_ICONS[c.campaign_type] || CATEGORY_ICONS.default}
                  </div>
                  <div className="portal-campaign-card__body">
                    <div className="portal-campaign-card__header">
                      <span className="portal-campaign-card__name">{c.name}</span>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <CampaignBadge campaign={c} />
                        <span className="portal-campaign-card__type">{CAMPAIGN_TYPE_LABELS[c.campaign_type] || formatEnumLabel(c.campaign_type)}</span>
                      </div>
                    </div>
                    <div className="portal-campaign-card__desc">{c.description || 'No description available'}</div>
                    {c.start_date && (
                      <div className="portal-campaign-card__dates">
                        {c.start_date}{c.end_date ? ` — ${c.end_date}` : ''}
                      </div>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
