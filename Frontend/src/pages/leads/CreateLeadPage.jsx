import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createLead } from '../../api/leads';
import PageHeader from '../../components/PageHeader';

export default function CreateLeadPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    company: '',
    source_channel: '',
    notes: '',
    consent_given: false,
  });

  function updateField(field, value) {
    setForm(prev => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const lead = await createLead(form);
      navigate(`/leads/${lead.lead_id}`);
    } catch (err) {
      setError(err.message || 'Failed to create lead');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <PageHeader
        title="New Lead"
        subtitle="Capture a new prospect"
        actions={
          <button className="btn btn--secondary" onClick={() => navigate(-1)}>Cancel</button>
        }
      />

      <form onSubmit={handleSubmit} className="form">
        {error && <div className="form-error-banner">{error}</div>}

        <div className="form-section">
          <h3>Contact Information</h3>
          <div className="form-grid">
            <div className="field">
              <label className="field__label">First Name</label>
              <input className="field__input" value={form.first_name} onChange={(e) => updateField('first_name', e.target.value)} />
            </div>
            <div className="field">
              <label className="field__label">Last Name</label>
              <input className="field__input" value={form.last_name} onChange={(e) => updateField('last_name', e.target.value)} />
            </div>
            <div className="field">
              <label className="field__label">Email</label>
              <input className="field__input" type="email" value={form.email} onChange={(e) => updateField('email', e.target.value)} />
            </div>
            <div className="field">
              <label className="field__label">Phone</label>
              <input className="field__input" value={form.phone} onChange={(e) => updateField('phone', e.target.value)} />
            </div>
            <div className="field">
              <label className="field__label">Company</label>
              <input className="field__input" value={form.company} onChange={(e) => updateField('company', e.target.value)} />
            </div>
            <div className="field">
              <label className="field__label">Source Channel</label>
              <select className="field__input" value={form.source_channel} onChange={(e) => updateField('source_channel', e.target.value)}>
                <option value="">Select channel</option>
                <option value="WEBSITE">Website</option>
                <option value="SOCIAL">Social Media</option>
                <option value="EMAIL">Email</option>
                <option value="SMS">SMS</option>
                <option value="USSD">USSD</option>
                <option value="PORTAL">Portal</option>
                <option value="REFERRAL">Referral</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
          </div>
        </div>

        <div className="form-section">
          <h3>Additional Details</h3>
          <div className="field">
            <label className="field__label">Notes</label>
            <textarea className="field__input" rows={3} value={form.notes} onChange={(e) => updateField('notes', e.target.value)} />
          </div>
          <div className="field">
            <label className="field__label">
              <input type="checkbox" checked={form.consent_given} onChange={(e) => updateField('consent_given', e.target.checked)} />
              {' '}Consent to contact
            </label>
          </div>
        </div>

        <div className="form-actions">
          <button type="button" className="btn btn--secondary" onClick={() => navigate(-1)}>Cancel</button>
          <button type="submit" className="btn btn--primary" disabled={loading}>
            {loading ? 'Creating...' : 'Create Lead'}
          </button>
        </div>
      </form>
    </div>
  );
}
