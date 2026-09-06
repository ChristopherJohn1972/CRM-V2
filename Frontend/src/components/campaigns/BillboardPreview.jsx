import { useState, useEffect } from 'react';
import { generateBillboard as apiGenerateBillboard } from '../../api/campaigns';

const TEMPLATES = [
  { key: 'hero', label: 'Product focused', description: 'Product centered with bold headline' },
  { key: 'split', label: 'Promotion focused', description: 'Product on left, text on right' },
  { key: 'minimal', label: 'Lifestyle', description: 'Product fills background with overlay' },
];

export default function BillboardPreview({ campaignId, creative, onBillboardGenerated }) {
  const [billboards, setBillboards] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState('hero');
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (creative?.image_url) {
      setBillboards({
        primary: { storage_key: creative.image_url },
      });
    }
  }, [creative]);

  const handleGenerate = async (template) => {
    if (!campaignId) return;
    setGenerating(true);
    setError(null);
    try {
      const data = await apiGenerateBillboard(campaignId, {
        template,
        creative_id: creative?.id,
      });
      setBillboards(data);
      setSelectedTemplate(template);
      onBillboardGenerated?.(data);
    } catch (err) {
      setError(err.message || 'Failed to generate creative');
    } finally {
      setGenerating(false);
    }
  };

  const getBillboardUrl = (billboardsData, template) => {
    if (!billboardsData) return null;
    if (billboardsData.billboards?.[template]?.storage_key) {
      return `/api/storage/${billboardsData.billboards[template].storage_key}`;
    }
    if (billboardsData.primary?.storage_key) {
      return `/api/storage/${billboardsData.primary.storage_key}`;
    }
    return null;
  };

  const headline = creative?.headline?.value || creative?.headline || '';
  const subheadline = creative?.subheadline?.value || creative?.subheadline || '';
  const cta = creative?.cta?.value || creative?.cta || '';

  return (
    <div className="billboard-preview">
      <div className="billboard-preview__header">
        <h3 className="billboard-preview__title">Campaign creative</h3>
        {campaignId > 0 && (
          <div className="billboard-preview__templates">
            {TEMPLATES.map((t) => (
              <button
                key={t.key}
                className={`billboard-preview__template-btn ${selectedTemplate === t.key ? 'active' : ''}`}
                onClick={() => handleGenerate(t.key)}
                disabled={generating}
                title={t.description}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {generating && (
        <div className="billboard-preview__loading">
          <div className="billboard-preview__spinner" />
          <span>Preparing your campaign creative...</span>
        </div>
      )}

      {error && (
        <div className="billboard-preview__error">{error}</div>
      )}

      <div className="billboard-preview__canvas">
        {getBillboardUrl(billboards, selectedTemplate) ? (
          <img
            src={getBillboardUrl(billboards, selectedTemplate)}
            alt="Campaign billboard"
            className="billboard-preview__image"
          />
        ) : (
          <div className="billboard-preview__placeholder">
            <div className="billboard-preview__placeholder-content">
              {headline && (
                <div className="billboard-preview__placeholder-headline">
                  {headline}
                </div>
              )}
              {subheadline && (
                <div className="billboard-preview__placeholder-sub">
                  {subheadline}
                </div>
              )}
              {creative?.visual_direction && (
                <div className="billboard-preview__placeholder-visual">
                  {creative.visual_direction}
                </div>
              )}
              {cta && (
                <div className="billboard-preview__placeholder-cta">
                  {cta}
                </div>
              )}
              {!headline && !subheadline && !cta && !campaignId && (
                <div className="billboard-preview__placeholder-empty">
                  Select a product to generate your campaign creative
                </div>
              )}
              {!headline && !subheadline && !cta && campaignId > 0 && (
                <div className="billboard-preview__placeholder-empty">
                  Choose a style to generate your creative
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {billboards?.billboards && Object.keys(billboards.billboards).length > 1 && (
        <div className="billboard-preview__variants">
          <span className="billboard-preview__variants-label">Other styles:</span>
          {Object.entries(billboards.billboards)
            .filter(([key]) => key !== selectedTemplate)
            .map(([key, data]) => (
              <button
                key={key}
                className="billboard-preview__variant-thumb"
                onClick={() => setSelectedTemplate(key)}
              >
                <img
                  src={`/api/storage/${data.storage_key}`}
                  alt={`${key} variant`}
                />
                <span>{TEMPLATES.find((t) => t.key === key)?.label || key}</span>
              </button>
            ))}
        </div>
      )}
    </div>
  );
}
