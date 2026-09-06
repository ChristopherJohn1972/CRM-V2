import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  getCampaign,
  transitionCampaign,
  generateBillboard as apiGenerateBillboard,
} from '../../api/campaigns';
import StatusBadge from '../../components/StatusBadge';
import ErrorState from '../../components/ErrorState';
import { formatEnumLabel } from '../../utils/format';
import {
  CAMPAIGN_STATUS_COLORS,
  CAMPAIGN_STATUS_LABELS,
  CAMPAIGN_OBJECTIVE_LABELS,
} from '../../utils/constants';

const STATUS_TRANSITIONS = {
  DRAFT: ['PRODUCT_SELECTED', 'CONFIGURING', 'CANCELLED', 'ABANDONED'],
  PRODUCT_SELECTED: ['CONFIGURING', 'CREATIVE_GENERATING', 'CANCELLED', 'ABANDONED'],
  CONFIGURING: ['CREATIVE_GENERATING', 'READY_FOR_REVIEW', 'CANCELLED', 'ABANDONED'],
  CREATIVE_GENERATING: ['CREATIVE_READY', 'GENERATION_FAILED', 'CANCELLED'],
  CREATIVE_READY: ['READY_FOR_REVIEW', 'CREATIVE_GENERATING', 'CANCELLED'],
  READY_FOR_REVIEW: ['APPROVED', 'CHANGES_REQUIRED', 'CANCELLED'],
  CHANGES_REQUIRED: ['CONFIGURING', 'CREATIVE_GENERATING', 'CANCELLED'],
  APPROVED: ['LAUNCHING', 'CHANGES_REQUIRED', 'CANCELLED'],
  LAUNCHING: ['ACTIVE', 'GENERATION_FAILED'],
  ACTIVE: ['PAUSED', 'COMPLETED'],
  PAUSED: ['ACTIVE', 'COMPLETED', 'CANCELLED'],
  GENERATION_FAILED: ['CREATIVE_GENERATING', 'CONFIGURING', 'CANCELLED'],
  COMPLETED: [],
  CANCELLED: [],
  ABANDONED: [],
};

const STYLES = [
  { key: 'hero', label: 'Product Focused', desc: 'Product centered with bold headline' },
  { key: 'split', label: 'Promotion Focused', desc: 'Product on left, text on right' },
  { key: 'minimal', label: 'Lifestyle', desc: 'Product fills background with overlay' },
];

const TABS = ['overview', 'creative'];

