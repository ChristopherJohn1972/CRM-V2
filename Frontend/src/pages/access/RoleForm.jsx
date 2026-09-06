import { useEffect, useMemo, useState } from 'react';
import Button from '../../components/Button';
import Field from '../../components/Field';
import FormSection from '../../components/FormSection';
import { getRightsCatalogue, getScopes } from '../../api/iam';
import { groupByResource } from '../../utils/iam';
import { SCOPE_MEANINGS, SCOPE_TO_POLICY, SCOPE_HIERARCHY } from '../../utils/constants';

function PermissionChecklist({ catalogue, selected, onToggle }) {
  const grouped = useMemo(() => groupByResource(catalogue), [catalogue]);

  if (catalogue.length === 0) return <p className="cell-secondary">No rights available.</p>;

  return (
    <div className="permission-checklist">
      {Object.entries(grouped).map(([resource, perms]) => {
        const resourceSelected = perms.filter((p) => selected.includes(p.code)).length;
        const allSelected = resourceSelected === perms.length;
        const toggleResource = () => {
          if (allSelected) {
            perms.forEach((p) => onToggle(p.code, false));
          } else {
            perms.forEach((p) => onToggle(p.code, true));
          }
        };
        return (
          <fieldset key={resource} className="permission-checklist__group">
            <legend className="permission-checklist__legend">
              <label className="permission-checklist__resource">
                <input type="checkbox" checked={allSelected} onChange={toggleResource} />
                <span>{resource}</span>
                <span className="badge badge--neutral badge--small">{resourceSelected}/{perms.length}</span>
              </label>
            </legend>
            <div className="permission-checklist__items">
              {perms.map((p) => (
                <label key={p.code} className="permission-checklist__item">
                  <input
                    type="checkbox"
                    checked={selected.includes(p.code)}
                    onChange={() => onToggle(p.code)}
                  />
                  <span className="permission-checklist__item-main">
                    <span className="permission-checklist__name">{p.name}</span>
                    <code className="permission-checklist__code">{p.code}</code>
                    {p.description && <span className="cell-secondary">{p.description}</span>}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
        );
      })}
    </div>
  );
}

/**
 * Shared create/edit form for a reusable role (name + rights + scope).
 * The scope choice is translated to backend access-policy codes
 * (GLOBAL_ALL / SCOPE_OWN / SCOPE_TEAM / SCOPE_DEPARTMENT / SCOPE_ASSIGNED).
 */
export function RoleForm({ initial, submitting, onSubmit, onCancel, submitLabel = 'Save Changes', onDirtyChange }) {
  const [form, setForm] = useState({
    name: '',
    code: '',
    description: '',
    is_active: true,
    is_system_role: false,
    permission_codes: [],
    scope: 'NONE',
  });
  const [catalogue, setCatalogue] = useState([]);
  const [scopes, setScopes] = useState([]);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    getRightsCatalogue()
      .then((res) => setCatalogue(res.permissions || []))
      .catch(() => setCatalogue([]));
    getScopes()
      .then((res) => setScopes(res.scopes || []))
      .catch(() => setScopes([]));
  }, []);

  useEffect(() => {
    if (!initial) return;
    setForm({
      name: initial.name || '',
      code: initial.code || '',
      description: initial.description || '',
      is_active: initial.is_active,
      is_system_role: initial.is_system_role,
      permission_codes: initial.permission_codes || [],
      scope: initial.effective_scope || 'NONE',
    });
  }, [initial]);

  const isDirty = useMemo(() => {
    if (!initial) return Object.values(form).some((v) => (Array.isArray(v) ? v.length > 0 : Boolean(v)));
    const sameStr = (a, b) => (a || '').trim() === (b || '').trim();
    const sameArr = (a, b) => {
      const x = a || [];
      const y = b || [];
      return x.length === y.length && x.every((v) => y.includes(v));
    };
    return (
      !sameStr(form.name, initial.name) ||
      !sameStr(form.code, initial.code) ||
      !sameStr(form.description, initial.description) ||
      form.is_active !== initial.is_active ||
      form.is_system_role !== initial.is_system_role ||
      !sameArr(form.permission_codes, initial.permission_codes) ||
      form.scope !== (initial.effective_scope || 'NONE')
    );
  }, [form, initial]);

  useEffect(() => {
    onDirtyChange?.(isDirty);
  }, [isDirty, onDirtyChange]);

  const set = (key) => (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [key]: value }));
    setErrors((prev) => {
      if (!prev[key]) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const togglePermission = (code, force) => {
    setForm((f) => {
      const has = f.permission_codes.includes(code);
      const next = force === undefined ? !has : force;
      return {
        ...f,
        permission_codes: next
          ? [...f.permission_codes, code]
          : f.permission_codes.filter((c) => c !== code),
      };
    });
  };

  const submit = (e) => {
    e.preventDefault();

    const problems = {};
    if (!form.name.trim()) problems.name = 'Role name is required.';
    if (!form.code.trim()) problems.code = 'Role code is required.';

    if (Object.keys(problems).length) {
      setErrors(problems);
      return;
    }

    const accessPolicyCodes = SCOPE_TO_POLICY[form.scope]
      ? [SCOPE_TO_POLICY[form.scope]]
      : [];

    onSubmit({
      name: form.name.trim(),
      code: form.code.trim(),
      description: form.description.trim() || null,
      is_active: form.is_active,
      is_system_role: form.is_system_role,
      permission_codes: form.permission_codes,
      access_policy_codes: accessPolicyCodes,
    });
  };

  const scopeOptions = scopes.length > 0 ? scopes : SCOPE_HIERARCHY.map((code) => ({ code, meaning: SCOPE_MEANINGS[code] }));

  return (
    <form className="form" onSubmit={submit} noValidate>

      <FormSection title="Role details" description="Roles are reusable permission bundles assigned to operators.">
        <Field label="Name" required htmlFor="role-name" error={errors} errorKey="name">
          <input id="role-name" className="field__input" value={form.name} onChange={set('name')} />
        </Field>
        <Field label="Code" required htmlFor="role-code" hint="Unique machine code, e.g. sales_manager." error={errors} errorKey="code">
          <input id="role-code" autoComplete="off" className="field__input" value={form.code} onChange={set('code')} />
        </Field>
        <Field label="Description" className="field--span-2" htmlFor="role-desc">
          <input id="role-desc" className="field__input" value={form.description} onChange={set('description')} />
        </Field>
        <Field label="Active" htmlFor="role-active">
          <label className="check-row">
            <input id="role-active" type="checkbox" checked={form.is_active} onChange={set('is_active')} />
            <span>Operators can be assigned this role while it is active.</span>
          </label>
        </Field>
        <Field label="System role" htmlFor="role-system">
          <label className="check-row">
            <input id="role-system" type="checkbox" checked={form.is_system_role} onChange={set('is_system_role')} />
            <span>Mark as a protected system role.</span>
          </label>
        </Field>
      </FormSection>

      <FormSection title="Rights" description={`Grant rights to this role (${form.permission_codes.length} selected).`}>
        <PermissionChecklist
          catalogue={catalogue}
          selected={form.permission_codes}
          onToggle={togglePermission}
        />
      </FormSection>

      <FormSection title="Scope" description="The record reach the role grants. The strongest policy wins for an operator.">
        <Field label="Scope" htmlFor="role-scope">
          <select id="role-scope" className="field__input" value={form.scope} onChange={set('scope')}>
            {scopeOptions.map((s) => (
              <option key={s.code} value={s.code}>{s.code} — {s.meaning}</option>
            ))}
          </select>
        </Field>
        {form.scope === 'NONE' && (
          <p className="field__hint field__hint--warn" role="note">
            Scope NONE grants access to no records. Operators with this role can only see records they create themselves.
            Choose a scope (e.g. All, Department or Assigned) so the rights actually apply to existing records.
          </p>
        )}
      </FormSection>

      <div className="form-actions">
        <Button variant="secondary" onClick={onCancel} disabled={submitting}>Cancel</Button>
        <Button type="submit" variant="primary" loading={submitting}>{submitting ? 'Saving changes…' : submitLabel}</Button>
      </div>
    </form>
  );
}

export default RoleForm;
