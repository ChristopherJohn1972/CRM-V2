import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { listSalesOrders } from '../../api/salesOrders';
import { portalMe } from '../../api/portal';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import Pagination from '../../components/Pagination';
import { formatDate, formatCurrency } from '../../utils/format';

function cleanEnum(value) {
  if (!value) return '';
  return value
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const STATUS_MAP = {
  PENDING: { label: 'Processing', variant: 'warning' },
  CONFIRMED: { label: 'Processing', variant: 'warning' },
  FULFILLED: { label: 'Completed', variant: 'success' },
  CANCELLED: { label: 'Cancelled', variant: 'danger' },
  REFUNDED: { label: 'Refunded', variant: 'info' },
};

function OrderStatusChip({ status }) {
  const cfg = STATUS_MAP[status] || { label: cleanEnum(status) || 'Unknown', variant: 'neutral' };
  return <span className={`badge badge--${cfg.variant}`}>{cfg.label}</span>;
}

export default function PurchasesPage() {
  const [data, setData] = useState({ count: 0, results: [] });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const abortRef = useRef(null);

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const me = await portalMe().catch(() => null);
      const customerId = me?.customer?.id || me?.customer_id;
      const res = await listSalesOrders({
        customer_id: customerId,
        page,
        page_size: pageSize,
      });
      setData(res);
    } catch (err) {
      if (err.name !== 'AbortError') setError(err);
    } finally {
      if (!abortRef.current || abortRef.current.signal === controller.signal) setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    load();
    return () => abortRef.current?.abort();
  }, [load]);

  const resetPage = (updater) => {
    setPage(1);
    updater();
  };

  return (
    <div className="portal-page">
      <PageHeader
        title="My Purchases"
        subtitle="View your order history and track deliveries"
      />

      {error ? (
        <ErrorState title="Could not load purchases" body={error.message} onRetry={load} />
      ) : loading && data.results.length === 0 ? (
        <div className="table-wrap">
          <table className="data-table">
            <tbody>
              <tr><td colSpan={5} className="cell-secondary">Loading purchases...</td></tr>
            </tbody>
          </table>
        </div>
      ) : data.results.length === 0 ? (
        <EmptyState
          title="No purchases yet"
          body="When you place an order, it will appear here so you can track its status."
        />
      ) : (
        <>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Order #</th>
                  <th>Date</th>
                  <th>Amount</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((order) => (
                  <tr key={order.id || order.order_id}>
                    <td>
                      <Link className="data-table__accent" to={`/portal/purchases/${order.id || order.order_id}`}>
                        {order.order_number || order.id}
                      </Link>
                    </td>
                    <td className="cell-secondary cell-nowrap">{formatDate(order.created_at || order.order_date)}</td>
                    <td style={{ fontWeight: 600 }}>{formatCurrency(order.grand_total, order.currency)}</td>
                    <td><OrderStatusChip status={order.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: 16 }}>
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
    </div>
  );
}
