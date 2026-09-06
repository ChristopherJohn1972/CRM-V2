import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { listOperators } from '../../api/iam';
import PageHeader from '../../components/PageHeader';
import SearchBar from '../../components/SearchBar';
import FilterBar from '../../components/FilterBar';
import DataTable from '../../components/DataTable';
import StatusBadge from '../../components/StatusBadge';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import { PermissionGate } from '../../components/PermissionGate';
import { PERMISSIONS, OPERATOR_STATUS, OPERATOR_STATUS_VARIANT } from '../../utils/constants';

function OperatorLink({ operator }) {
  return (
    <Link className="data-table__accent" to={`/operators/${operator.user_id}`}>
      {operator.first_name} {operator.last_name}
    </Link>
  );
}

function RoleChips({ roleCodes }) {
  if (!roleCodes || roleCodes.length === 0) return <span className="cell-secondary">No roles</span>;
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
      {roleCodes.map((code) => <span key={code} className="badge badge--neutral badge--small">{code}</span>)}
    </div>
  );
}

function MobileOperatorCard({ operator }) {
  return (
    <div className="mobile-client-card">
      <div className="mobile-client-card__row">
        <Link className="data-table__accent" to={`/operators/${operator.user_id}`}>
          {operator.first_name} {operator.last_name}
        </Link>
        <StatusBadge variant={OPERATOR_STATUS_VARIANT[operator.status] || 'neutral'}>
          {OPERATOR_STATUS[operator.status] || operator.status}
        </StatusBadge>
      </div>
      <div className="mobile-client-card__meta">
        <span>@{operator.username}</span>
      </div>
      <div className="mobile-client-card__meta">
        <span>{operator.email || 'No email'}</span>
      </div>
    </div>
  );
}

export function OperatorsPage() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [data, setData] = useState({ count: 0, operators: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listOperators();
      setData(res);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return data.operators.filter((op) => {
      if (status && op.status !== status) return false;
      if (!q) return true;
      const haystack = [op.username, op.email, op.first_name, op.last_name, op.phone, ...(op.role_codes || [])]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [data.operators, search, status]);

  const columns = [
    { key: 'name', header: 'Operator', render: (r) => <OperatorLink operator={r} /> },
    { key: 'username', header: 'Username', render: (r) => <span className="cell-secondary">@{r.username}</span> },
    { key: 'email', header: 'Email', render: (r) => <span className="cell-secondary cell-nowrap">{r.email || '—'}</span> },
    { key: 'phone', header: 'Phone', render: (r) => <span className="cell-secondary cell-nowrap">{r.phone || '—'}</span> },
    { key: 'status', header: 'Status', render: (r) => (
      <StatusBadge variant={OPERATOR_STATUS_VARIANT[r.status] || 'neutral'}>{OPERATOR_STATUS[r.status] || r.status}</StatusBadge>
    ) },
    { key: 'roles', header: 'Roles', render: (r) => <RoleChips roleCodes={r.role_codes} /> },
    { key: 'review', header: '', render: (r) => (
      <Link className="btn btn--secondary btn--small" to={`/operators/${r.user_id}/access-review`}>Access review</Link>
    ) },
  ];

  const addButton = (
    <PermissionGate permission={PERMISSIONS.IAM_USER_MANAGE}>
      <Link to="/operators/new" className="btn btn--primary">Add Operator</Link>
    </PermissionGate>
  );

  return (
    <div>
      <PageHeader
        title="Operators"
        subtitle="Internal CRM users. Assign reusable roles and review effective access."
        actions={addButton}
      />

      <div className="toolbar">
        <div className="toolbar__search">
          <SearchBar
            value={search}
            onChange={setSearch}
            placeholder="Search name, username, email, role…"
            label="Search operators"
          />
        </div>
        <div className="toolbar__filters">
          <FilterBar>
            <label className="sr-only" htmlFor="operator-status">Status</label>
            <select id="operator-status" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All statuses</option>
              {Object.entries(OPERATOR_STATUS).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </FilterBar>
        </div>
      </div>

      {error ? (
        <ErrorState title="Could not load operators" body={error.message} onRetry={load} />
      ) : loading && data.operators.length === 0 ? (
        <DataTable columns={columns} rows={[]} loading />
      ) : data.operators.length === 0 ? (
        <div className="table-wrap">
          <EmptyState
            title="No operators yet"
            body="Create the first internal user to start assigning roles and access."
            action={addButton}
          />
        </div>
      ) : filtered.length === 0 ? (
        <div className="table-wrap">
          <EmptyState title="No operators match your search" body="Try adjusting your search or status filter." />
        </div>
      ) : (
        <>
          <DataTable columns={columns} rows={filtered} keyField="user_id" />
          <div className="mobile-clients">
            {filtered.map((op) => <MobileOperatorCard key={op.user_id} operator={op} />)}
          </div>
        </>
      )}
    </div>
  );
}

export default OperatorsPage;
