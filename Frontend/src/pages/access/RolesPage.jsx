import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { listRoles, listOperators, createRole, updateRole } from '../../api/iam';
import PageHeader from '../../components/PageHeader';
import SearchBar from '../../components/SearchBar';
import FilterBar from '../../components/FilterBar';
import DataTable from '../../components/DataTable';
import StatusBadge from '../../components/StatusBadge';
import ScopeBadge from '../../components/ScopeBadge';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import Button from '../../components/Button';
import Modal from '../../components/Modal';
import { Menu, MenuItem, MenuLinkItem } from '../../components/Menu';
import { PermissionGate } from '../../components/PermissionGate';
import { useToast } from '../../components/Toast';
import { PERMISSIONS } from '../../utils/constants';
import { buildDuplicateRolePayload } from '../../utils/iam';
import { formatDate } from '../../utils/format';

function RoleLink({ role }) {
  return <Link className="data-table__accent" to={`/roles/${role.role_id}`}>{role.name}</Link>;
}

function SystemBadge({ role }) {
  if (!role.is_system_role) return null;
  return <span className="badge badge--info badge--small">system</span>;
}

function RoleRowActions({ role, onDuplicate, onToggleStatus }) {
  const deactivating = role.is_active;
  return (
    <Menu trigger={<button type="button" className="icon-btn" aria-label={`Actions for ${role.name}`}>⋯</button>}>
      {(close) => (
        <>
          <MenuLinkItem to={`/roles/${role.role_id}`}>View role</MenuLinkItem>
          <MenuItem onClick={() => { close(); onDuplicate(role); }} disabled={role.is_system_role}>Duplicate</MenuItem>
          <MenuItem
            onClick={() => { close(); onToggleStatus(role); }}
            disabled={role.is_system_role}
            danger={deactivating}
          >
            {deactivating ? 'Deactivate' : 'Activate'}
          </MenuItem>
        </>
      )}
    </Menu>
  );
}

function MobileRoleCard({ role, operatorCount }) {
  return (
    <div className="mobile-client-card">
      <div className="mobile-client-card__row">
        <Link className="data-table__accent" to={`/roles/${role.role_id}`}>{role.name}</Link>
        <StatusBadge variant={role.is_active ? 'success' : 'muted'}>{role.is_active ? 'Active' : 'Inactive'}</StatusBadge>
      </div>
      <div className="mobile-client-card__meta">
        <code>{role.code}</code>
        {role.is_system_role && <span>system</span>}
      </div>
      <div className="mobile-client-card__meta">
        <span>{operatorCount} operators</span>
        <span>{role.permission_codes.length} permissions</span>
        <span>Scope: {role.effective_scope || 'NONE'}</span>
      </div>
    </div>
  );
}

