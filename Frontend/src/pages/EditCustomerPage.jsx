import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getCustomer, updateCustomer } from '../api/customers';
import PageHeader from '../components/PageHeader';
import Button from '../components/Button';
import Field from '../components/Field';
import FormSection from '../components/FormSection';
import ErrorState from '../components/ErrorState';
import SkeletonTable from '../components/SkeletonTable';
import { useToast } from '../components/Toast';
import { CUSTOMER_TYPES } from '../utils/constants';
import { customerDisplayName } from '../utils/customers';

function buildFormFromCustomer(customer) {
  return {
    customer_type: customer.customer_type || 'BUSINESS',
    first_name: customer.first_name || '',
    middle_name: customer.middle_name || '',
    last_name: customer.last_name || '',
    legal_name: customer.legal_name || '',
    email: customer.email || '',
    phone: customer.phone || '',
    customer_category: customer.customer_category || '',
    segment: customer.segment || '',
    industry: customer.industry || '',
    registration_number: customer.registration_number || '',
    tax_identifier: customer.tax_identifier || '',
    version: customer.version,
  };
}

export function EditCustomerPage() {
  const { customerId } = useParams();
  const id = Number(customerId);
  const navigate = useNavigate();
  const { notify } = useToast();

  const [form, setForm] = useState(null);
  const [original, setOriginal] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [errors, setErrors] = useState({});
  const [banner, setBanner] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const customer = await getCustomer(id);
      setOriginal(customer);
      setForm(buildFormFromCustomer(customer));
    } catch (err) {
      setLoadError(err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

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

  const validate = () => {
    const problems = {};
    if (form.customer_type === 'INDIVIDUAL') {
      if (!form.first_name.trim() && !form.legal_name.trim()) {
        problems.first_name = 'Individual customers require a first name or legal name.';
      }
    } else if (!form.legal_name.trim()) {
      problems.legal_name = 'Legal name is required.';
    }
    return problems;
  };

  const submit = async (e) => {
    e.preventDefault();
    setBanner(null);

    const problems = validate();
    if (Object.keys(problems).length) {
      setErrors(problems);
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        first_name: form.first_name.trim() || null,
        middle_name: form.middle_name.trim() || null,
        last_name: form.last_name.trim() || null,
        legal_name: form.legal_name.trim() || null,
        email: form.email.trim() || null,
        phone: form.phone.trim() || null,
        customer_category: form.customer_category.trim() || null,
        segment: form.segment.trim() || null,
        industry: form.industry.trim() || null,
        registration_number: form.registration_number.trim() || null,
        tax_identifier: form.tax_identifier.trim() || null,
        version: form.version,
      };

      await updateCustomer(id, payload);
      notify('Customer updated', {
        message: `${original.account_number} has been updated successfully.`,
        variant: 'success',
      });
      navigate(`/customers/${id}`);
    } catch (err) {
      setBanner(err.message || 'Could not update the customer.');
      if (err.fieldErrors) setErrors(err.fieldErrors);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="page">
        <SkeletonTable columns={3} rows={8} />
      </div>
    );
  }

  if (loadError || !form) {
    return (
      <div className="page">
        <ErrorState
          title="Could not load customer"
          body={loadError?.message || 'The customer record could not be loaded.'}
          onRetry={load}
        />
      </div>
    );
  }

  const individual = form.customer_type === 'INDIVIDUAL';

  return (
    <div className="page">
      <PageHeader
        title={`Edit ${original.account_number}`}
        subtitle={customerDisplayName(original) || original.display_name}
        breadcrumbs={[
          { label: 'Clients', to: '/clients' },
          { label: original.account_number, to: `/customers/${id}` },
          { label: 'Edit' },
        ]}
      />

      <form className="form" onSubmit={submit} noValidate style={{ maxWidth: 800 }}>
        {banner && <div className="form-error-banner" role="alert">{banner}</div>}

        <FormSection title="Customer type">
          <Field label="Customer type" required htmlFor="edit-type">
            <select id="edit-type" className="field__input" value={form.customer_type} disabled>
              {Object.entries(CUSTOMER_TYPES).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </Field>
        </FormSection>

        <FormSection title="Identity" description="The customer's legal name. This is the canonical name shown across the app.">
          {individual ? (
            <>
              <Field label="First name" required htmlFor="edit-first-name" error={errors} errorKey="first_name">
                <input id="edit-first-name" className="field__input" value={form.first_name} onChange={set('first_name')} />
              </Field>
              <Field label="Middle name" htmlFor="edit-middle-name">
                <input id="edit-middle-name" className="field__input" value={form.middle_name} onChange={set('middle_name')} />
              </Field>
              <Field label="Last name" htmlFor="edit-last-name">
                <input id="edit-last-name" className="field__input" value={form.last_name} onChange={set('last_name')} />
              </Field>
              <Field label="Legal name" htmlFor="edit-legal-name" error={errors} errorKey="legal_name" hint="Full registered name.">
                <input id="edit-legal-name" className="field__input" value={form.legal_name} onChange={set('legal_name')} />
              </Field>
            </>
          ) : (
            <Field
              label="Legal name"
              required
              htmlFor="edit-legal-name"
              error={errors}
              errorKey="legal_name"
              className="field--span-2"
              hint="The organisation's registered legal name — displayed wherever the client appears."
            >
              <input id="edit-legal-name" className="field__input" value={form.legal_name} onChange={set('legal_name')} />
            </Field>
          )}
          {!individual && (
            <Field label="Registration number" htmlFor="edit-registration" error={errors} errorKey="registration_number">
              <input id="edit-registration" className="field__input" value={form.registration_number} onChange={set('registration_number')} />
            </Field>
          )}
          {!individual && (
            <Field label="Tax identifier" htmlFor="edit-taxid" error={errors} errorKey="tax_identifier">
              <input id="edit-taxid" className="field__input" value={form.tax_identifier} onChange={set('tax_identifier')} />
            </Field>
          )}
        </FormSection>

        <FormSection title="Contact">
          <Field label="Email" htmlFor="edit-email" error={errors} errorKey="email">
            <input id="edit-email" type="email" className="field__input" value={form.email} onChange={set('email')} />
          </Field>
          <Field label="Phone" htmlFor="edit-phone" error={errors} errorKey="phone">
            <input id="edit-phone" className="field__input" value={form.phone} onChange={set('phone')} />
          </Field>
        </FormSection>

        <FormSection title="Classification">
          <Field label="Industry" htmlFor="edit-industry">
            <input id="edit-industry" className="field__input" value={form.industry} onChange={set('industry')} />
          </Field>
          <Field label="Category" htmlFor="edit-category">
            <input id="edit-category" className="field__input" value={form.customer_category} onChange={set('customer_category')} />
          </Field>
          <Field label="Segment" htmlFor="edit-segment">
            <input id="edit-segment" className="field__input" value={form.segment} onChange={set('segment')} />
          </Field>
        </FormSection>

        <div className="form-actions">
          <Button variant="secondary" onClick={() => navigate(`/customers/${id}`)} disabled={submitting}>Cancel</Button>
          <Button type="submit" variant="primary" loading={submitting}>Save Changes</Button>
        </div>
      </form>
    </div>
  );
}

export default EditCustomerPage;
