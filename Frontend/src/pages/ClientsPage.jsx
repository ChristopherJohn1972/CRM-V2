import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { listCustomers, deleteCustomer } from '../api/customers';
import { useAuth } from '../auth/AuthContext';
import PageHeader from '../components/PageHeader';
import Button from '../components/Button';
import SearchBar from '../components/SearchBar';
import FilterBar from '../components/FilterBar';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import StatusSelect from '../components/StatusSelect';
import Pagination from '../components/Pagination';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import { PermissionGate } from '../components/PermissionGate';
import { AddClientModal } from '../components/AddClientModal';
import { formatDate } from '../utils/format';
import { CUSTOMER_STATUS, CUSTOMER_TYPES, PERMISSIONS } from '../utils/constants';
import { customerDisplayName } from '../utils/customers';
import { useDebouncedValue } from '../utils/useDebouncedValue';

const SCOPE_LABELS = {
  ALL: 'All clients',
  NONE: 'Limited visibility',
  OWN: 'My clients',
  ASSIGNED: 'Assigned clients',
  TEAM: 'My team',
  DEPARTMENT: 'My department',
};

function AccountLink({ accountNumber, customerId }) {
  return <Link className="data-table__accent" to={`/customers/${customerId}`}>{accountNumber}</Link>;
}

function MobileClientCard({ customer, onDelete }) {
  const navigate = useNavigate();
  return (
    <div className="mobile-client-card">
      <div className="mobile-client-card__row">
        <Link className="data-table__accent" to={`/customers/${customer.customer_id}`}>
          {customer.account_number}
        </Link>
        <div className="table-actions">
          <button
            type="button"
            className="icon-btn icon-btn--edit"
            onClick={() => navigate(`/customers/${customer.customer_id}/edit`)}
            title="Edit"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M11.5 1.5l3 3-9 9H2.5v-3l9-9z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
          <button
            type="button"
            className="icon-btn icon-btn--delete"
            onClick={() => onDelete?.(customer)}
            title="Delete"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M5.333 4V2.667a1.333 1.333 0 011.334-1.334h2.666a1.333 1.333 0 011.334 1.334V4m2 0v9.333a1.333 1.333 0 01-1.334 1.334H4.667a1.333 1.333 0 01-1.334-1.334V4h9.334z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
        </div>
      </div>
      <div className="mobile-client-card__meta">
        <span style={{ fontWeight: 600 }}>{customerDisplayName(customer)}</span>
      </div>
      <div className="mobile-client-card__meta">
        <span>{customer.email || 'No email'}</span>
        <span>{customer.phone || 'No phone'}</span>
      </div>
    </div>
  );
}