export function RolesPage() {
  const navigate = useNavigate();
  const { notify } = useToast();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [data, setData] = useState({ count: 0, roles: [] });
  const [operators, setOperators] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [rolesRes, opsRes] = await Promise.all([
        listRoles(),
        listOperators().catch(() => ({ operators: [] })),
      ]);
      setData(rolesRes);
      setOperators(opsRes.operators || []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const operatorCountByRole = useMemo(() => {
    const counts = {};
    for (const op of operators) {
      for (const code of op.role_codes || []) counts[code] = (counts[code] || 0) + 1;
    }
    return counts;
  }, [operators]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return data.roles.filter((r) => {
      if (status && (r.is_active ? 'ACTIVE' : 'INACTIVE') !== status) return false;
      if (!q) return true;
      return [r.name, r.code, r.description, ...(r.permission_codes || [])]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
        .includes(q);
    });
  }, [data.roles, search, status]);

  const duplicate = async (role) => {
    setBusy(true);
    try {
      const res = await listRoles();
      const existingCodes = res.roles.map((r) => r.code);
      const copy = await createRole(buildDuplicateRolePayload(role, existingCodes));
      notify('Role duplicated', { message: 'Permissions and scope copied; operator assignments were not.', variant: 'success' });
      navigate(`/roles/${copy.role_id}`, { state: { message: `Role "${copy.name}" created from "${role.name}".` } });
    } catch (err) {
      notify('Could not duplicate role', { message: err.message, variant: 'error' });
      setConfirm(null);
      setBusy(false);
    }
  };

  const toggleStatus = async (role) => {
    setBusy(true);
    try {
      const updated = await updateRole(role.role_id, { is_active: !role.is_active });
      notify(updated.is_active ? 'Role activated' : 'Role deactivated', { variant: 'success' });
      setConfirm(null);
      await load();
    } catch (err) {
      notify('Could not update role status', { message: err.message, variant: 'error' });
      setConfirm(null);
      setBusy(false);
    }
  };

  const confirmRole = confirm || {};
  const columns = [
    { key: 'name', header: 'Role', render: (r) => (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
        <RoleLink role={r} />
        <SystemBadge role={r} />
      </span>
    ) },
    { key: 'description', header: 'Description', render: (r) => <span className="cell-secondary">{r.description || '—'}</span> },
    { key: 'operators', header: 'Operators', render: (r) => <span>{operatorCountByRole[r.code] || 0}</span> },
    { key: 'rights', header: 'Permissions', render: (r) => <span>{r.permission_codes.length}</span> },
    { key: 'scope', header: 'Scope', render: (r) => <ScopeBadge scope={r.effective_scope} /> },
    { key: 'status', header: 'Status', render: (r) => (
      <StatusBadge variant={r.is_active ? 'success' : 'muted'}>{r.is_active ? 'Active' : 'Inactive'}</StatusBadge>
    ) },
    { key: 'updated_at', header: 'Updated', render: (r) => <span className="cell-secondary cell-nowrap">{formatDate(r.updated_at)}</span> },
    { key: 'actions', header: 'Actions', render: (r) => (
      <RoleRowActions role={r} onDuplicate={duplicate} onToggleStatus={toggleStatus} />
    ) },
  ];

  const addButton = (
    <PermissionGate permission={PERMISSIONS.IAM_ROLE_MANAGE}>
      <Link to="/roles/new" className="btn btn--primary">Create Role</Link>
    </PermissionGate>
  );

  return (
    <div>
      <PageHeader
        title="Roles"
        subtitle="Reusable permission bundles assigned to operators. Deactivate instead of deleting."
        actions={addButton}
      />

      <div className="toolbar">
        <div className="toolbar__search">
          <SearchBar
            value={search}
            onChange={setSearch}
            placeholder="Search roles, codes or permissions…"
            label="Search roles"
          />
        </div>
        <div className="toolbar__filters">
          <FilterBar>
            <label className="sr-only" htmlFor="role-status">Status</label>
            <select id="role-status" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
            </select>
          </FilterBar>
        </div>
      </div>

      {error ? (
        <ErrorState title="Could not load roles" body={error.message} onRetry={load} />
      ) : loading && data.roles.length === 0 ? (
        <DataTable columns={columns} rows={[]} loading />
      ) : data.roles.length === 0 ? (
        <div className="table-wrap">
          <EmptyState
            title="No roles yet"
            body="Create reusable roles to bundle permissions and scope for operators."
            action={addButton}
          />
        </div>
      ) : filtered.length === 0 ? (
        <div className="table-wrap">
          <EmptyState
            title="No roles match your search"
            body="Try adjusting your search or status filter."
            action={<Button variant="secondary" onClick={() => { setSearch(''); setStatus(''); }}>Clear filters</Button>}
          />
        </div>
      ) : (
        <>
          <DataTable columns={columns} rows={filtered} keyField="role_id" />
          <div className="mobile-clients">
            {filtered.map((r) => <MobileRoleCard key={r.role_id} role={r} operatorCount={operatorCountByRole[r.code] || 0} />)}
          </div>
        </>
      )}

      <Modal
        open={confirmRole.role != null}
        onClose={() => setConfirm(null)}
        title={confirmRole.action === 'toggle' && confirmRole.role?.is_active ? 'Deactivate role' : 'Duplicate role'}
        footer={(
          <>
            <Button variant="secondary" onClick={() => setConfirm(null)}>Cancel</Button>
            {confirmRole.action === 'toggle' ? (
              <Button
                variant={confirmRole.role?.is_active ? 'danger' : 'primary'}
                onClick={() => toggleStatus(confirmRole.role)}
                loading={busy}
              >
                {confirmRole.role?.is_active ? 'Deactivate role' : 'Activate role'}
              </Button>
            ) : (
              <Button variant="primary" onClick={() => duplicate(confirmRole.role)} loading={busy}>Duplicate role</Button>
            )}
          </>
        )}
      >
        {confirmRole.action === 'toggle' ? (
          confirmRole.role?.is_active ? (
            <p>
              <strong>{confirmRole.role?.name}</strong> will no longer be available for new assignments.
              Existing assignments are kept.
            </p>
          ) : (
            <p>Reactivate <strong>{confirmRole.role?.name}</strong> so it can be assigned again.</p>
          )
        ) : (
          <p>
            Creates <strong>{confirmRole.role?.name} (Copy)</strong> with the same permissions and scope.
            Operator assignments are <strong>not</strong> copied.
          </p>
        )}
      </Modal>
    </div>
  );
}

export default RolesPage;