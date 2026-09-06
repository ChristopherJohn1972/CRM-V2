import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createOperator, listRoles, getRightsCatalogue } from '../../api/iam';
import PageHeader from '../../components/PageHeader';
import Button from '../../components/Button';
import Field from '../../components/Field';
import FormSection from '../../components/FormSection';
import AccessMatrix from '../../components/AccessMatrix';
import { catalogueByCode, roleCodeToPreview, operatorDisplayName } from '../../utils/iam';
import { OPERATOR_STATUS } from '../../utils/constants';

const EMPTY_FORM = {
  username: '',
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  department_id: '',
  team_id: '',
  role_codes: [],
  status: 'ACTIVE',
};

export function AddOperatorPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [roles, setRoles] = useState([]);
  const [catalogByCode, setCatalogByCode] = useState(null);
  const [errors, setErrors] = useState({});
  const [banner, setBanner] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([listRoles(), getRightsCatalogue()]).then(([rolesRes, catalogRes]) => {
      if (cancelled) return;
      if (rolesRes.status === 'fulfilled') setRoles(rolesRes.value.roles || []);
      setCatalogByCode(catalogueByCode(catalogRes.status === 'fulfilled' ? catalogRes.value.permissions : []));
    });
    return () => { cancelled = true; };
  }, []);

  const rolesById = useMemo(() => new Map(roles.map((r) => [r.code, r])), [roles]);

  const preview = useMemo(
    () => (catalogByCode ? roleCodeToPreview(form.role_codes, rolesById, catalogByCode) : {}),
    [form.role_codes, rolesById, catalogByCode],
  );
  const previewCount = Object.values(preview).reduce((n, items) => n + items.length, 0);

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

  const toggleRole = (code) => {
    setForm((f) => ({
      ...f,
      role_codes: f.role_codes.includes(code)
        ? f.role_codes.filter((c) => c !== code)
        : [...f.role_codes, code],
    }));
  };

  const submit = async (e) => {
    e.preventDefault();
    setBanner(null);

    const problems = {};
    if (!form.username.trim()) problems.username = 'Username is required.';
    if (!form.first_name.trim()) problems.first_name = 'First name is required.';
    if (!form.last_name.trim()) problems.last_name = 'Last name is required.';
    if (!form.email.trim()) problems.email = 'Email is required.';

    const payload = {
      username: form.username.trim(),
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim() || null,
      department_id: form.department_id ? Number(form.department_id) : null,
      team_id: form.team_id ? Number(form.team_id) : null,
      status: form.status,
      role_codes: form.role_codes,
    };

    if (Object.keys(problems).length) {
      setErrors(problems);
      return;
    }

    setSubmitting(true);
    try {
      const res = await createOperator(payload);
      setCreated({ ...res, displayName: operatorDisplayName(res.operator) });
    } catch (err) {
      setBanner(err.message || 'Could not create the operator.');
      if (err.fieldErrors) setErrors(err.fieldErrors);
    } finally {
      setSubmitting(false);
    }
  };

  if (created) {
    const operator = created.operator;
    return (
      <div className="page">
        <div className="table-wrap" style={{ maxWidth: 600, margin: '8vh auto' }}>
          <div className="card">
            <div className="card__header">
              <h2 className="card__title">Operator created</h2>
            </div>
            <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <p>Operator <strong>{created.displayName}</strong> (@{operator.username}) is ready to sign in.</p>

              <div className="card">
                <div className="card__header"><h3 className="card__title">Temporary password</h3></div>
                <div className="card__body">
                  <code className="temp-password" style={{ fontSize: 16, fontWeight: 600, wordBreak: 'break-all' }}>
                    {created.temporary_password}
                  </code>
                  <p className="field__hint" style={{ marginTop: 8 }}>
                    Shown only once. Share it securely with the operator and require a change on first sign-in.
                  </p>
                </div>
              </div>

              {created.rights_preview && created.rights_preview.length > 0 && (
                <div>
                  <p className="field__hint" style={{ marginBottom: 8 }}>
                    Standard rights granted by the selected roles ({created.rights_preview.length}).
                  </p>
                  <AccessMatrix
                    rightsByResource={roleCodeToPreview(
                      operator.role_codes,
                      new Map(roles.map((r) => [r.code, r])),
                      catalogueByCode(created.rights_preview.map((p) => ({ code: p.code, name: p.name, resource: p.resource, action: p.action, description: '' }))),
                    )}
                    dense
                  />
                </div>
              )}
            </div>
            <div className="card__footer" style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <Button variant="secondary" onClick={() => navigate('/operators')}>Back to Operators</Button>
              <Button variant="primary" onClick={() => navigate(`/operators/${operator.user_id}/access-review`)}>
                Open Access Review
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader
        title="Add Operator"
        subtitle="Create an internal CRM user and assign roles. Direct exceptions are added on the operator profile after creation."
        breadcrumbs={[{ label: 'Operators', to: '/operators' }, { label: 'Add Operator' }]}
      />

      <form className="form" onSubmit={submit} noValidate>
        {banner && <div className="form-error-banner" role="alert">{banner}</div>}

        <FormSection title="Identity" description="Sign-in credentials and personal name.">
          <Field label="Username" required htmlFor="op-username" error={errors} errorKey="username">
            <input id="op-username" autoComplete="off" className="field__input" value={form.username} onChange={set('username')} />
          </Field>
          <Field label="Status" htmlFor="op-status">
            <select id="op-status" className="field__input" value={form.status} onChange={set('status')}>
              {Object.entries(OPERATOR_STATUS).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </Field>
          <Field label="First name" required htmlFor="op-first" error={errors} errorKey="first_name">
            <input id="op-first" className="field__input" value={form.first_name} onChange={set('first_name')} />
          </Field>
          <Field label="Last name" required htmlFor="op-last" error={errors} errorKey="last_name">
            <input id="op-last" className="field__input" value={form.last_name} onChange={set('last_name')} />
          </Field>
        </FormSection>

        <FormSection title="Contact">
          <Field label="Email" required htmlFor="op-email" error={errors} errorKey="email">
            <input id="op-email" type="email" className="field__input" value={form.email} onChange={set('email')} />
          </Field>
          <Field label="Phone" htmlFor="op-phone" error={errors} errorKey="phone">
            <input id="op-phone" className="field__input" value={form.phone} onChange={set('phone')} />
          </Field>
        </FormSection>

        <FormSection title="Organisation" description="Department and team IDs are verified by the backend on save.">
          <Field label="Department ID" htmlFor="op-dept" hint="The departments module is not yet exposed over the API.">
            <input id="op-dept" type="number" min="1" className="field__input" value={form.department_id} onChange={set('department_id')} />
          </Field>
          <Field label="Team ID" htmlFor="op-team">
            <input id="op-team" type="number" min="1" className="field__input" value={form.team_id} onChange={set('team_id')} />
          </Field>
        </FormSection>

        <FormSection title="Roles" description="Reusable permission bundles. One or more roles can be assigned.">
          <div className="role-select">
            {roles.length === 0 && <p className="cell-secondary">Loading roles…</p>}
            {roles.map((role) => (
              <label key={role.role_id} className={`role-select__option${form.role_codes.includes(role.code) ? ' is-selected' : ''}`}>
                <input
                  type="checkbox"
                  checked={form.role_codes.includes(role.code)}
                  onChange={() => toggleRole(role.code)}
                />
                <span className="role-select__main">
                  <span className="role-select__name">{role.name}</span>
                  <span className="cell-secondary">{role.description || role.code}</span>
                </span>
                <span className="badge badge--neutral badge--small">{role.permission_codes.length} rights</span>
              </label>
            ))}
          </div>
        </FormSection>

        <FormSection
          title="Rights preview"
          description="Live preview of the standard rights your selected roles will grant. Direct exceptions and scope are reviewed per operator."
        >
          {form.role_codes.length === 0 ? (
            <p className="cell-secondary">Select at least one role to preview its rights.</p>
          ) : previewCount === 0 ? (
            <p className="cell-secondary">The selected roles grant no rights.</p>
          ) : (
            <AccessMatrix rightsByResource={preview} dense />
          )}
        </FormSection>

        <div className="form-actions">
          <Button variant="secondary" onClick={() => navigate('/operators')} disabled={submitting}>Cancel</Button>
          <Button type="submit" variant="primary" loading={submitting}>Create Operator</Button>
        </div>
      </form>
    </div>
  );
}

export default AddOperatorPage;