export function ClientsPage() {
  const { user } = useAuth();
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search, 350);

  const [filters, setFilters] = useState({ status: '', customer_type: '', segment: '' });
  const [data, setData] = useState({ count: 0, results: [] });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [addOpen, setAddOpen] = useState(false);

  const scopeLabel = user?.scope ? SCOPE_LABELS[user.scope] : null;

  const segmentOptions = useMemo(() => {
    const set = new Set();
    for (const item of data.results) if (item.segment) set.add(item.segment);
    return [...set];
  }, [data.results]);

  const abortRef = useRef(null);

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const res = await listCustomers({
        search: debouncedSearch || undefined,
        status: filters.status || undefined,
        customer_type: filters.customer_type || undefined,
        segment: filters.segment || undefined,
        page,
        page_size: pageSize,
      });
      setData(res);
    } catch (err) {
      if (err.name !== 'AbortError') setError(err);
    } finally {
      if (!abortRef.current || abortRef.current.signal === controller.signal) setLoading(false);
    }
  }, [debouncedSearch, filters.status, filters.customer_type, filters.segment, page, pageSize]);

  useEffect(() => {
    load();
    return () => abortRef.current?.abort();
  }, [load]);

  const resetPage = (updater) => {
    setPage(1);
    updater();
  };

  const handleDelete = async (customer) => {
    const name = customerDisplayName(customer);
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try {
      await deleteCustomer(customer.customer_id);
      load();
    } catch (err) {
      window.alert(err.message || 'Failed to delete client.');
    }
  };

  const columns = [
    { key: 'account_number', header: 'Account', render: (r) => <AccountLink accountNumber={r.account_number} customerId={r.customer_id} /> },
    { key: 'customer', header: 'Customer', render: (r) => <span style={{ fontWeight: 500 }}>{customerDisplayName(r)}</span> },
    { key: 'customer_type', header: 'Type', render: (r) => <span className="cell-secondary">{CUSTOMER_TYPES[r.customer_type] || r.customer_type}</span> },
    { key: 'email', header: 'Email', render: (r) => <span className="cell-secondary cell-nowrap">{r.email || '—'}</span> },
    { key: 'phone', header: 'Phone', render: (r) => <span className="cell-secondary cell-nowrap">{r.phone || '—'}</span> },
    { key: 'status', header: 'Status', render: (r) => (
      <StatusBadge status={r.status}>{CUSTOMER_STATUS[r.status] || r.status}</StatusBadge>
    ) },
    { key: 'segment', header: 'Segment', render: (r) => <span className="cell-secondary">{r.segment || '—'}</span> },
    { key: 'created_at', header: 'Created', render: (r) => <span className="cell-secondary cell-nowrap">{formatDate(r.created_at)}</span> },
    { key: 'actions', header: '', render: (r) => (
      <div className="table-actions">
        <PermissionGate permission={PERMISSIONS.CUSTOMER_UPDATE}>
          <button
            type="button"
            className="icon-btn icon-btn--edit"
            onClick={(e) => { e.stopPropagation(); navigate(`/customers/${r.customer_id}/edit`); }}
            title="Edit client"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M11.5 1.5l3 3-9 9H2.5v-3l9-9z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </PermissionGate>
        <PermissionGate permission={PERMISSIONS.CUSTOMER_DELETE}>
          <button
            type="button"
            className="icon-btn icon-btn--delete"
            onClick={(e) => { e.stopPropagation(); handleDelete(r); }}
            title="Delete client"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M2 4h12M5.333 4V2.667a1.333 1.333 0 011.334-1.334h2.666a1.333 1.333 0 011.334 1.334V4m2 0v9.333a1.333 1.333 0 01-1.334 1.334H4.667a1.333 1.333 0 01-1.334-1.334V4h9.334z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </PermissionGate>
      </div>
    ) },
  ];

  const addButton = (
    <PermissionGate permission={PERMISSIONS.CUSTOMER_CREATE}>
      <Button variant="primary" onClick={() => setAddOpen(true)}>Add Client</Button>
    </PermissionGate>
  );

  const emptyTitle = debouncedSearch || filters.status || filters.customer_type || filters.segment
    ? 'No clients match your search'
    : 'No clients found';
  const emptyBody = debouncedSearch || filters.status || filters.customer_type || filters.segment
    ? 'Try adjusting your search or filters.'
    : scopeLabel && scopeLabel !== 'All clients'
      ? `No clients are available within your current access scope (${scopeLabel}). Contact an administrator to adjust your permissions.`
      : 'No client records yet. Create your first client to get started.';

  return (
    <div>
      <PageHeader
        title="Clients"
        subtitle="Search customer records by account number, name, phone or email."
        actions={addButton}
      />

      {scopeLabel && (
        <div className="c360-header__meta" style={{ marginBottom: 16 }}>
          <span className="badge badge--neutral">Visibility: {scopeLabel}</span>
        </div>
      )}

      <div className="toolbar">
        <div className="toolbar__search">
          <SearchBar
            value={search}
            onChange={(v) => { setSearch(v); }}
            placeholder="Search account number, name, phone or email…"
            label="Search clients"
          />
        </div>
        <div className="toolbar__filters">
          <FilterBar>
            <label className="sr-only" htmlFor="filter-status">Status</label>
            <StatusSelect id="filter-status" value={filters.status} onChange={(e) => resetPage(() => setFilters((f) => ({ ...f, status: e.target.value })))} />

            <label className="sr-only" htmlFor="filter-type">Customer type</label>
            <select id="filter-type" value={filters.customer_type} onChange={(e) => resetPage(() => setFilters((f) => ({ ...f, customer_type: e.target.value })))}>
              <option value="">All types</option>
              {Object.entries(CUSTOMER_TYPES).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>

            {segmentOptions.length > 0 && (
              <>
                <label className="sr-only" htmlFor="filter-segment">Segment</label>
                <select id="filter-segment" value={filters.segment} onChange={(e) => resetPage(() => setFilters((f) => ({ ...f, segment: e.target.value })))}>
                  <option value="">All segments</option>
                  {segmentOptions.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </>
            )}
          </FilterBar>
        </div>
      </div>

      {error ? (
        <ErrorState title="Could not load clients" body={error.message} onRetry={load} />
      ) : loading && data.results.length === 0 ? (
        <DataTable columns={columns} rows={[]} loading />
      ) : data.results.length === 0 ? (
        <div className="table-wrap">
          <EmptyState
            title={emptyTitle}
            body={emptyBody}
            action={debouncedSearch || filters.status || filters.customer_type || filters.segment
              ? <Button variant="secondary" onClick={() => { setSearch(''); setFilters({ status: '', customer_type: '', segment: '' }); setPage(1); }}>Clear filters</Button>
              : addButton}
          />
        </div>
      ) : (
        <>
          <DataTable columns={columns} rows={data.results} keyField="customer_id" />
          <div className="mobile-clients">
            {data.results.map((c) => <MobileClientCard key={c.customer_id} customer={c} onDelete={handleDelete} />)}
          </div>
          <div className="table-wrap" style={{ marginTop: 16 }}>
            <Pagination
              page={page}
              pageSize={pageSize}
              count={data.count}
              onPageChange={setPage}
              pageSizeOptions={[10, 20, 50]}
              onPageSizeChange={(n) => resetPage(() => setPageSize(n))}
            />
          </div>
        </>
      )}

      <AddClientModal open={addOpen} onClose={() => setAddOpen(false)} />
    </div>
  );
}

export default ClientsPage;