export default function CampaignDetailPage() {
  const { campaignId } = useParams();
  const [campaign, setCampaign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('creative');
  const [transitioning, setTransitioning] = useState(false);

  const [selectedStyle, setSelectedStyle] = useState('hero');
  const [creativeImage, setCreativeImage] = useState(null);
  const [creating, setCreating] = useState(false);
  const [creativeError, setCreativeError] = useState(null);

  useEffect(() => { loadCampaign(); }, [campaignId]);

  async function loadCampaign() {
    setLoading(true);
    setError(null);
    try {
      const c = await getCampaign(campaignId);
      setCampaign(c);

      if (c.target_products?.[0]?.image_url) {
        setCreativeImage(c.target_products[0].image_url);
      }
      if (c.creative?.image_url) {
        setCreativeImage(c.creative.image_url);
      }
    } catch (err) {
      setError(err.message || 'Failed to load campaign');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateCreative() {
    setCreating(true);
    setCreativeError(null);
    try {
      const result = await apiGenerateBillboard(campaignId, { template: selectedStyle });
      if (result.billboards?.[selectedStyle]?.storage_key) {
        setCreativeImage(`/api/storage/${result.billboards[selectedStyle].storage_key}`);
      } else if (result.billboards?.hero?.storage_key) {
        setCreativeImage(`/api/storage/${result.billboards.hero.storage_key}`);
      }
    } catch (err) {
      setCreativeError('Failed to create creative. Please try again.');
    } finally {
      setCreating(false);
    }
  }

  async function handleTransition(newStatus) {
    if (!confirm(`Transition campaign to ${newStatus}?`)) return;
    setTransitioning(true);
    try {
      await transitionCampaign(campaignId, { new_status: newStatus });
      await loadCampaign();
    } catch (err) {
      alert(err.message || 'Failed to transition campaign');
    } finally {
      setTransitioning(false);
    }
  }

  if (loading) return <div className="page"><div className="loading-spinner">Loading...</div></div>;
  if (error) return <div className="page"><ErrorState message={error} onRetry={loadCampaign} /></div>;
  if (!campaign) return <div className="page"><ErrorState message="Campaign not found" /></div>;

  const allowedTransitions = STATUS_TRANSITIONS[campaign.status] || [];
  const targetProduct = campaign.target_products?.[0];

  return (
    <div className="page campaign-detail-page">
      <div className="campaign-detail-page__header">
        <div className="campaign-detail-page__breadcrumb">
          <Link to="/campaigns" className="campaign-detail-page__back">← Campaigns</Link>
        </div>
        <div className="campaign-detail-page__title-row">
          <h1 className="campaign-detail-page__name">{campaign.name}</h1>
          <div className="campaign-detail-page__actions">
            <StatusBadge status={campaign.status}>{CAMPAIGN_STATUS_LABELS[campaign.status] || formatEnumLabel(campaign.status)}</StatusBadge>
            {allowedTransitions.map(s => (
              <button
                key={s}
                className={`btn btn--secondary btn--sm`}
                disabled={transitioning}
                onClick={() => handleTransition(s)}
              >
                {CAMPAIGN_STATUS_LABELS[s] || formatEnumLabel(s)}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="campaign-detail-page__tabs">
        {TABS.map(tab => (
          <button
            key={tab}
            className={`campaign-tab ${activeTab === tab ? 'campaign-tab--active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      <div className="campaign-detail-page__content">
        {activeTab === 'creative' && (
          <div className="creative-canvas">
            {!creativeImage && !creating && (
              <div className="creative-canvas__empty">
                <div className="creative-canvas__empty-icon">✦</div>
                <h2 className="creative-canvas__empty-title">Create your campaign creative</h2>
                <p className="creative-canvas__empty-desc">Choose a style to get started.</p>

                <div className="style-selector">
                  {STYLES.map(style => (
                    <button
                      key={style.key}
                      className={`style-card ${selectedStyle === style.key ? 'style-card--selected' : ''}`}
                      onClick={() => setSelectedStyle(style.key)}
                    >
                      <div className="style-card__icon">
                        {style.key === 'hero' && '◆'}
                        {style.key === 'split' && '◧'}
                        {style.key === 'minimal' && '◻'}
                      </div>
                      <div className="style-card__label">{style.label}</div>
                      <div className="style-card__desc">{style.desc}</div>
                      {selectedStyle === style.key && <div className="style-card__check">✓</div>}
                    </button>
                  ))}
                </div>

                <button
                  className="btn btn--primary btn--lg"
                  onClick={handleCreateCreative}
                >
                  Create
                </button>
              </div>
            )}

            {creating && (
              <div className="creative-canvas__loading">
                <div className="creative-canvas__spinner" />
                <h2 className="creative-canvas__loading-title">Creating your creative</h2>
                <p className="creative-canvas__loading-desc">This will take a moment</p>
              </div>
            )}

            {creativeImage && !creating && (
              <div className="creative-canvas__result">
                <div className="creative-canvas__image-wrap">
                  <img src={creativeImage} alt="Campaign creative" className="creative-canvas__image" />
                </div>

                <div className="creative-canvas__style-label">
                  {STYLES.find(s => s.key === selectedStyle)?.label || 'Campaign Creative'}
                </div>

                {creativeError && (
                  <div className="creative-canvas__error">{creativeError}</div>
                )}

                <div className="creative-canvas__controls">
                  <button className="btn btn--primary" onClick={handleCreateCreative} disabled={creating}>
                    Regenerate
                  </button>
                  <a
                    href={creativeImage}
                    download
                    className="btn btn--secondary"
                  >
                    Download
                  </a>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'overview' && (
          <div className="campaign-overview-canvas">
            <div className="overview-grid">
              {targetProduct && (
                <div className="overview-card">
                  <h4 className="overview-card__title">Product</h4>
                  <p className="overview-card__value">{targetProduct.name}</p>
                  {targetProduct.description && (
                    <p className="overview-card__desc">{targetProduct.description}</p>
                  )}
                  {targetProduct.price && (
                    <p className="overview-card__meta">KES {parseFloat(targetProduct.price).toLocaleString()}</p>
                  )}
                </div>
              )}

              <div className="overview-card">
                <h4 className="overview-card__title">Objective</h4>
                <p className="overview-card__value">{CAMPAIGN_OBJECTIVE_LABELS[campaign.objective] || formatEnumLabel(campaign.objective) || 'Not set'}</p>
              </div>

              <div className="overview-card">
                <h4 className="overview-card__title">Description</h4>
                <p className="overview-card__value">{campaign.description || 'No description'}</p>
              </div>

              <div className="overview-card">
                <h4 className="overview-card__title">Created</h4>
                <p className="overview-card__value">{new Date(campaign.created_at).toLocaleDateString()}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
