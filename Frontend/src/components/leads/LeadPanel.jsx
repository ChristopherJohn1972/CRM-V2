import { useState, useEffect } from 'react';
import { getLead, createLead, updateLead, deleteLead } from '../../api/leads';

const STATUS_LABELS = {
  NEW: 'New',
  CONTACTED: 'Contacted',
  QUALIFIED: 'Qualified',
  UNQUALIFIED: 'Unqualified',
  CONVERTED: 'Converted',
  LOST: 'Lost',
};

const STATUS_COLORS = {
  NEW: '#3b82f6',
  CONTACTED: '#8b5cf6',
  QUALIFIED: '#22c55e',
  UNQUALIFIED: '#94a3b8',
  CONVERTED: '#16a34a',
  LOST: '#ef4444',
};

const SOURCE_LABELS = {
  WEBSITE: 'Website',
  SOCIAL: 'Social Media',
  EMAIL: 'Email',
  SMS: 'SMS',
  USSD: 'USSD',
  PORTAL: 'Portal',
  REFERRAL: 'Referral',
  OTHER: 'Other',
};

function getInitials(firstName, lastName) {
  const f = (firstName || '').charAt(0).toUpperCase();
  const l = (lastName || '').charAt(0).toUpperCase();
  return f + l || '?';
}

