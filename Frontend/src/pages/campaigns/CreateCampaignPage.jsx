import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  createCampaign,
  updateCampaignAudience,
  updateCampaignOffer,
  addCampaignChannel,
  updateCampaignBudget,
  generateBillboard as apiGenerateBillboard,
  getCampaignReadiness,
  launchCampaign,
  uploadProductImage,
} from '../../api/campaigns';
import PageHeader from '../../components/PageHeader';

const OBJECTIVES = [
  { value: 'AWARENESS', label: 'Awareness', desc: 'Increase brand visibility' },
  { value: 'CONVERSION', label: 'Conversion', desc: 'Drive purchases' },
  { value: 'LEAD_GENERATION', label: 'Lead Generation', desc: 'Capture interested prospects' },
  { value: 'ENGAGEMENT', label: 'Engagement', desc: 'Build audience interaction' },
];

const AUDIENCE_TYPES = [
  { value: 'BROAD', label: 'Broad' },
  { value: 'INTEREST', label: 'Interest-based' },
  { value: 'DEMOGRAPHIC', label: 'Demographic' },
  { value: 'BEHAVIORAL', label: 'Behavioral' },
  { value: 'CUSTOM', label: 'Custom' },
];

const OFFER_TYPES = [
  { value: 'PERCENTAGE_DISCOUNT', label: 'Percentage off' },
  { value: 'FIXED_DISCOUNT', label: 'Fixed discount' },
  { value: 'NONE', label: 'No offer' },
];

const CHANNELS = [
  { value: 'INSTAGRAM', label: 'Instagram', icon: '📸' },
  { value: 'FACEBOOK', label: 'Facebook', icon: '👥' },
  { value: 'WEBSITE', label: 'Website', icon: '🌐' },
  { value: 'EMAIL', label: 'Email', icon: '✉️' },
  { value: 'SMS', label: 'SMS', icon: '💬' },
  { value: 'GOOGLE_ADS', label: 'Google Ads', icon: '🔍' },
  { value: 'TWITTER', label: 'Twitter/X', icon: '🐦' },
  { value: 'LINKEDIN', label: 'LinkedIn', icon: '💼' },
  { value: 'TIKTOK', label: 'TikTok', icon: '🎵' },
];

const STYLES = [
  { value: 'hero', label: 'Product Focused', desc: 'Product is the hero of the creative', icon: '◆' },
  { value: 'split', label: 'Promotion Focused', desc: 'Split layout with product and messaging', icon: '◧' },
  { value: 'minimal', label: 'Lifestyle', desc: 'Full-bleed imagery with minimal overlay', icon: '◻' },
];

