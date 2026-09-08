import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { listSalesOrders, deleteSalesOrder } from '../../api/salesOrders';
import { useAuth } from '../../auth/AuthContext';
import PageHeader from '../../components/PageHeader';
import Button from '../../components/Button';
import SearchBar from '../../components/SearchBar';
import FilterBar from '../../components/FilterBar';
import DataTable from '../../components/DataTable';
import StatusBadge from '../../components/StatusBadge';
import Pagination from '../../components/Pagination';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import { useToast } from '../../components/Toast';
import { formatDate } from '../../utils/format';
import { getOrderStatusLabel, getOrderStatusColor, getSourceLabel, getPaymentOverallStatusLabel, getPaymentOverallStatusVariant, formatOrderAmount } from '../../utils/salesOrders';
import { useDebouncedValue } from '../../utils/useDebouncedValue';
import { PERMISSIONS } from '../../utils/constants';
import { PermissionGate } from '../../components/PermissionGate';
function StatCard({ label, value, variant = 'neutral' }) {
  return (<div className={`quote-stat-card quote-stat-card--${variant}`}><div className="quote-stat-card__value">{value}</div><div className="quote-stat-card__label">{label}</div></div>);
}
export function SalesOrderListPage() {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const { notify } = useToast();
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search, 350);
  const [filters, setFilters] = useState({ status: '', source: '' });
  const [data, setData] = useState({ count: 0, results: [] });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState({ total: 0, drafts: 0, confirmed: 0, processing: 0, fulfilled: 0 });
  const abortRef = useRef(null);

  const [openMenuId, setOpenMenuId] = useState(null);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const menuRef = useRef(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const canCreate = hasPermission(PERMISSIONS.SALES_ORDER_CREATE);
  const canUpdate = hasPermission(PERMISSIONS.SALES_ORDER_UPDATE);
  const canDelete = hasPermission(PERMISSIONS.SALES_ORDER_DELETE);
  const showActions = canUpdate || canDelete;

  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpenMenuId(null);
      }
    }
    if (openMenuId) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [openMenuId]);

  function toggleMenu(orderId, buttonEl) {
    if (openMenuId === orderId) {
      setOpenMenuId(null);
      return;
    }
    const rect = buttonEl.getBoundingClientRect();
    const menuHeight = 130;
    const spaceBelow = window.innerHeight - rect.bottom;
    const openAbove = spaceBelow < menuHeight;
    const top = openAbove ? rect.top - menuHeight - 4 : rect.bottom + 4;
    const left = rect.left - 120;
    setMenuPos({ top, left: Math.max(8, left) });
    setOpenMenuId(orderId);
  }

  function handleConfirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    deleteSalesOrder(deleteTarget.order_id)
      .then(() => {
        setDeleteTarget(null);
        setOpenMenuId(null);
        notify('Order deleted', { variant: 'success' });
        load();
      })
      .catch(err => {
        notify(err.message || 'Failed to delete order', { variant: 'error' });
      })
      .finally(() => setDeleting(false));
  }
  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true); setError(null);
    try {
      const res = await listSalesOrders({ search: debouncedSearch || undefined, status: filters.status || undefined, source: filters.source || undefined, page, page_size: pageSize });
      setData(res);
      const counts = { total: res.count, drafts: 0, confirmed: 0, processing: 0, fulfilled: 0 };
      for (const o of res.results) {
        if (o.status === 'DRAFT') counts.drafts++;
        if (o.status === 'CONFIRMED') counts.confirmed++;
        if (o.status === 'PROCESSING') counts.processing++;
        if (o.status === 'FULFILLED') counts.fulfilled++;
      }
      setSummary(counts);
    } catch (err) { if (err.name !== 'AbortError') setError(err); }
    finally { if (!abortRef.current || abortRef.current.signal === controller.signal) setLoading(false); }
  }, [debouncedSearch, filters.status, filters.source, page, pageSize]);
  useEffect(() => { load(); return () => abortRef.current?.abort(); }, [load]);
  const resetPage = (updater) => { setPage(1); updater(); };
  const columns = [
    { key: 'order_number', header: 'Order #', render: (r) => <Link className="data-table__accent" to={`/sales-orders/${r.order_id}`}>{r.order_number}</Link> },
    { key: 'source', header: 'Source', render: (r) => <span className="badge badge--neutral">{getSourceLabel(r.source)}</span> },
    { key: 'order_date', header: 'Date', render: (r) => <span className="cell-secondary cell-nowrap">{formatDate(r.order_date)}</span> },
    { key: 'grand_total', header: 'Amount', render: (r) => <span style={{ fontWeight: 600 }}>{formatOrderAmount(r.grand_total, r.currency)}</span> },
    { key: 'amount_paid', header: 'Paid', render: (r) => <span style={{ color: 'var(--color-success)' }}>{formatOrderAmount(r.amount_paid, r.currency)}</span> },
    { key: 'balance_due', header: 'Balance', render: (r) => <span style={{ fontWeight: 500, color: r.balance_due > 0 ? 'var(--color-warning)' : 'var(--color-text-muted)' }}>{formatOrderAmount(r.balance_due, r.currency)}</span> },
    { key: 'payment_status', header: 'Payment', render: (r) => <StatusBadge label={getPaymentOverallStatusLabel(r.payment_status)} variant={getPaymentOverallStatusVariant(r.payment_status)} /> },
    { key: 'status', header: 'Status', render: (r) => { const c = getOrderStatusColor(r.status); return <StatusBadge label={getOrderStatusLabel(r.status)} style={{ background: c.bg, color: c.text }} />; } },
    ...(showActions ? [{
      key: '__actions',
      header: 'Actions',
      render: (r) => (
        <div className="lead-actions-cell">
          <button
            className="lead-menu-trigger"
            onClick={(e) => { e.stopPropagation(); toggleMenu(r.order_id, e.currentTarget); }}
          >
            ⋮
          </button>
        </div>
      ),
    }] : []),
  ];
  const emptyTitle = debouncedSearch || filters.status || filters.source ? 'No orders match your search' : 'No sales orders yet';
  const emptyBody = debouncedSearch || filters.status || filters.source ? 'Try adjusting your search or filters.' : 'Create your first sales order to get started.';
  return (
    <div>
      <PageHeader title="Sales Orders" subtitle="Manage orders, payments and receipts." actions={<PermissionGate permission={PERMISSIONS.SALES_ORDER_CREATE}><Button variant="primary" onClick={() => navigate('/sales-orders/new')}>+ New Order</Button></PermissionGate>} />
      <div className="quote-stat-grid">
        <StatCard label="Total Orders" value={summary.total} />
        <StatCard label="Drafts" value={summary.drafts} variant="muted" />
        <StatCard label="Confirmed" value={summary.confirmed} variant="success" />
        <StatCard label="Processing" value={summary.processing} variant="info" />
        <StatCard label="Fulfilled" value={summary.fulfilled} variant="success" />
      </div>
      <div className="toolbar">
        <div className="toolbar__search"><SearchBar value={search} onChange={(v) => setSearch(v)} placeholder="Search order number..." label="Search orders" /></div>
        <div className="toolbar__filters">
          <FilterBar>
            <label className="sr-only" htmlFor="filter-order-status">Status</label>
            <select id="filter-order-status" value={filters.status} onChange={(e) => resetPage(() => setFilters((f) => ({ ...f, status: e.target.value })))}>
              <option value="">All statuses</option><option value="DRAFT">Draft</option><option value="PENDING_APPROVAL">Pending Approval</option><option value="APPROVED">Approved</option><option value="CONFIRMED">Confirmed</option><option value="PROCESSING">Processing</option><option value="FULFILLED">Fulfilled</option><option value="CANCELLED">Cancelled</option><option value="ON_HOLD">On Hold</option>
            </select>
            <label className="sr-only" htmlFor="filter-order-source">Source</label>
            <select id="filter-order-source" value={filters.source} onChange={(e) => resetPage(() => setFilters((f) => ({ ...f, source: e.target.value })))}>
              <option value="">All sources</option><option value="DIRECT">Direct</option><option value="QUOTE">From Quote</option>
            </select>
          </FilterBar>
        </div>
      </div>
      {error ? (
        <ErrorState title="Could not load orders" body={error.message} onRetry={load} />
      ) : loading && data.results.length === 0 ? (
        <DataTable columns={columns} rows={[]} loading />
      ) : data.results.length === 0 ? (
        <div className="table-wrap">
          <EmptyState title={emptyTitle} body={emptyBody} action={debouncedSearch || filters.status || filters.source ? <Button variant="secondary" onClick={() => { setSearch(''); setFilters({ status: '', source: '' }); setPage(1); }}>Clear filters</Button> : <PermissionGate permission={PERMISSIONS.SALES_ORDER_CREATE}><Button variant="primary" onClick={() => navigate('/sales-orders/new')}>Create Order</Button></PermissionGate>} />
        </div>
      ) : (
        <>
          <DataTable columns={columns} rows={data.results} keyField="order_id" />
          <div className="mobile-quotes">{data.results.map((o) => <div key={o.order_id} className="mobile-quote-card"><div className="mobile-quote-card__row"><Link className="data-table__accent" to={`/sales-orders/${o.order_id}`}>{o.order_number}</Link><StatusBadge label={getOrderStatusLabel(o.status)} style={{ background: getOrderStatusColor(o.status).bg, color: getOrderStatusColor(o.status).text }} /></div><div className="mobile-quote-card__meta"><span style={{ fontWeight: 600 }}>{getSourceLabel(o.source)}</span></div><div className="mobile-quote-card__meta"><span>{formatOrderAmount(o.grand_total, o.currency)}</span><span>{formatDate(o.order_date)}</span></div><div className="mobile-quote-card__meta"><span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Balance: {formatOrderAmount(o.balance_due, o.currency)}</span></div></div>)}</div>
          <div className="table-wrap" style={{ marginTop: 16 }}><Pagination page={page} pageSize={pageSize} count={data.count} onPageChange={setPage} pageSizeOptions={[10, 20, 50]} onPageSizeChange={(n) => resetPage(() => setPageSize(n))} /></div>
        </>
      )}

      {openMenuId && (
        <div
          ref={menuRef}
          className="lead-menu lead-menu--fixed"
          style={{ top: menuPos.top, left: menuPos.left }}
          onClick={(e) => e.stopPropagation()}
        >
          <button className="lead-menu__item" onClick={() => { navigate(`/sales-orders/${openMenuId}`); setOpenMenuId(null); }}>
            View Order
          </button>
          {canUpdate && (
            <button className="lead-menu__item" onClick={() => { navigate(`/sales-orders/${openMenuId}/edit`); setOpenMenuId(null); }}>
              Edit Order
            </button>
          )}
          {canDelete && (
            <button className="lead-menu__item lead-menu__item--danger" onClick={() => {
              const o = data.results.find(x => x.order_id === openMenuId);
              setDeleteTarget(o);
              setOpenMenuId(null);
            }}>
              Delete Order
            </button>
          )}
        </div>
      )}

      {deleteTarget && (
        <div className="modal-overlay" onClick={() => setDeleteTarget(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="modal__title">Delete Sales Order?</h3>
            </div>
            <div className="modal__body">
              <p>
                Are you sure you want to delete <strong>{deleteTarget.order_number}</strong>?
              </p>
              <p style={{ color: 'var(--color-text-secondary, #6B7280)', fontSize: 13, marginTop: 8 }}>
                This action may affect associated payments, receipts and financial records.
              </p>
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => setDeleteTarget(null)} disabled={deleting}>
                Cancel
              </button>
              <button className="btn btn--danger" onClick={handleConfirmDelete} disabled={deleting}>
                {deleting ? 'Deleting...' : 'Delete Order'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
export default SalesOrderListPage;