function formatDate(dateStr) {
  if (!dateStr) return '--';
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

function formatDateTime(dateStr) {
  if (!dateStr) return '--';
  return new Date(dateStr).toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function LeadPanel({ leadId, mode: initialMode, onClose, onCreated, onUpdated, onDeleted }) {
  const [mode, setMode] = useState(initialMode || 'create');
  const [lead, setLead] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
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

  useEffect(() => {
    if (leadId && (mode === 'view' || mode === 'edit')) {
      loadLead();
    }
  }, [leadId, mode]);

  useEffect(() => {
    setMode(initialMode || 'create');
  }, [initialMode, leadId]);

  async function loadLead() {
    setLoading(true);
    setError(null);
    try {
      const data = await getLead(leadId);
      setLead(data);
      setForm({
        first_name: data.first_name || '',
        last_name: data.last_name || '',
        email: data.email || '',
        phone: data.phone || '',
        company: data.company || '',
        source_channel: data.source_channel || '',
        notes: data.notes || '',
        consent_given: data.consent_given || false,
      });
    } catch (err) {
      setError(err.message || 'Failed to load lead');
    } finally {
      setLoading(false);
    }
  }

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const newLead = await createLead(form);
      onCreated?.(newLead);
      onClose?.();
    } catch (err) {
      setError(err.message || 'Failed to create lead');
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdate(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await updateLead(leadId, form);
      setLead(updated);
      setMode('view');
      onUpdated?.(updated);
    } catch (err) {
      setError(err.message || 'Failed to update lead');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm('Delete this lead? This cannot be undone.')) return;
    try {
      await deleteLead(leadId);
      onDeleted?.(leadId);
      onClose?.();
    } catch (err) {
      alert(err.message || 'Failed to delete lead');
    }
  }

  function handleClose() {
    onClose?.();
  }

  const fullName = [lead?.first_name, lead?.last_name].filter(Boolean).join(' ') || form.first_name + ' ' + form.last_name || '';

  return (
    <div className="lead-panel-overlay" onClick={handleClose}>
      <div className="lead-panel" onClick={(e) => e.stopPropagation()}>
        <div className="lead-panel__header">
          <h3 className="lead-panel__title">
            {mode === 'create' ? 'New Lead' : 'Lead Details'}
          </h3>
          <button className="lead-panel__close" onClick={handleClose}>×</button>
        </div>

        <div className="lead-panel__body">
          {loading && (
            <div className="lead-panel__loading">
              <div className="lead-panel__spinner" />
              <span>Loading lead...</span>
            </div>
          )}

          {error && !loading && (
            <div className="lead-panel__error">{error}</div>
          )}

          {/* ===================== PROFILE MODE ===================== */}
          {!loading && mode === 'view' && lead && (
            <div className="lead-profile">
              <div className="lead-profile__header">
                <div className="lead-profile__avatar" style={{ background: STATUS_COLORS[lead.status] || '#3b82f6' }}>
                  {getInitials(lead.first_name, lead.last_name)}
                </div>
                <div className="lead-profile__identity">
                  <div className="lead-profile__name">{fullName || 'Unnamed Lead'}</div>
                  <div className="lead-profile__email">{lead.email || ''}</div>
                  {lead.company && <div className="lead-profile__company">{lead.company}</div>}
                </div>
              </div>

              <div className="lead-profile__status-row">
                <span className="lead-profile__status" style={{ color: STATUS_COLORS[lead.status] || '#3b82f6' }}>
                  <span className="lead-profile__status-dot" style={{ background: STATUS_COLORS[lead.status] || '#3b82f6' }} />
                  {STATUS_LABELS[lead.status] || lead.status}
                </span>
                <span className="lead-profile__score">
                  Lead Score: <strong>{lead.qualification_score ?? '—'}</strong>
                </span>
              </div>

              <div className="lead-profile__divider" />

              <div className="lead-profile__section">
                <div className="lead-profile__section-title">Contact Information</div>
                <div className="lead-profile__cards">
                  <div className="lead-profile__card">
                    <div className="lead-profile__card-label">Email</div>
                    <div className="lead-profile__card-value">{lead.email || '—'}</div>
                  </div>
                  <div className="lead-profile__card">
                    <div className="lead-profile__card-label">Phone</div>
                    <div className="lead-profile__card-value">{lead.phone || '—'}</div>
                  </div>
                  <div className="lead-profile__card">
                    <div className="lead-profile__card-label">Company</div>
                    <div className="lead-profile__card-value">{lead.company || '—'}</div>
                  </div>
                  <div className="lead-profile__card">
                    <div className="lead-profile__card-label">Source</div>
                    <div className="lead-profile__card-value">{SOURCE_LABELS[lead.source_channel] || lead.source_channel || '—'}</div>
                  </div>
                </div>
              </div>

              <div className="lead-profile__section">
                <div className="lead-profile__section-title">Additional Information</div>
                <div className="lead-profile__meta">
                  <div className="lead-profile__meta-row">
                    <span className="lead-profile__meta-label">Created</span>
                    <span className="lead-profile__meta-value">{formatDate(lead.created_at)}</span>
                  </div>
                  <div className="lead-profile__meta-row">
                    <span className="lead-profile__meta-label">Last Updated</span>
                    <span className="lead-profile__meta-value">{formatDateTime(lead.updated_at)}</span>
                  </div>
                  <div className="lead-profile__meta-row">
                    <span className="lead-profile__meta-label">Consent</span>
                    <span className="lead-profile__meta-value">
                      {lead.consent_given ? (
                        <span className="lead-profile__consent lead-profile__consent--yes">✓ Contact permitted</span>
                      ) : (
                        <span className="lead-profile__consent lead-profile__consent--no">Not permitted</span>
                      )}
                    </span>
                  </div>
                </div>
              </div>

              <div className="lead-profile__section">
                <div className="lead-profile__section-title">Notes</div>
                <div className="lead-profile__notes">
                  {lead.notes || <span className="lead-profile__notes-empty">No notes added</span>}
                </div>
              </div>
            </div>
          )}

          {/* ===================== FORM MODE (Create / Edit) ===================== */}
          {!loading && (mode === 'create' || mode === 'edit') && (
            <form onSubmit={mode === 'create' ? handleCreate : handleUpdate} className="lead-form">
              <div className="lead-form__section">
                <div className="lead-form__section-title">Contact Information</div>
                <div className="lead-form__grid">
                  <div className="lead-form__field">
                    <label>First Name</label>
                    <input value={form.first_name} onChange={(e) => updateField('first_name', e.target.value)} required />
                  </div>
                  <div className="lead-form__field">
                    <label>Last Name</label>
                    <input value={form.last_name} onChange={(e) => updateField('last_name', e.target.value)} />
                  </div>
                  <div className="lead-form__field">
                    <label>Email</label>
                    <input type="email" value={form.email} onChange={(e) => updateField('email', e.target.value)} />
                  </div>
                  <div className="lead-form__field">
                    <label>Phone</label>
                    <input value={form.phone} onChange={(e) => updateField('phone', e.target.value)} />
                  </div>
                  <div className="lead-form__field">
                    <label>Company</label>
                    <input value={form.company} onChange={(e) => updateField('company', e.target.value)} />
                  </div>
                  <div className="lead-form__field">
                    <label>Source Channel</label>
                    <select value={form.source_channel} onChange={(e) => updateField('source_channel', e.target.value)}>
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

              <div className="lead-form__section">
                <div className="lead-form__section-title">Additional Information</div>
                <div className="lead-form__field lead-form__field--full">
                  <label>Notes</label>
                  <textarea rows={3} value={form.notes} onChange={(e) => updateField('notes', e.target.value)} />
                </div>
                <label className="lead-form__checkbox">
                  <input type="checkbox" checked={form.consent_given} onChange={(e) => updateField('consent_given', e.target.checked)} />
                  <span>Consent to contact</span>
                </label>
              </div>
            </form>
          )}
        </div>

        {/* ===================== FOOTER ===================== */}
        <div className="lead-panel__footer">
          {mode === 'view' && (
            <>
              <button className="btn btn--primary" onClick={() => setMode('edit')}>Edit Lead</button>
              <button className="btn btn--secondary" onClick={handleClose}>Close</button>
            </>
          )}
          {mode === 'create' && (
            <>
              <button className="btn btn--primary" disabled={saving} onClick={handleCreate}>
                {saving ? 'Creating...' : 'Create Lead'}
              </button>
              <button className="btn btn--secondary" onClick={handleClose}>Cancel</button>
            </>
          )}
          {mode === 'edit' && (
            <>
              <button className="btn btn--primary" disabled={saving} onClick={handleUpdate}>
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              <button className="btn btn--secondary" onClick={() => setMode('view')}>Cancel</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
