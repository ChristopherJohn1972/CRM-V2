import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getCampaign, updateCampaign } from '../../api/campaigns';
import PageHeader from '../../components/PageHeader';
import ErrorState from '../../components/ErrorState';
import { formatEnumLabel } from '../../utils/format';
import { CAMPAIGN_STATUS_LABELS, CAMPAIGN_TYPE_LABELS } from '../../utils/constants';

const CAMPAIGN_TYPES = Object.entries(CAMPAIGN_TYPE_LABELS).map(([value, label]) => ({ value, label }));

export default function EditCampaignPage() {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({
    name: '',
    description: '',
    campaign_type: '',
    status: '',
    start_date: '',
    end_date: '',
  });

  useEffect(() => { loadCampaign(); }, [campaignId]);

  async function loadCampaign() {
    setLoading(true);
    setError(null);
    try {
      const data = await getCampaign(campaignId);
      setForm({
        name: data.name || '',
        description: data.description || '',
        campaign_type: data.campaign_type || '',
        status: data.status || '',
        start_date: data.start_date || '',
        end_date: data.end_date || '',
      });
    } catch (err) {
      setError(err.message || 'Failed to load campaign');
    } finally {
      setLoading(false);
    }
  }

  function handleChange(field, value) {
    setForm(prev => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.name.trim()) {
      setError('Campaign name is required.');
      return;
    }
    if (form.start_date && form.end_date && form.end_date < form.start_date) {
      setError('End date cannot precede start date.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload = {};
      if (form.name !== '') payload.name = form.name;
      if (form.description !== '') payload.description = form.description;
      if (form.campaign_type !== '') payload.campaign_type = form.campaign_type;
      if (form.status !== '') payload.status = form.status;
      if (form.start_date !== '') payload.start_date = form.start_date || null;
      if (form.end_date !== '') payload.end_date = form.end_date || null;
      await updateCampaign(campaignId, payload);
      navigate(`/campaigns/${campaignId}`);
    } catch (err) {
      setError(err.message || 'Failed to update campaign');
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="page"><div style={{ padding: 40, textAlign: 'center', color: '#6B7280' }}>Loading...</div></div>;
  if (error && !form.name) return <div className="page"><ErrorState message={error} onRetry={loadCampaign} /></div>;

  return (
    <div className="page">
      <PageHeader
        title="Edit Campaign"
        subtitle={form.name}
        actions={
          <Link to={`/campaigns/${campaignId}`} className="btn btn--secondary">
            Cancel
          </Link>
        }
      />

      {error && <div className="alert alert--error">{error}</div>}

      <form onSubmit={handleSubmit} style={{ maxWidth: 600 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Campaign Name *
            </label>
            <input
              className="field__input"
              value={form.name}
              onChange={e => handleChange('name', e.target.value)}
              required
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Campaign Type
            </label>
            <select
              className="field__input"
              value={form.campaign_type}
              onChange={e => handleChange('campaign_type', e.target.value)}
            >
              <option value="">Select type</option>
              {CAMPAIGN_TYPES.map(t => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Status
            </label>
            <select
              className="field__input"
              value={form.status}
              onChange={e => handleChange('status', e.target.value)}
            >
              {Object.entries(CAMPAIGN_STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Start Date
              </label>
              <input
                className="field__input"
                type="date"
                value={form.start_date}
                onChange={e => handleChange('start_date', e.target.value)}
              />
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                End Date
              </label>
              <input
                className="field__input"
                type="date"
                value={form.end_date}
                onChange={e => handleChange('end_date', e.target.value)}
              />
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Description
            </label>
            <textarea
              className="field__input"
              rows={4}
              value={form.description}
              onChange={e => handleChange('description', e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', gap: 8, paddingTop: 16, borderTop: '1px solid #e5e7eb' }}>
            <button className="btn btn--primary" type="submit" disabled={saving}>
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
            <Link to={`/campaigns/${campaignId}`} className="btn btn--secondary">Cancel</Link>
          </div>
        </div>
      </form>
    </div>
  );
}
