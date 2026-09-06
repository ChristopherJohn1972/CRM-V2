import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { getCampaign } from '../../api/campaigns';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import ErrorState from '../../components/ErrorState';
import { formatEnumLabel } from '../../utils/format';
import {
  CAMPAIGN_STATUS_LABELS,
  CAMPAIGN_TYPE_LABELS,
} from '../../utils/constants';

const PRODUCT_ICONS = {
  GPU: '🎮', CPU: '⚡', RAM: '💾', SSD: '💿', MONITOR: '🖥️',
  default: '📦',
};

export default function PortalCampaignDetailPage() {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const [campaign, setCampaign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [acknowledged, setAcknowledged] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const c = await getCampaign(campaignId);
        setCampaign(c);
      } catch (err) {
        setError(err.message || 'Campaign not found');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [campaignId]);

  if (loading) return <div className="portal-page"><div className="loading-spinner">Loading...</div></div>;
  if (error) return <div className="portal-page"><ErrorState message={error} /></div>;
  if (!campaign) return <div className="portal-page"><ErrorState message="Campaign not found" /></div>;

  const products = campaign.products || [];
  const hasProducts = products.length > 0;

  return (
    <div className="portal-page">
      <Link to="/portal/campaigns" className="portal-back">← Back to Campaigns</Link>

      <div className="portal-campaign-hero">
        <div className="portal-campaign-hero__image">
          {PRODUCT_ICONS[campaign.campaign_type] || PRODUCT_ICONS.default}
        </div>
        <h1 className="portal-campaign-hero__title">{campaign.name}</h1>
        <p className="portal-campaign-hero__desc">{campaign.description || 'No description available'}</p>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap' }}>
          <StatusBadge status={campaign.status}>{CAMPAIGN_STATUS_LABELS[campaign.status] || formatEnumLabel(campaign.status)}</StatusBadge>
          {campaign.campaign_type && (
            <span className="portal-campaign-card__type">{CAMPAIGN_TYPE_LABELS[campaign.campaign_type] || formatEnumLabel(campaign.campaign_type)}</span>
          )}
        </div>
      </div>

      {hasProducts && (
        <div className="portal-section">
          <h3 className="portal-section__title">Products in this Campaign</h3>
          <div className="portal-products-grid">
            {products.map((p, idx) => (
              <div key={p.product_id || idx} className="portal-product-card">
                <div className="portal-product-card__image">
                  {PRODUCT_ICONS[p.category] || PRODUCT_ICONS.default}
                </div>
                <div className="portal-product-card__name">{p.name || p.product_name || `Product ${idx + 1}`}</div>
                {p.description && <div className="portal-product-card__benefit">{p.description}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="portal-section">
        <h3 className="portal-section__title">Campaign Details</h3>
        <div className="portal-profile-section">
          <dl className="detail-list">
            <dt>Type</dt><dd>{CAMPAIGN_TYPE_LABELS[campaign.campaign_type] || formatEnumLabel(campaign.campaign_type)}</dd>
            <dt>Start Date</dt><dd>{campaign.start_date || 'Ongoing'}</dd>
            <dt>End Date</dt><dd>{campaign.end_date || 'Ongoing'}</dd>
          </dl>
        </div>
      </div>

      <div className="portal-consent">
        <label className="portal-consent__check">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
          />
          <span>I understand this campaign and want to register my interest</span>
        </label>
        <p className="portal-consent__text">
          By registering, you agree to be contacted about this campaign. Your data will be used
          solely for this purpose and handled in accordance with our privacy policy.
        </p>
      </div>

      <div style={{ marginTop: 20, display: 'flex', gap: 12 }}>
        <button
          className="btn btn--primary btn--lg"
          disabled={!acknowledged}
          onClick={() => navigate(`/portal/leads/new?campaign=${campaign.campaign_id}`)}
        >
          Register Your Interest
        </button>
        <button
          className="btn btn--secondary"
          onClick={() => {
            if (navigator.share) {
              navigator.share({ title: campaign.name, text: campaign.description, url: window.location.href });
            } else {
              navigator.clipboard?.writeText(window.location.href);
            }
          }}
        >
          Share Campaign
        </button>
      </div>
    </div>
  );
}
