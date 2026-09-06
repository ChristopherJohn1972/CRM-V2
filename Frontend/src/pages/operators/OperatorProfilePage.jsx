import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  getOperator,
  updateOperator,
  listRoles,
  setOperatorRoles,
  getOperatorDirectPermissions,
  setOperatorDirectPermission,
  revokeOperatorDirectPermission,
  getRightsCatalogue,
} from '../../api/iam';
import PageHeader from '../../components/PageHeader';
import Button from '../../components/Button';
import Field from '../../components/Field';
import Tabs from '../../components/Tabs';
import StatusBadge from '../../components/StatusBadge';
import EffectBadge from '../../components/EffectBadge';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import { catalogueByCode, operatorDisplayName } from '../../utils/iam';
import { OPERATOR_STATUS, OPERATOR_STATUS_VARIANT } from '../../utils/constants';
import { formatDateTime } from '../../utils/format';

function IdentityPanel({ operator, onUpdated }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [errors, setErrors] = useState({});
  const [banner, setBanner] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setForm({
      first_name: operator.first_name || '',
      last_name: operator.last_name || '',
      phone: operator.phone || '',
      department_id: operator.department_id ?? '',
      team_id: operator.team_id ?? '',
      status: operator.status || 'ACTIVE',
    });
  }, [operator]);

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

  const save = async (e) => {
    e.preventDefault();
    setBanner(null);
    setSaving(true);
    try {
      const payload = {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        phone: form.phone.trim() || null,
        department_id: form.department_id ? Number(form.department_id) : null,
        team_id: form.team_id ? Number(form.team_id) : null,
        status: form.status,
      };
      const updated = await updateOperator(operator.user_id, payload);
      onUpdated(updated);
      setEditing(false);
    } catch (err) {
      setBanner(err.message || 'Could not save changes.');
      if (err.fieldErrors) setErrors(err.fieldErrors);
    } finally {
      setSaving(false);
    }
  };

  if (!editing) {
    return (
      <div className="form">
        <div className="def-list">
          <dt>Username</dt><dd>@{operator.username}</dd>
          <dt>Email</dt><dd>{operator.email || '—'}</dd>
          <dt>Phone</dt><dd>{operator.phone || '—'}</dd>
          <dt>Department ID</dt><dd>{operator.department_id ?? '—'}</dd>
          <dt>Team ID</dt><dd>{operator.team_id ?? '—'}</dd>
          <dt>Status</dt>
          <dd>
            <StatusBadge variant={OPERATOR_STATUS_VARIANT[operator.status] || 'neutral'}>
              {OPERATOR_STATUS[operator.status] || operator.status}
            </StatusBadge>
          </dd>
          <dt>Created</dt><dd>{formatDateTime(operator.created_at)}</dd>
          <dt>Last updated</dt><dd>{formatDateTime(operator.updated_at)}</dd>
        </div>
        <div className="form-actions">
          <Button variant="secondary" onClick={() => setEditing(true)}>Edit identity</Button>
        </div>
      </div>
    );
  }

  return (
    <form className="form" onSubmit={save} noValidate>
      {banner && <div className="form-error-banner" role="alert">{banner}</div>}
      <div className="form-grid">
        <Field label="First name" required htmlFor="op-edit-first" error={errors} errorKey="first_name">
          <input id="op-edit-first" className="field__input" value={form.first_name} onChange={set('first_name')} />
        </Field>
        <Field label="Last name" required htmlFor="op-edit-last" error={errors} errorKey="last_name">
          <input id="op-edit-last" className="field__input" value={form.last_name} onChange={set('last_name')} />
        </Field>
        <Field label="Phone" htmlFor="op-edit-phone" error={errors} errorKey="phone">
          <input id="op-edit-phone" className="field__input" value={form.phone} onChange={set('phone')} />
        </Field>
        <Field label="Status" htmlFor="op-edit-status" error={errors} errorKey="status">
          <select id="op-edit-status" className="field__input" value={form.status} onChange={set('status')}>
            {Object.entries(OPERATOR_STATUS).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </Field>
        <Field label="Department ID" htmlFor="op-edit-dept" error={errors} errorKey="department_id">
          <input id="op-edit-dept" type="number" min="1" className="field__input" value={form.department_id} onChange={set('department_id')} />
        </Field>
        <Field label="Team ID" htmlFor="op-edit-team" error={errors} errorKey="team_id">
          <input id="op-edit-team" type="number" min="1" className="field__input" value={form.team_id} onChange={set('team_id')} />
        </Field>
      </div>
      <div className="form-actions">
        <Button variant="secondary" onClick={() => setEditing(false)} disabled={saving}>Cancel</Button>
        <Button type="submit" variant="primary" loading={saving}>Save identity</Button>
      </div>
    </form>
  );
}

