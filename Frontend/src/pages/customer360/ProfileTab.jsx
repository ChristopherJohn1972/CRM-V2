import { useCallback, useEffect, useState } from 'react';
import { updateCustomer } from '../../api/customers';
import Button from '../../components/Button';
import Field from '../../components/Field';
import FormSection from '../../components/FormSection';
import RestrictedBanner from '../../components/RestrictedBanner';
import { PermissionGate } from '../../components/PermissionGate';
import { useToast } from '../../components/Toast';
import { formatDateTime } from '../../utils/format';
import { CUSTOMER_TYPES, PERMISSIONS } from '../../utils/constants';

function Row({ label, value, mask }) {
  return (
    <>
      <dt>{label}</dt>
      <dd className={mask ? 'cell-monospace' : ''}>{value || '—'}</dd>
    </>
  );
}

export function ProfileTab({ customerId, core, reloadCore, initialEdit = false }) {
  const { notify } = useToast();
  const [editMode, setEditMode] = useState(initialEdit);
  const [form, setForm] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState({});
  const [banner, setBanner] = useState(initialEdit ? 'Edits are saved only when you press “Save changes”.' : null);

  useEffect(() => {
    if (!core) return;
    setForm({
      customer_type: core.customer_type,
      first_name: core.first_name || '',
      middle_name: core.middle_name || '',
      last_name: core.last_name || '',
      legal_name: core.legal_name || '',
      email: core.email || '',
      phone: core.phone || '',
      customer_category: core.customer_category || '',
      segment: core.segment || '',
      industry: core.industry || '',
      registration_number: core.registration_number || '',
      tax_identifier: core.tax_identifier || '',
      version: core.version,
    });
    setDirty(false);
    setErrors({});
    if (!initialEdit) setBanner(null);
  }, [core, initialEdit]);

  const enterEdit = () => {
    setBanner('Edits are saved only when you press “Save changes”.');
    setEditMode(true);
  };

  const cancelEdit = () => {
    if (dirty && !window.confirm('Discard unsaved changes?')) return;
    setEditMode(false);
    setBanner(null);
    if (core) {
      setForm({
        customer_type: core.customer_type,
        first_name: core.first_name || '',
        middle_name: core.middle_name || '',
        last_name: core.last_name || '',
        legal_name: core.legal_name || '',
        email: core.email || '',
        phone: core.phone || '',
        customer_category: core.customer_category || '',
        segment: core.segment || '',
        industry: core.industry || '',
        registration_number: core.registration_number || '',
        tax_identifier: core.tax_identifier || '',
        version: core.version,
      });
      setErrors({});
    }
  };

  const handleBeforeUnload = useCallback((e) => {
    if (dirty && editMode) {
      e.preventDefault();
      e.returnValue = '';
    }
  }, [dirty, editMode]);

  useEffect(() => {
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [handleBeforeUnload]);

  if (!core) return <RestrictedBanner>This customer could not be loaded for viewing.</RestrictedBanner>;

  const set = (key) => (e) => {
    setForm((f) => ({ ...f, [key]: e.target.value, version: f.version }));
    setDirty(true);
    setBanner('You have unsaved changes.');
    setErrors((prev) => {
      if (!prev[key]) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const individual = core.customer_type === 'INDIVIDUAL';

  const handleSave = async () => {
    setSaving(true);
    setBanner(null);
    try {
      const cleaned = { ...form };
      for (const [k, v] of Object.entries(cleaned)) {
        if (typeof v === 'string' && k !== 'customer_type') cleaned[k] = v.trim() || null;
        else if (k === 'customer_type') continue;
      }
      const updated = await updateCustomer(customerId, cleaned);
      await reloadCore();
      setEditMode(false);
      notify('Customer updated', { variant: 'success' });
      void updated;
    } catch (err) {
      setBanner(err.message || 'Could not save the customer.');
      if (err.fieldErrors) setErrors(err.fieldErrors);
    } finally {
      setSaving(false);
    }
  };

  const canEdit = PERMISSIONS.CUSTOMER_UPDATE;

  return (
    <div className="form" style={{ gap: 24 }}>
      {banner && <div className="muted-banner">{banner}</div>}

      {!editMode ? (
        <>
          <section className="card">
            <div className="card__header">
              <h2 className="card__title">Account information</h2>
              <PermissionGate permission={canEdit}>
                <Button variant="secondary" size="sm" onClick={enterEdit}>Edit client</Button>
              </PermissionGate>
            </div>
            <div className="card__body">
              <dl className="def-list">
                <Row label="Account number" value={core.account_number} mask />
                <Row label="Status" value={core.status} />
                <Row label="Version" value={core.version} mask />
                <Row label="Created" value={formatDateTime(core.created_at)} />
                <Row label="Updated" value={formatDateTime(core.updated_at)} />
              </dl>
            </div>
          </section>

          <section className="card">
            <div className="card__header"><h2 className="card__title">Identity</h2></div>
            <div className="card__body">
              <dl className="def-list">
                <Row label="Customer type" value={CUSTOMER_TYPES[core.customer_type] || core.customer_type} />
                <Row label="Legal name" value={core.legal_name} />
                <Row label="First name" value={individual ? core.first_name : null} />
                <Row label="Middle name" value={individual ? core.middle_name : null} />
                <Row label="Last name" value={individual ? core.last_name : null} />
                <Row label="Registration number" value={core.registration_number} mask />
                <Row label="Tax identifier" value={core.tax_identifier} mask />
              </dl>
            </div>
          </section>

          <div className="grid-2">
            <section className="card">
              <div className="card__header"><h2 className="card__title">Contact</h2></div>
              <div className="card__body">
                <dl className="def-list">
                  <Row label="Email" value={core.email} />
                  <Row label="Phone" value={core.phone} />
                </dl>
              </div>
            </section>

            <section className="card">
              <div className="card__header"><h2 className="card__title">Classification</h2></div>
              <div className="card__body">
                <dl className="def-list">
                  <Row label="Industry" value={core.industry} />
                  <Row label="Category" value={core.customer_category} />
                  <Row label="Segment" value={core.segment} />
                </dl>
              </div>
            </section>
          </div>

          </>
      ) : (
        <form
          className="form"
          onSubmit={(e) => { e.preventDefault(); handleSave(); }}
          noValidate
        >
          {banner && <div className="form-error-banner" role="alert">{banner}</div>}

          <FormSection title="Identity">
            <Field label="Customer type" hint="Customer type cannot be changed.">
              <input className="field__input" value={CUSTOMER_TYPES[core.customer_type] || core.customer_type} disabled />
            </Field>
            <Field label="Legal name" required htmlFor="pf-legal" error={errors} errorKey="legal_name" className="field--span-2">
              <input id="pf-legal" className="field__input" value={form.legal_name || ''} onChange={set('legal_name')} />
            </Field>
            {individual && (
              <>
                <Field label="First name" htmlFor="pf-first" error={errors} errorKey="first_name">
                  <input id="pf-first" className="field__input" value={form.first_name || ''} onChange={set('first_name')} />
                </Field>
                <Field label="Middle name" htmlFor="pf-middle" error={errors} errorKey="middle_name">
                  <input id="pf-middle" className="field__input" value={form.middle_name || ''} onChange={set('middle_name')} />
                </Field>
                <Field label="Last name" htmlFor="pf-last" error={errors} errorKey="last_name">
                  <input id="pf-last" className="field__input" value={form.last_name || ''} onChange={set('last_name')} />
                </Field>
              </>
            )}
            {!individual && (
              <>
                <Field label="Registration number" htmlFor="pf-reg" error={errors} errorKey="registration_number">
                  <input id="pf-reg" className="field__input" value={form.registration_number || ''} onChange={set('registration_number')} />
                </Field>
                <Field label="Tax identifier" htmlFor="pf-tax" error={errors} errorKey="tax_identifier">
                  <input id="pf-tax" className="field__input" value={form.tax_identifier || ''} onChange={set('tax_identifier')} />
                </Field>
              </>
            )}
          </FormSection>

          <FormSection title="Contact">
            <Field label="Email" htmlFor="pf-email" error={errors} errorKey="email">
              <input id="pf-email" type="email" className="field__input" value={form.email || ''} onChange={set('email')} />
            </Field>
            <Field label="Phone" htmlFor="pf-phone" error={errors} errorKey="phone">
              <input id="pf-phone" className="field__input" value={form.phone || ''} onChange={set('phone')} />
            </Field>
          </FormSection>

          <FormSection title="Classification">
            <Field label="Industry" htmlFor="pf-industry">
              <input id="pf-industry" className="field__input" value={form.industry || ''} onChange={set('industry')} />
            </Field>
            <Field label="Category" htmlFor="pf-cat">
              <input id="pf-cat" className="field__input" value={form.customer_category || ''} onChange={set('customer_category')} />
            </Field>
            <Field label="Segment" htmlFor="pf-segment">
              <input id="pf-segment" className="field__input" value={form.segment || ''} onChange={set('segment')} />
            </Field>
          </FormSection>

          <div className="form-actions">
            <Button variant="secondary" onClick={cancelEdit} disabled={saving}>Cancel</Button>
            <Button type="submit" variant="primary" loading={saving}>Save changes</Button>
          </div>
        </form>
      )}
    </div>
  );
}

export default ProfileTab;