export default function CreateCampaignPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [step, setStep] = useState('product');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [campaignId, setCampaignId] = useState(null);
  const [generatedImage, setGeneratedImage] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [readiness, setReadiness] = useState(null);
  const [launching, setLaunching] = useState(false);

  const [product, setProduct] = useState({
    name: '',
    description: '',
    price: '',
    offer: '',
    imageFile: null,
    imagePreview: null,
    imageUrl: null,
  });

  const [selectedStyle, setSelectedStyle] = useState('hero');

  const [config, setConfig] = useState({
    name: '',
    objective: 'CONVERSION',
    audience_type: 'INTEREST',
    audience_description: '',
    offer_type: 'PERCENTAGE_DISCOUNT',
    offer_value: 15,
    offer_description: '',
    channels: ['INSTAGRAM', 'FACEBOOK'],
    budget: 1000,
    customizing_audience: false,
    customizing_offer: false,
    customizing_channels: false,
  });

  function updateProduct(field, value) {
    setProduct((prev) => ({ ...prev, [field]: value }));
  }

  function updateConfig(field, value) {
    setConfig((prev) => ({ ...prev, [field]: value }));
  }

  function handleImageSelect(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const preview = URL.createObjectURL(file);
    setProduct((prev) => ({ ...prev, imageFile: file, imagePreview: preview }));
  }

  function handleDrop(e) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    const preview = URL.createObjectURL(file);
    setProduct((prev) => ({ ...prev, imageFile: file, imagePreview: preview }));
  }

  function handleDragOver(e) {
    e.preventDefault();
  }

  function removeImage() {
    setProduct((prev) => ({ ...prev, imageFile: null, imagePreview: null, imageUrl: null }));
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function handleNextToStyle() {
    if (!product.name.trim()) {
      setError('Product name is required.');
      return;
    }
    setError(null);
    setStep('style');
  }

  async function handleGenerate() {
    setGenerating(true);
    setError(null);

    try {
      let imageUrl = product.imageUrl;
      if (product.imageFile && !imageUrl) {
        const uploadResult = await uploadProductImage(product.imageFile);
        imageUrl = uploadResult.url;
        updateProduct('imageUrl', imageUrl);
      }

      const campaignName = config.name || `${product.name} Campaign`;

      const campaign = await createCampaign({
        name: campaignName,
        description: product.description || `Campaign for ${product.name}`,
        campaign_type: 'PROMOTIONAL',
        objective: config.objective,
        target_products: [{
          name: product.name,
          description: product.description,
          price: product.price ? parseFloat(product.price) : null,
          offer: product.offer,
          image_url: imageUrl,
        }],
      });

      const cid = campaign.campaign_id;
      setCampaignId(cid);

      const billboardResult = await apiGenerateBillboard(cid, {
        template: selectedStyle,
        product_image_url: imageUrl,
      });

      if (billboardResult && billboardResult.billboards) {
        const primary = billboardResult.billboards[selectedStyle] || billboardResult.billboards.hero;
        if (primary) {
          setGeneratedImage(`/api/storage/${primary.storage_key}`);
        }
      }

      setStep('generating');

      await updateCampaignAudience(cid, {
        audience_type: config.audience_type,
        description: config.audience_description || `People interested in ${product.name}`,
      }).catch(() => {});

      if (config.offer_type !== 'NONE') {
        const offerText = product.offer || `${config.offer_value}% off ${product.name}`;
        await updateCampaignOffer(cid, {
          offer_type: config.offer_type,
          value: config.offer_value,
          description: offerText,
        }).catch(() => {});
      }

      for (const ch of config.channels) {
        await addCampaignChannel(cid, { channel: ch }).catch(() => {});
      }

      await updateCampaignBudget(cid, {
        amount: config.budget,
        currency: 'KES',
        period: 'CAMPAIGN',
      }).catch(() => {});

      const readinessResult = await getCampaignReadiness(cid).catch(() => null);
      setReadiness(readinessResult);

      setStep('result');
    } catch (err) {
      setError(err.message || 'Failed to generate creative. Please try again.');
      setStep('style');
    } finally {
      setGenerating(false);
    }
  }

  async function handleRegenerate() {
    if (!campaignId) return;
    setGenerating(true);
    setError(null);
    try {
      const billboardResult = await apiGenerateBillboard(campaignId, {
        template: selectedStyle,
        product_image_url: product.imageUrl,
      });
      if (billboardResult && billboardResult.billboards) {
        const primary = billboardResult.billboards[selectedStyle] || billboardResult.billboards.hero;
        if (primary) {
          setGeneratedImage(`/api/storage/${primary.storage_key}`);
        }
      }
    } catch (err) {
      setError(err.message || 'Failed to regenerate. Please try again.');
    } finally {
      setGenerating(false);
    }
  }

  async function handleLaunch() {
    setLaunching(true);
    setError(null);
    try {
      await launchCampaign(campaignId, {});
      navigate(`/campaigns/${campaignId}`);
    } catch (err) {
      setError(err.message || 'Failed to launch campaign');
    } finally {
      setLaunching(false);
    }
  }

  if (step === 'product') {
    return (
      <div className="page">
        <PageHeader
          title="Create campaign"
          subtitle="Tell us about the product you want to advertise"
          actions={
            <button className="btn btn--secondary" onClick={() => navigate(-1)}>
              Cancel
            </button>
          }
        />

        <div className="product-entry">
          <div className="product-entry__form">
            <div className="product-entry__field">
              <label className="product-entry__label">Product name *</label>
              <input
                className="product-entry__input"
                type="text"
                value={product.name}
                onChange={(e) => updateProduct('name', e.target.value)}
                placeholder="e.g. Running Shoe X"
                autoFocus
              />
            </div>

            <div className="product-entry__field">
              <label className="product-entry__label">Product description</label>
              <textarea
                className="product-entry__textarea"
                value={product.description}
                onChange={(e) => updateProduct('description', e.target.value)}
                placeholder="Describe the product — what it is, who it's for, what makes it special"
                rows={3}
              />
            </div>

            <div className="product-entry__row">
              <div className="product-entry__field product-entry__field--half">
                <label className="product-entry__label">Price</label>
                <div className="product-entry__price-wrap">
                  <span className="product-entry__currency">KES</span>
                  <input
                    className="product-entry__input product-entry__input--price"
                    type="number"
                    value={product.price}
                    onChange={(e) => updateProduct('price', e.target.value)}
                    placeholder="0"
                    min="0"
                  />
                </div>
              </div>

              <div className="product-entry__field product-entry__field--half">
                <label className="product-entry__label">Promotion / offer</label>
                <input
                  className="product-entry__input"
                  type="text"
                  value={product.offer}
                  onChange={(e) => updateProduct('offer', e.target.value)}
                  placeholder="e.g. 20% off"
                />
              </div>
            </div>

            <div className="product-entry__field">
              <label className="product-entry__label">Product image</label>
              {product.imagePreview ? (
                <div className="product-entry__image-preview">
                  <img src={product.imagePreview} alt="Product preview" />
                  <button className="product-entry__image-remove" onClick={removeImage}>Remove</button>
                </div>
              ) : (
                <div
                  className="product-entry__upload"
                  onClick={() => fileInputRef.current?.click()}
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                >
                  <div className="product-entry__upload-icon">+</div>
                  <div className="product-entry__upload-text">
                    Upload product image
                  </div>
                  <div className="product-entry__upload-hint">
                    Drag & drop or click to browse
                  </div>
                  <div className="product-entry__upload-formats">
                    JPEG, PNG, WebP — max 10MB
                  </div>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleImageSelect}
                style={{ display: 'none' }}
              />
            </div>

            {error && (
              <div className="product-entry__error">{error}</div>
            )}

            <button
              className="btn btn--primary btn--lg btn--full"
              disabled={!product.name.trim()}
              onClick={handleNextToStyle}
            >
              Continue
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (step === 'style') {
    return (
      <div className="page">
        <PageHeader
          title="Choose creative style"
          subtitle={`For ${product.name}`}
          actions={
            <button className="btn btn--secondary" onClick={() => setStep('product')}>
              Back
            </button>
          }
        />

        <div className="campaign-style-page">
          {product.imagePreview && (
            <div className="campaign-style-page__preview">
              <img src={product.imagePreview} alt="Product" />
            </div>
          )}

          <div className="style-selector">
            {STYLES.map((style) => (
              <button
                key={style.value}
                className={`style-card ${selectedStyle === style.value ? 'style-card--selected' : ''}`}
                onClick={() => setSelectedStyle(style.value)}
              >
                <span className="style-card__icon">{style.icon}</span>
                <span className="style-card__label">{style.label}</span>
                <span className="style-card__desc">{style.desc}</span>
                {selectedStyle === style.value && <span className="style-card__check">✓</span>}
              </button>
            ))}
          </div>

          {error && (
            <div className="product-entry__error">{error}</div>
          )}

          <button
            className="btn btn--primary btn--lg btn--full"
            disabled={generating}
            onClick={handleGenerate}
          >
            {generating ? 'Generating...' : 'Generate creative'}
          </button>
        </div>
      </div>
    );
  }

  if (step === 'generating') {
    return (
      <div className="page">
        <div className="campaign-preparing">
          <div className="campaign-preparing__content">
            <div className="campaign-preparing__spinner" />
            <h2 className="campaign-preparing__title">Creating your campaign creative</h2>
            <p style={{ color: '#64748b', fontSize: 14, marginTop: 8 }}>
              This may take up to 30 seconds while we generate a professional marketing image.
            </p>
            <div className="campaign-preparing__steps">
              <div className="campaign-preparing__step campaign-preparing__step--done">
                <span className="campaign-preparing__check">✓</span>
                Product information received
              </div>
              <div className="campaign-preparing__step campaign-preparing__step--done">
                <span className="campaign-preparing__check">✓</span>
                Campaign direction set
              </div>
              <div className="campaign-preparing__step campaign-preparing__step--active">
                <span className="campaign-preparing__dot" />
                Generating campaign creative
              </div>
              <div className="campaign-preparing__step">
                <span className="campaign-preparing__dot" />
                Finalizing campaign
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (step === 'result') {
    return (
      <div className="page">
        <PageHeader
          title="Your creative is ready"
          subtitle={product.name}
          actions={
            <button className="btn btn--secondary" onClick={() => setStep('style')}>
              Try another style
            </button>
          }
        />

        <div className="campaign-workspace">
          <div className="campaign-workspace__creative">
            <div className="creative-canvas">
              {generating ? (
                <div className="creative-canvas__loading">
                  <div className="campaign-preparing__spinner" />
                  <p>Regenerating...</p>
                </div>
              ) : generatedImage ? (
                <img src={generatedImage} alt="Generated creative" className="creative-canvas__image" />
              ) : (
                <div className="creative-canvas__empty">
                  <p>No creative generated yet</p>
                </div>
              )}
            </div>

            <div className="creative-canvas__controls">
              <button
                className="btn btn--secondary"
                onClick={handleRegenerate}
                disabled={generating}
              >
                Regenerate
              </button>
              <button
                className="btn btn--secondary"
                onClick={() => setStep('style')}
              >
                Try another style
              </button>
            </div>
          </div>

          <div className="campaign-workspace__config">
            <div className="config-panel">
              <h3 className="config-panel__title">Campaign settings</h3>

              <div className="config-section">
                <div className="config-section__header">
                  <span className="config-section__label">Product</span>
                </div>
                <div className="config-section__value">
                  {product.name}
                  <button className="config-section__change" onClick={() => setStep('product')}>
                    Change
                  </button>
                </div>
              </div>

              <div className="config-section">
                <div className="config-section__header">
                  <span className="config-section__label">Campaign name</span>
                </div>
                <input
                  className="config-section__input"
                  value={config.name}
                  onChange={(e) => updateConfig('name', e.target.value)}
                  placeholder={`${product.name} Campaign`}
                />
              </div>

              <div className="config-section">
                <div className="config-section__header">
                  <span className="config-section__label">Objective</span>
                </div>
                <div className="config-section__options">
                  {OBJECTIVES.map((obj) => (
                    <button
                      key={obj.value}
                      className={`config-option ${config.objective === obj.value ? 'config-option--active' : ''}`}
                      onClick={() => updateConfig('objective', obj.value)}
                    >
                      {obj.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="config-section">
                <div className="config-section__header">
                  <span className="config-section__label">Audience</span>
                  <button
                    className="config-section__toggle"
                    onClick={() => updateConfig('customizing_audience', !config.customizing_audience)}
                  >
                    {config.customizing_audience ? 'Done' : 'Customize'}
                  </button>
                </div>
                {config.customizing_audience ? (
                  <div className="config-section__detail">
                    <div className="config-field">
                      <label>Audience type</label>
                      <select
                        value={config.audience_type}
                        onChange={(e) => updateConfig('audience_type', e.target.value)}
                      >
                        {AUDIENCE_TYPES.map((at) => (
                          <option key={at.value} value={at.value}>{at.label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="config-field">
                      <label>Description</label>
                      <input
                        value={config.audience_description}
                        onChange={(e) => updateConfig('audience_description', e.target.value)}
                        placeholder={`People interested in ${product.name}`}
                      />
                    </div>
                  </div>
                ) : (
                  <div className="config-section__value config-section__value--recommended">
                    <span className="config-badge">Recommended</span>
                    People interested in {product.name}
                  </div>
                )}
              </div>

              <div className="config-section">
                <div className="config-section__header">
                  <span className="config-section__label">Offer</span>
                  <button
                    className="config-section__toggle"
                    onClick={() => updateConfig('customizing_offer', !config.customizing_offer)}
                  >
                    {config.customizing_offer ? 'Done' : 'Customize'}
                  </button>
                </div>
                {config.customizing_offer ? (
                  <div className="config-section__detail">
                    <div className="config-field">
                      <label>Type</label>
                      <select
                        value={config.offer_type}
                        onChange={(e) => updateConfig('offer_type', e.target.value)}
                      >
                        {OFFER_TYPES.map((ot) => (
                          <option key={ot.value} value={ot.value}>{ot.label}</option>
                        ))}
                      </select>
                    </div>
                    {config.offer_type !== 'NONE' && (
                      <div className="config-field">
                        <label>{config.offer_type === 'PERCENTAGE_DISCOUNT' ? 'Percentage (%)' : 'Amount (KES)'}</label>
                        <input
                          type="number"
                          value={config.offer_value}
                          onChange={(e) => updateConfig('offer_value', parseFloat(e.target.value) || 0)}
                        />
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="config-section__value config-section__value--recommended">
                    <span className="config-badge">Recommended</span>
                    {product.offer || `${config.offer_value}% off`}
                  </div>
                )}
              </div>

              <div className="config-section">
                <div className="config-section__header">
                  <span className="config-section__label">Channels</span>
                  <button
                    className="config-section__toggle"
                    onClick={() => updateConfig('customizing_channels', !config.customizing_channels)}
                  >
                    {config.customizing_channels ? 'Done' : 'Change'}
                  </button>
                </div>
                {config.customizing_channels ? (
                  <div className="config-section__detail">
                    <div className="channel-picker">
                      {CHANNELS.map((ch) => (
                        <button
                          key={ch.value}
                          className={`channel-chip ${config.channels.includes(ch.value) ? 'channel-chip--active' : ''}`}
                          onClick={() => {
                            const next = config.channels.includes(ch.value)
                              ? config.channels.filter((c) => c !== ch.value)
                              : [...config.channels, ch.value];
                            updateConfig('channels', next);
                          }}
                        >
                          <span>{ch.icon}</span> {ch.label}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="config-section__value">
                    {config.channels
                      .map((c) => CHANNELS.find((ch) => ch.value === c)?.label || c)
                      .join(' · ')}
                  </div>
                )}
              </div>

              <div className="config-section">
                <div className="config-section__header">
                  <span className="config-section__label">Budget</span>
                </div>
                <div className="config-section__budget">
                  <span className="config-section__currency">KES</span>
                  <input
                    className="config-section__budget-input"
                    type="number"
                    value={config.budget}
                    onChange={(e) => updateConfig('budget', parseFloat(e.target.value) || 0)}
                  />
                </div>
              </div>

              {error && (
                <div className="config-panel__error">{error}</div>
              )}

              <button
                className="btn btn--primary btn--full"
                onClick={() => setStep('review')}
              >
                Continue to review
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (step === 'review') {
    const checks = readiness?.checks || [];

    return (
      <div className="page">
        <PageHeader
          title="Review and launch"
          subtitle={product.name}
          actions={
            <button className="btn btn--secondary" onClick={() => setStep('result')}>
              Back to editor
            </button>
          }
        />

        <div className="campaign-review">
          <div className="campaign-review__creative">
            {generatedImage && (
              <div className="creative-canvas">
                <img src={generatedImage} alt="Generated creative" className="creative-canvas__image" />
              </div>
            )}
          </div>

          <div className="campaign-review__summary">
            <h3>Campaign summary</h3>

            <div className="review-item">
              <span className="review-item__label">Product</span>
              <span className="review-item__value">{product.name}</span>
            </div>
            {product.description && (
              <div className="review-item">
                <span className="review-item__label">Description</span>
                <span className="review-item__value">{product.description}</span>
              </div>
            )}
            {product.price && (
              <div className="review-item">
                <span className="review-item__label">Price</span>
                <span className="review-item__value">KES {parseFloat(product.price).toLocaleString()}</span>
              </div>
            )}
            {product.offer && (
              <div className="review-item">
                <span className="review-item__label">Offer</span>
                <span className="review-item__value">{product.offer}</span>
              </div>
            )}
            <div className="review-item">
              <span className="review-item__label">Objective</span>
              <span className="review-item__value">{OBJECTIVES.find((o) => o.value === config.objective)?.label}</span>
            </div>
            <div className="review-item">
              <span className="review-item__label">Audience</span>
              <span className="review-item__value">
                {config.customizing_audience
                  ? config.audience_description || config.audience_type
                  : `People interested in ${product.name}`}
              </span>
            </div>
            <div className="review-item">
              <span className="review-item__label">Channels</span>
              <span className="review-item__value">
                {config.channels.map((c) => CHANNELS.find((ch) => ch.value === c)?.label || c).join(', ')}
              </span>
            </div>
            <div className="review-item">
              <span className="review-item__label">Budget</span>
              <span className="review-item__value">KES {config.budget.toLocaleString()}</span>
            </div>

            {checks.length > 0 && (
              <div className="review-checklist">
                <h4>Readiness check</h4>
                {checks.map((check, i) => (
                  <div key={i} className={`review-check review-check--${check.status === 'passed' ? 'pass' : check.status === 'warning' ? 'warn' : 'fail'}`}>
                    <span className="review-check__icon">
                      {check.status === 'passed' ? '✓' : check.status === 'warning' ? '⚠' : '○'}
                    </span>
                    <span className="review-check__text">{check.message || check.key}</span>
                  </div>
                ))}
              </div>
            )}

            {error && (
              <div className="config-panel__error">{error}</div>
            )}

            <div className="review-actions">
              <button
                className="btn btn--primary btn--lg btn--full"
                disabled={launching}
                onClick={handleLaunch}
              >
                {launching ? 'Launching...' : 'Launch campaign'}
              </button>
              <button
                className="btn btn--secondary btn--full"
                onClick={() => navigate(`/campaigns/${campaignId}`)}
              >
                Save as draft
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
