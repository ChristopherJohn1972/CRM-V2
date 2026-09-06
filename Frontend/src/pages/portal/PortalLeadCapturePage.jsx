import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { createLead } from '../../api/leads';
import PageHeader from '../../components/PageHeader';

const USE_CASE_OPTIONS = ['Gaming', 'Office', 'Creator', 'Programming', 'Other'];
const BUDGET_OPTIONS = [
  { value: 'UNDER_50K', label: 'Under KES 50,000' },
  { value: '50K_200K', label: 'KES 50,000 – 200,000' },
  { value: '200K_500K', label: 'KES 200,000 – 500,000' },
  { value: '500K_1M', label: 'KES 500,000 – 1,000,000' },
  { value: 'OVER_1M', label: 'Over KES 1,000,000' },
];

export default function PortalLeadCapturePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const campaignId = searchParams.get('campaign');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone: '',
    product_interests: '', use_case: '', budget_range: '',
    notes: '', consent_given: false,
  });

  function updateField(field, value) {
    setForm(prev => ({ ...prev, [field]: value }));
  }

  function toggleUseCase(option) {
    setForm(prev => ({
      ...prev,
      use_case: prev.use_case === option ? '' : option,
    }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (submitted) return;
    if (!form.consent_given) { setError('Please accept the privacy policy to continue.'); return; }
    setLoading(true); setError(null);
    try {
      const payload = {
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        phone: form.phone || undefined,
        product_interests: form.product_interests ? form.product_interests.split(',').map(s => s.trim()).filter(Boolean) : [],
        use_case: form.use_case || undefined,
        budget_range: form.budget_range || undefined,
        notes: form.notes || undefined,
        consent_given: true,
        source_channel: 'PORTAL',
        source_campaign_id: campaignId ? Number(campaignId) : undefined,
      };
      await createLead(payload);
      setSubmitted(true);
      const qs = campaignId ? `?campaign=${campaignId}` : '';
      navigate(`/portal/leads/success${qs}`);
    } catch (err) {
      setError(err.message || 'Failed to submit. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="portal-page">
      <PageHeader title="Register Your Interest" subtitle="Tell us what you're looking for — we'll get back to you" />

      <form onSubmit={handleSubmit} className="form portal-lead-form">
        {error && <div className="form-error-banner">{error}</div>}

        <div className="form-section">
          <h3>Contact Details</h3>
          <div className="form-grid form-grid--2">
            <div className="field">
              <label className="field__label">First Name *</label>
              <input className="field__input" required value={form.first_name} onChange={(e) => updateField('first_name', e.target.value)} />
            </div>
            <div className="field">
              <label className="field__label">Last Name *</label>
              <input className="field__input" required value={form.last_name} onChange={(e) => updateField('last_name', e.target.value)} />
            </div>
            <div className="field">
              <label className="field__label">Email *</label>
              <input className="field__input" type="email" required value={form.email} onChange={(e) => updateField('email', e.target.value)} />
            </div>
            <div className="field">
              <label className="field__label">Phone</label>
              <input className="field__input" value={form.phone} onChange={(e) => updateField('phone', e.target.value)} placeholder="Optional" />
            </div>
          </div>
        </div>

        <div className="form-section">
          <h3>What are you looking for?</h3>
          <div className="field">
            <label className="field__label">Product Interests</label>
            <input className="field__input" placeholder="e.g. GPU, CPU, RAM, SSD" value={form.product_interests} onChange={(e) => updateField('product_interests', e.target.value)} />
            <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>Separate multiple products with commas</p>
          </div>

          <div className="field">
            <label className="field__label">Use Case</label>
            <div className="portal-chip-group">
              {USE_CASE_OPTIONS.map(opt => (
                <button key={opt} type="button" className={`portal-chip${form.use_case === opt ? ' is-selected' : ''}`} onClick={() => toggleUseCase(opt)}>
                  {opt}
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label className="field__label">Budget Range</label>
            <select className="field__input" value={form.budget_range} onChange={(e) => updateField('budget_range', e.target.value)}>
              <option value="">Select range</option>
              {BUDGET_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>

          <div className="field">
            <label className="field__label">Additional Notes</label>
            <textarea className="field__input" rows={3} value={form.notes} onChange={(e) => updateField('notes', e.target.value)} placeholder="Anything else you'd like us to know..." />
          </div>
        </div>

        <div className="portal-consent">
          <label className="portal-consent__check">
            <input type="checkbox" checked={form.consent_given} onChange={(e) => updateField('consent_given', e.target.checked)} />
            <span>I agree to be contacted about this interest. I understand my data will be used in accordance with the privacy policy.</span>
          </label>
          <p className="portal-consent__text">
            Your information is secure and will only be used to respond to your inquiry.
            You can request data removal at any time by contacting support.
          </p>
        </div>

        <div className="form-actions">
          <button type="button" className="btn btn--secondary" onClick={() => navigate(-1)}>Cancel</button>
          <button type="submit" className="btn btn--primary" disabled={loading || submitted}>
            {loading ? 'Submitting...' : 'Get My Recommendation'}
          </button>
        </div>
      </form>
    </div>
  );
}