function RolesPanel({ operator, onUpdated }) {
  const [roles, setRoles] = useState([]);
  const [selected, setSelected] = useState([]);
  const [banner, setBanner] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    listRoles().then((res) => setRoles(res.roles || [])).catch(() => setRoles([]));
  }, []);

  useEffect(() => {
    setSelected(operator.role_codes || []);
  }, [operator]);

  const toggle = (code) => {
    setSelected((prev) => (prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]));
  };

  const save = async () => {
    setBanner(null);
    setSaving(true);
    try {
      const res = await setOperatorRoles(operator.user_id, selected);
      onUpdated({ ...operator, role_codes: res.role_codes });
    } catch (err) {
      setBanner(err.message || 'Could not update roles.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="form">
      {banner && <div className="form-error-banner" role="alert">{banner}</div>}
      <p className="field__hint" style={{ marginBottom: 12 }}>
        Assigning roles replaces the current set. Effective scope for this operator: <strong>{operator.effective_scope || 'NONE'}</strong>.
      </p>
      <div className="role-select">
        {roles.length === 0 && <p className="cell-secondary">Loading roles…</p>}
        {roles.map((role) => (
          <label key={role.role_id} className={`role-select__option${selected.includes(role.code) ? ' is-selected' : ''}`}>
            <input type="checkbox" checked={selected.includes(role.code)} onChange={() => toggle(role.code)} />
            <span className="role-select__main">
              <span className="role-select__name">{role.name}</span>
              <span className="cell-secondary">{role.description || role.code}</span>
            </span>
            <span className="badge badge--neutral badge--small">{role.permission_codes.length} rights · {role.effective_scope || 'NONE'}</span>
          </label>
        ))}
      </div>
      <div className="form-actions">
        <Button variant="primary" onClick={save} loading={saving}>Save roles</Button>
      </div>
    </div>
  );
}

function DirectRightsPanel({ operator }) {
  const [direct, setDirect] = useState([]);
  const [catalogByCode, setCatalogByCode] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({ permission_code: '', effect: 'ALLOW', reason: '' });
  const [banner, setBanner] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getOperatorDirectPermissions(operator.user_id);
      setDirect(res.direct_permissions || []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [operator.user_id]);

  useEffect(() => {
    load();
    getRightsCatalogue()
      .then((res) => setCatalogByCode(catalogueByCode(res.permissions)))
      .catch(() => setCatalogByCode(catalogueByCode([])));
  }, [load]);

  const catalogue = useMemo(
    () => (catalogByCode ? [...catalogByCode.values()].sort((a, b) => a.resource.localeCompare(b.resource) || a.name.localeCompare(b.name)) : []),
    [catalogByCode],
  );

  const add = async (e) => {
    e.preventDefault();
    setBanner(null);
    if (!form.permission_code) {
      setBanner('Choose a right to apply the exception to.');
      return;
    }
    setSaving(true);
    try {
      await setOperatorDirectPermission(operator.user_id, {
        permission_code: form.permission_code,
        effect: form.effect,
        reason: form.reason.trim(),
      });
      setForm({ permission_code: '', effect: 'ALLOW', reason: '' });
      await load();
    } catch (err) {
      setBanner(err.message || 'Could not set the exception.');
    } finally {
      setSaving(false);
    }
  };

  const revoke = async (permissionCode) => {
    setBanner(null);
    try {
      await revokeOperatorDirectPermission(operator.user_id, permissionCode);
      await load();
    } catch (err) {
      setBanner(err.message || 'Could not revoke the exception.');
    }
  };

  return (
    <div className="form">
      {banner && <div className="form-error-banner" role="alert">{banner}</div>}

      <form className="form-section" onSubmit={add} noValidate>
        <div className="form-section__header">
          <h3 className="form-section__title">Add direct exception</h3>
          <p className="form-section__desc">
            ALLOW or DENY a single right for this operator. DENY wins over role grants. Backend-enforced.
          </p>
        </div>
        <div className="form-grid">
          <Field label="Right" required htmlFor="dp-permission">
            <select id="dp-permission" className="field__input" value={form.permission_code} onChange={(e) => setForm((f) => ({ ...f, permission_code: e.target.value }))}>
              <option value="">Select a right…</option>
              {catalogue.map((p) => (
                <option key={p.code} value={p.code}>{p.resource} · {p.name}</option>
              ))}
            </select>
          </Field>
          <Field label="Effect" htmlFor="dp-effect">
            <select id="dp-effect" className="field__input" value={form.effect} onChange={(e) => setForm((f) => ({ ...f, effect: e.target.value }))}>
              <option value="ALLOW">ALLOW</option>
              <option value="DENY">DENY</option>
            </select>
          </Field>
          <Field label="Reason" className="field--span-2" htmlFor="dp-reason" hint="The reason is audited and shown in the access review.">
            <input id="dp-reason" className="field__input" value={form.reason} onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))} />
          </Field>
        </div>
        <div className="form-actions">
          <Button type="submit" variant="primary" loading={saving}>Apply exception</Button>
        </div>
      </form>

      {error ? (
        <ErrorState title="Could not load direct rights" body={error.message} onRetry={load} />
      ) : loading && direct.length === 0 ? (
        <p className="cell-secondary">Loading direct rights…</p>
      ) : direct.length === 0 ? (
        <EmptyState title="No direct exceptions" body="This operator has no user-level ALLOW or DENY overrides. Their access comes from roles." />
      ) : (
        <table className="data-table data-table--desktop" style={{ marginTop: 20 }}>
          <thead>
            <tr>
              <th>Right</th>
              <th>Effect</th>
              <th>Reason</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {direct.map((d) => (
              <tr key={d.permission_code}>
                <td>
                  <div style={{ fontWeight: 500 }}>{d.permission_code}</div>
                  <div className="cell-secondary">{catalogByCode?.get(d.permission_code)?.name || ''}</div>
                </td>
                <td><EffectBadge effect={d.effect} /></td>
                <td><span className="cell-secondary">{d.reason || '—'}</span></td>
                <td>
                  <Button variant="secondary" size="small" onClick={() => revoke(d.permission_code)}>Revoke</Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function OperatorProfilePage() {
  const { operatorId } = useParams();
  const [operator, setOperator] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState('identity');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const op = await getOperator(operatorId);
      setOperator(op);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [operatorId]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) {
    return <ErrorState title="Could not load operator" body={error.message} onRetry={load} />;
  }
  if (loading || !operator) {
    return <p className="cell-secondary">Loading operator…</p>;
  }

  const name = operatorDisplayName(operator);
  const tabs = [
    { key: 'identity', label: 'Identity' },
    { key: 'roles', label: 'Roles', count: (operator.roles || []).length },
    { key: 'direct', label: 'Direct Rights', count: (operator.direct_permissions || []).length },
  ];

  return (
    <div className="page">
      <PageHeader
        title={name}
        subtitle={`@${operator.username} · ${operator.email || ''}`}
        breadcrumbs={[{ label: 'Operators', to: '/operators' }, { label: name }]}
        actions={(
          <Link className="btn btn--primary" to={`/operators/${operator.user_id}/access-review`}>Access Review</Link>
        )}
      />

      <div className="c360-header__meta" style={{ marginBottom: 20 }}>
        <StatusBadge variant={OPERATOR_STATUS_VARIANT[operator.status] || 'neutral'}>
          {OPERATOR_STATUS[operator.status] || operator.status}
        </StatusBadge>
        <span className="badge badge--neutral">Effective scope: {operator.effective_scope || 'NONE'}</span>
      </div>

      <Tabs tabs={tabs} activeKey={tab} onChange={setTab} />

      <div className="form" style={{ marginTop: 20 }}>
        {tab === 'identity' && <IdentityPanel operator={operator} onUpdated={(op) => setOperator(op)} />}
        {tab === 'roles' && <RolesPanel operator={operator} onUpdated={(op) => setOperator(op)} />}
        {tab === 'direct' && <DirectRightsPanel operator={operator} />}
      </div>
    </div>
  );
}

export default OperatorProfilePage;
