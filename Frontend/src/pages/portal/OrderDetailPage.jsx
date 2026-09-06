import { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getSalesOrder, listPayments, listReceipts, getReceiptPdfUrl } from '../../api/salesOrders';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import StatusBadge from '../../components/StatusBadge';
import { formatDate, formatCurrency } from '../../utils/format';

function cleanEnum(value) {
  if (!value) return '';
  return value
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const STATUS_MAP = {
  DRAFT: { label: 'Draft', variant: 'muted' },
  PENDING: { label: 'Processing', variant: 'warning' },
  CONFIRMED: { label: 'Processing', variant: 'warning' },
  FULFILLED: { label: 'Completed', variant: 'success' },
  CANCELLED: { label: 'Cancelled', variant: 'danger' },
  REFUNDED: { label: 'Refunded', variant: 'info' },
};

function OrderStatusBadge({ status }) {
  const cfg = STATUS_MAP[status] || { label: cleanEnum(status) || 'Unknown', variant: 'neutral' };
  return <StatusBadge label={cfg.label} variant={cfg.variant} />;
}

const PAYMENT_STATUS_MAP = {
  UNPAID: { label: 'Unpaid', variant: 'danger' },
  PARTIAL: { label: 'Partially Paid', variant: 'warning' },
  PAID: { label: 'Paid', variant: 'success' },
  REFUNDED: { label: 'Refunded', variant: 'info' },
};

function PaymentStatusChip({ status }) {
  const cfg = PAYMENT_STATUS_MAP[status] || { label: cleanEnum(status) || 'Unknown', variant: 'neutral' };
  return <span className={`badge badge--${cfg.variant}`}>{cfg.label}</span>;
}

export default function OrderDetailPage() {
  const { orderId } = useParams();
  const [order, setOrder] = useState(null);
  const [payments, setPayments] = useState([]);
  const [receipts, setReceipts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [orderData, paymentsData, receiptsData] = await Promise.all([
        getSalesOrder(orderId),
        listPayments(orderId).catch(() => ({ results: [] })),
        listReceipts(orderId).catch(() => ({ results: [] })),
      ]);
      setOrder(orderData);
      setPayments(paymentsData.results || []);
      setReceipts(receiptsData.results || []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="portal-page"><div className="loading-spinner">Loading order...</div></div>;

  if (error) {
    return (
      <div className="portal-page">
        <PageHeader
          title="Order Details"
          subtitle="Could not load order"
          actions={
            <Link to="/portal/purchases" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
              &larr; Back to Purchases
            </Link>
          }
        />
        <ErrorState title="Could not load order" body={error.message} onRetry={load} />
      </div>
    );
  }

  if (!order) return null;

  const items = order.items || [];
  const firstReceipt = receipts.length > 0 ? receipts[0] : null;

  return (
    <div className="portal-page">
      <PageHeader
        title={order.order_number || `Order #${order.id}`}
        subtitle={
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <OrderStatusBadge status={order.status} />
          </span>
        }
        actions={
          <Link to="/portal/purchases" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
            &larr; Back to Purchases
          </Link>
        }
      />

      <div className="form-section">
        <div className="form-section__header">
          <h2 className="form-section__title">Order Details</h2>
        </div>
        <div className="quote-detail__info">
          <div className="field-display">
            <span className="field-display__label">Order Number</span>
            <span className="field-display__value">{order.order_number || order.id}</span>
          </div>
          <div className="field-display">
            <span className="field-display__label">Date</span>
            <span className="field-display__value">{formatDate(order.created_at || order.order_date)}</span>
          </div>
          <div className="field-display">
            <span className="field-display__label">Status</span>
            <span className="field-display__value"><OrderStatusBadge status={order.status} /></span>
          </div>
          <div className="field-display">
            <span className="field-display__label">Payment Status</span>
            <span className="field-display__value">
              <PaymentStatusChip status={order.payment_status} />
            </span>
          </div>
        </div>
      </div>

      <div className="form-section">
        <div className="form-section__header">
          <h2 className="form-section__title">Items</h2>
        </div>
        {items.length === 0 ? (
          <EmptyState title="No items" body="This order does not have any items." />
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Description</th>
                  <th>Qty</th>
                  <th>Unit Price</th>
                  <th>Amount</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, idx) => (
                  <tr key={item.id || idx}>
                    <td>{idx + 1}</td>
                    <td>
                      <div style={{ fontWeight: 500 }}>{item.description || item.name}</div>
                      {item.sku && <div className="cell-secondary">{item.sku}</div>}
                    </td>
                    <td>{item.quantity}</td>
                    <td>{formatCurrency(item.unit_price, order.currency)}</td>
                    <td style={{ fontWeight: 600 }}>{formatCurrency(item.line_total || item.amount, order.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="form-section">
        <div className="form-section__header">
          <h2 className="form-section__title">Totals</h2>
        </div>
        <div className="quote-summary-panel">
          <div className="quote-summary-panel__row">
            <span className="quote-summary-panel__label">Subtotal</span>
            <span className="quote-summary-panel__value">{formatCurrency(order.subtotal, order.currency)}</span>
          </div>
          {order.discount_amount > 0 && (
            <div className="quote-summary-panel__row">
              <span className="quote-summary-panel__label">Discount</span>
              <span className="quote-summary-panel__value quote-summary-panel__value--discount">
                -{formatCurrency(order.discount_amount, order.currency)}
              </span>
            </div>
          )}
          {order.tax_amount > 0 && (
            <div className="quote-summary-panel__row">
              <span className="quote-summary-panel__label">Tax</span>
              <span className="quote-summary-panel__value">{formatCurrency(order.tax_amount, order.currency)}</span>
            </div>
          )}
          <div className="quote-summary-panel__row quote-summary-panel__row--total">
            <span className="quote-summary-panel__label">Total</span>
            <span className="quote-summary-panel__value">{formatCurrency(order.grand_total, order.currency)}</span>
          </div>
        </div>
      </div>

      {firstReceipt && (
        <div className="form-section">
          <div className="form-section__header">
            <h2 className="form-section__title">Receipt</h2>
          </div>
          <div className="quote-detail__info">
            <div className="field-display">
              <span className="field-display__label">Receipt #</span>
              <span className="field-display__value">{firstReceipt.receipt_number || firstReceipt.id}</span>
            </div>
            <div className="field-display">
              <span className="field-display__label">Date</span>
              <span className="field-display__value">{formatDate(firstReceipt.created_at)}</span>
            </div>
            <div className="field-display">
              <span className="field-display__label">Amount</span>
              <span className="field-display__value">{formatCurrency(firstReceipt.amount, order.currency)}</span>
            </div>
          </div>
          <a
            href={getReceiptPdfUrl(firstReceipt.id)}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn--secondary btn--sm"
            style={{ marginTop: 12 }}
          >
            Download Receipt
          </a>
        </div>
      )}
    </div>
  );
}
