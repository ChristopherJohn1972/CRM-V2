import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  getRole,
  updateRole,
  listOperators,
  listRoles,
  createRole,
  setOperatorRoles,
} from '../../api/iam';
import PageHeader from '../../components/PageHeader';
import Button from '../../components/Button';
import Modal from '../../components/Modal';
import StatusBadge from '../../components/StatusBadge';
import ScopeBadge from '../../components/ScopeBadge';
import ErrorState from '../../components/ErrorState';
import EmptyState from '../../components/EmptyState';
import RoleForm from './RoleForm';
import UnsavedChangesBlocker from '../../components/UnsavedChangesBlocker';
import { useToast } from '../../components/Toast';
import { buildDuplicateRolePayload, operatorDisplayName } from '../../utils/iam';
import { formatDateTime } from '../../utils/format';
import { OPERATOR_STATUS, OPERATOR_STATUS_VARIANT } from '../../utils/constants';

function AssignedOperatorsTable({ operators, busy, onManage }) {
  if (operators.length === 0) {
    return (
      <EmptyState
        title="No operators assigned"
        body="Assign this role to operators from the operator profile, or use Manage operators."
        action={<Button variant="secondary" onClick={onManage}>Manage operators</Button>}
      />
    );
  }
  return (
    <>
      <div className="table-wrap">
        <table className="data-table data-table--desktop">
          <thead>
            <tr>
              <th>Operator</th>
              <th>Username</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {operators.map((op) => (
              <tr key={op.user_id}>
                <td><Link className="data-table__accent" to={`/operators/${op.user_id}`}>{operatorDisplayName(op)}</Link></td>
                <td><span className="cell-secondary">@{op.username}</span></td>
                <td>
                  <StatusBadge variant={OPERATOR_STATUS_VARIANT[op.status] || 'neutral'}>
                    {OPERATOR_STATUS[op.status] || op.status}
                  </StatusBadge>
                </td>
                <td><Link className="btn btn--secondary btn--small" to={`/operators/${op.user_id}`}>View profile</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: 12 }}>
        <Button variant="secondary" onClick={onManage} disabled={busy}>Manage operators</Button>
      </div>
    </>
  );
}

function ManageOperatorsModal({ role, operators, open, onClose, onSaved }) {
  const [selected, setSelected] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const { notify } = useToast();

  useEffect(() => {
    if (!open) return;
    const next = {};
    for (const op of operators) next[op.user_id] = op.role_codes.includes(role.code);
    setSelected(next);
    setError(null);
  }, [open, operators, role.code]);

  const toggle = (userId) => {
    setSelected((prev) => ({ ...prev, [userId]: !prev[userId] }));
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    const changes = operators.filter((op) => selected[op.user_id] !== op.role_codes.includes(role.code));
    const failures = [];
    for (const op of changes) {
      const newCodes = selected[op.user_id]
        ? [...new Set([...op.role_codes, role.code])]
        : op.role_codes.filter((c) => c !== role.code);
      try {
        await setOperatorRoles(op.user_id, newCodes);
      } catch {
        failures.push(op);
      }
    }
    setSaving(false);
    if (failures.length > 0) {
      setError(`${failures.length} of ${changes.length} changes could not be saved.`);
      return;
    }
    notify('Assignments saved', { message: `Role "${role.name}" now applies to the selected operators.`, variant: 'success' });
    onSaved();
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Manage operators — ${role.name}`}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button variant="primary" onClick={save} loading={saving}>Save assignments</Button>
        </>
      )}
    >
      {error && <div className="form-error-banner" role="alert">{error}</div>}
      {operators.length === 0 ? (
        <p className="cell-secondary">No operators exist yet.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 380, overflow: 'auto' }}>
          {operators.map((op) => (
            <label key={op.user_id} className="role-select__option">
              <input type="checkbox" checked={selected[op.user_id] || false} onChange={() => toggle(op.user_id)} />
              <span className="role-select__main">
                <span className="role-select__name">{operatorDisplayName(op)}</span>
                <span className="cell-secondary">@{op.username}</span>
              </span>
              <StatusBadge variant={OPERATOR_STATUS_VARIANT[op.status] || 'neutral'}>
                {OPERATOR_STATUS[op.status] || op.status}
              </StatusBadge>
            </label>
          ))}
        </div>
      )}
    </Modal>
  );
}

export function RoleDetailPage() {
  const { roleId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { notify } = useToast();
  const [role, setRole] = useState(null);
  const [operators, setOperators] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [banner, setBanner] = useState(null);
  const [confirmAction, setConfirmAction] = useState(null);
  const [manageOpen, setManageOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [roleRes, opsRes] = await Promise.all([
        getRole(roleId),
        listOperators().catch(() => ({ operators: [] })),
      ]);
      setRole(roleRes);
      setOperators(opsRes.operators || []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [roleId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (location.state?.message) {
      setBanner({ kind: 'success', text: location.state.message });
      navigate(location.pathname.replace(/\/+$/, ''), { replace: true, state: {} });
    }
  }, [location, navigate]);

  const assignedOperators = useMemo(
    () => (role ? operators.filter((op) => op.role_codes.includes(role.code)) : []),
    [role, operators],
  );

  const submit = async (payload) => {
    setSubmitting(true);
    setBanner(null);
    try {
      const updated = await updateRole(roleId, payload);
      setRole(updated);
      setDirty(false);
      const count = (updated.permission_codes || []).length;
      setBanner({ kind: 'success', text: `Role permissions saved successfully. ${count} right${count === 1 ? '' : 's'} assigned to ${updated.name}.` });
      notify('Role saved', { message: `${count} right${count === 1 ? '' : 's'} assigned.`, variant: 'success' });
    } catch (err) {
      const msg = err.status === 403
        ? 'You do not have permission to modify this role.'
        : err.message || 'Unable to save role permissions. Try again.';
      setBanner({ kind: 'error', text: msg });
      notify('Save failed', { message: msg, variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  const duplicate = async () => {
    setSubmitting(true);
    try {
      const res = await listRoles();
      const existingCodes = res.roles.map((r) => r.code);
      const copy = await createRole(buildDuplicateRolePayload(role, existingCodes));
      notify('Role duplicated', { message: 'Permissions and scope were copied. Operator assignments were not copied.', variant: 'success' });
      navigate(`/roles/${copy.role_id}`, { state: { message: `Role "${copy.name}" created from "${role.name}". Permissions and scope were copied; operator assignments were not.` } });
    } catch (err) {
      setBanner({ kind: 'error', text: err.message || 'Could not duplicate the role.' });
      setSubmitting(false);
    }
  };

  const toggleActive = async () => {
    setSubmitting(true);
    try {
      const updated = await updateRole(roleId, { is_active: !role.is_active });
      setRole(updated);
      setConfirmAction(null);
      setBanner({
        kind: 'success',
        text: updated.is_active ? 'Role activated.' : 'Role deactivated. It can no longer be assigned to new operators; existing assignments remain.',
      });
      notify(updated.is_active ? 'Role activated' : 'Role deactivated', { variant: 'success' });
    } catch (err) {
      setBanner({ kind: 'error', text: err.message || 'Could not update the role status.' });
      setConfirmAction(null);
    } finally {
      setSubmitting(false);
    }
  };

  if (error) {
    return <ErrorState title="Could not load role" body={error.message} onRetry={load} />;
  }
  if (loading || !role) {
    return <p className="cell-secondary">Loading role…</p>;
  }

  const isSystem = role.is_system_role;

  return (
    <div className="page">
      <PageHeader
        title={role.name}
        subtitle={<code>{role.code}</code>}
        breadcrumbs={[{ label: 'Roles', to: '/roles' }, { label: role.name }]}
        actions={(
          <>
            <Button
              variant="secondary"
              onClick={() => setConfirmAction('duplicate')}
              disabled={submitting}
              title={isSystem ? 'System roles can be duplicated.' : undefined}
            >
              Duplicate
            </Button>
            <Button
              variant="secondary"
              onClick={() => setConfirmAction('toggle')}
              disabled={submitting || isSystem}
              title={isSystem ? 'System roles cannot be deactivated.' : undefined}
            >
              {role.is_active ? 'Deactivate' : 'Activate'}
            </Button>
            <Button variant="primary" onClick={() => navigate('/roles')}>Back to Roles</Button>
          </>
        )}
      />

      {banner && (
        <div className={banner.kind === 'success' ? 'form-success-banner' : 'form-error-banner'} role="status">
          {banner.text}
        </div>
      )}

      <div className="c360-header__meta" style={{ marginBottom: 20 }}>
        <StatusBadge variant={role.is_active ? 'success' : 'muted'}>{role.is_active ? 'Active' : 'Inactive'}</StatusBadge>
        {isSystem && <span className="badge badge--info">Protected system role</span>}
        <ScopeBadge scope={role.effective_scope} showMeaning />
        <span className="badge badge--neutral">{role.permission_codes.length} permissions</span>
        <span className="badge badge--neutral">{assignedOperators.length} operators</span>
      </div>

      {role.created_at && (
        <p className="field__hint" style={{ marginBottom: 20 }}>
          Created {formatDateTime(role.created_at)}{role.updated_at && role.updated_at !== role.created_at ? ` · last updated ${formatDateTime(role.updated_at)}` : ''}.
        </p>
      )}

      <div style={{ marginTop: 20 }}>
        <RoleForm
          initial={role}
          submitting={submitting}
          onSubmit={submit}
          onCancel={() => navigate('/roles')}
          onDirtyChange={setDirty}
        />
      </div>

      <div className="table-wrap" style={{ marginTop: 24 }}>
        <h3 className="access-matrix__resource">Assigned operators</h3>
        <div style={{ padding: 'var(--space-5)' }}>
          <AssignedOperatorsTable
            operators={assignedOperators}
            busy={submitting}
            onManage={() => setManageOpen(true)}
          />
        </div>
      </div>

      <ManageOperatorsModal
        role={role}
        operators={operators}
        open={manageOpen}
        onClose={() => setManageOpen(false)}
        onSaved={load}
      />

      <UnsavedChangesBlocker when={dirty} />

      <Modal
        open={confirmAction === 'duplicate'}
        onClose={() => setConfirmAction(null)}
        title="Duplicate role"
        footer={(
          <>
            <Button variant="secondary" onClick={() => setConfirmAction(null)}>Cancel</Button>
            <Button variant="primary" onClick={duplicate} loading={submitting}>Duplicate role</Button>
          </>
        )}
      >
        <p>
          Creates <strong>{role.name} (Copy)</strong> with the same permissions and scope.
          Operator assignments are <strong>not</strong> copied.
        </p>
      </Modal>

      <Modal
        open={confirmAction === 'toggle'}
        onClose={() => setConfirmAction(null)}
        title={role.is_active ? 'Deactivate role' : 'Activate role'}
        footer={(
          <>
            <Button variant="secondary" onClick={() => setConfirmAction(null)}>Cancel</Button>
            <Button variant={role.is_active ? 'danger' : 'primary'} onClick={toggleActive} loading={submitting}>
              {role.is_active ? 'Deactivate role' : 'Activate role'}
            </Button>
          </>
        )}
      >
        {role.is_active ? (
          <p>
            <strong>{role.name}</strong> will no longer be available for new assignments.
            Existing operator assignments and history are kept.
          </p>
        ) : (
          <p>Reactivate <strong>{role.name}</strong> so it can be assigned to operators again.</p>
        )}
      </Modal>
    </div>
  );
}

export default RoleDetailPage;