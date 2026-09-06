import { useState } from 'react';
import { createCustomer } from '../api/customers';
import Button from '../components/Button';
import { EMPTY_CUSTOMER_FORM, buildCustomerCreatePayload, validateCustomerForm } from '../utils/customerForm';
import { CUSTOMER_TYPES } from '../utils/constants';

export function AddClientForm({ onCreated, onCancel }) {
  const [form, setForm] = useState(EMPTY_CUSTOMER_FORM);
  const [errors, setErrors] = useState({});
  const [banner, setBanner] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const set = (key) => (e) => {
    setForm((f) => ({ ...f, [key]: e.target.value }));
    setErrors((prev) => {
      if (!prev[key]) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
    setBanner(null);
  };

  const individual = form.customer_type === 'INDIVIDUAL';

  const submit = async (e) => {
    e.preventDefault();
    setBanner(null);

    const problems = validateCustomerForm(form);
    if (Object.keys(problems).length) {
      setErrors(problems);
      return;
    }

    setSubmitting(true);
    try {
      const createdCustomer = await createCustomer(buildCustomerCreatePayload(form));
      onCreated(createdCustomer);
    } catch (err) {
      setBanner(err.message || 'Could not create the client.');
      if (err.fieldErrors) setErrors(err.fieldErrors);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="form form--compact" onSubmit={submit} noValidate>
      {banner && <div className="form-error-banner" role="alert">{banner}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px 16px' }}>
        <div style={{ gridColumn: '1 / -1' }}>
          <label className="field field--tight" htmlFor="cc-type">
            <span className="field__label">Customer type <span className="field__required">*</span></span>
            <select id="cc-type" className="field__input" value={form.customer_type} onChange={set('customer_type')}>
              {Object.entries(CUSTOMER_TYPES).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </label>
        </div>

        {individual ? (
          <>
            <label className="field field--tight" htmlFor="cc-first-name">
              <span className="field__label">First name <span className="field__required">*</span></span>
              {errors.first_name && <span className="field__error">{errors.first_name}</span>}
              <input id="cc-first-name" className="field__input" value={form.first_name} onChange={set('first_name')} />
            </label>
            <label className="field field--tight" htmlFor="cc-middle-name">
              <span className="field__label">Middle name</span>
              <input id="cc-middle-name" className="field__input" value={form.middle_name} onChange={set('middle_name')} />
            </label>
            <label className="field field--tight" htmlFor="cc-last-name">
              <span className="field__label">Last name</span>
              <input id="cc-last-name" className="field__input" value={form.last_name} onChange={set('last_name')} />
            </label>
            <label className="field field--tight" htmlFor="cc-legal-name">
              <span className="field__label">Legal name</span>
              {errors.legal_name && <span className="field__error">{errors.legal_name}</span>}
              <input id="cc-legal-name" className="field__input" value={form.legal_name} onChange={set('legal_name')} />
            </label>
          </>
        ) : (
          <>
            <label className="field field--tight" htmlFor="cc-legal-name" style={{ gridColumn: '1 / -1' }}>
              <span className="field__label">Legal name <span className="field__required">*</span></span>
              {errors.legal_name && <span className="field__error">{errors.legal_name}</span>}
              <input id="cc-legal-name" className="field__input" value={form.legal_name} onChange={set('legal_name')} />
            </label>
            <label className="field field--tight" htmlFor="cc-registration">
              <span className="field__label">Registration number</span>
              <input id="cc-registration" className="field__input" value={form.registration_number} onChange={set('registration_number')} />
            </label>
            <label className="field field--tight" htmlFor="cc-taxid">
              <span className="field__label">Tax identifier</span>
              <input id="cc-taxid" className="field__input" value={form.tax_identifier} onChange={set('tax_identifier')} />
            </label>
          </>
        )}

        <label className="field field--tight" htmlFor="cc-email">
          <span className="field__label">Email</span>
          {errors.email && <span className="field__error">{errors.email}</span>}
          <input id="cc-email" type="email" className="field__input" value={form.email} onChange={set('email')} />
        </label>
        <label className="field field--tight" htmlFor="cc-phone">
          <span className="field__label">Phone</span>
          {errors.phone && <span className="field__error">{errors.phone}</span>}
          <input id="cc-phone" className="field__input" value={form.phone} onChange={set('phone')} />
        </label>

        <label className="field field--tight" htmlFor="cc-industry">
          <span className="field__label">Industry</span>
          <input id="cc-industry" className="field__input" value={form.industry} onChange={set('industry')} />
        </label>
        <label className="field field--tight" htmlFor="cc-category">
          <span className="field__label">Category</span>
          <input id="cc-category" className="field__input" value={form.customer_category} onChange={set('customer_category')} />
        </label>

        <label className="field field--tight" htmlFor="cc-segment">
          <span className="field__label">Segment</span>
          <input id="cc-segment" className="field__input" value={form.segment} onChange={set('segment')} />
        </label>
        <label className="field field--tight" htmlFor="cc-address">
          <span className="field__label">Address</span>
          <input id="cc-address" className="field__input" value={form.address} onChange={set('address')} />
        </label>
      </div>

      <div className="form-actions">
        <Button variant="secondary" onClick={onCancel} disabled={submitting}>Cancel</Button>
        <Button type="submit" variant="primary" loading={submitting}>Create Client</Button>
      </div>
    </form>
  );
}

export default AddClientForm;
