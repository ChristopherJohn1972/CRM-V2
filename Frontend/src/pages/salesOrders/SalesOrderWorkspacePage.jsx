import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  getSalesOrder, updateSalesOrder, addSalesOrderItem, updateSalesOrderItem, removeSalesOrderItem,
  confirmSalesOrder, cancelSalesOrder, markProcessingSO, markFulfilledSO,
  submitForApprovalSO, approveSalesOrder,
  listPayments, recordPayment, confirmPayment, reversePayment,
  listReceipts, voidReceipt, getReceipt,
} from '../../api/salesOrders';
import { useAuth } from '../../auth/AuthContext';
import { PermissionGate } from '../../components/PermissionGate';
import PageHeader from '../../components/PageHeader';
import Button from '../../components/Button';
import Field from '../../components/Field';
import StatusBadge from '../../components/StatusBadge';
import Modal from '../../components/Modal';
import { useToast } from '../../components/Toast';
import SalesOrderItemFormDrawer from '../../components/salesOrders/SalesOrderItemFormDrawer';
import SalesOrderActionBar from '../../components/salesOrders/SalesOrderActionBar';
import ReceiptPreview from '../../components/salesOrders/ReceiptPreview';
import { formatDate, formatCurrency } from '../../utils/format';
import {
  getOrderStatusLabel, getOrderStatusColor, getSourceLabel, canEditOrder,
  getPaymentStatusLabel, getPaymentStatusColor,
  getReceiptStatusLabel, getReceiptStatusColor,
  PAYMENT_METHOD_LABELS,
} from '../../utils/salesOrders';
import { PERMISSIONS } from '../../utils/constants';

function cleanEnum(value) {
  if (!value || typeof value !== 'string') return value;
  const dotIndex = value.lastIndexOf('.');
  return dotIndex >= 0 ? value.slice(dotIndex + 1) : value;
}

function OrderDocumentHeader({ order }) {
  return (
    <div className="so-doc-header">
      <img src="/curl-stack-logo.jpg" alt="Curl Stack" className="so-doc-header__logo-img" />
      <span className="so-doc-header__title">SALES ORDER</span>
      <div className="so-doc-header__dates">
        <div className="so-doc-header__date-row">
          <span className="so-doc-header__date-label">Order Date:</span>
          <span>{formatDate(order.order_date) || '—'}</span>
        </div>
        <div className="so-doc-header__date-row">
          <span className="so-doc-header__date-label">Expected Delivery:</span>
          <span>{formatDate(order.expected_delivery_date) || '—'}</span>
        </div>
      </div>
    </div>
  );
}

function OrderDocumentFooter({ order }) {
  return (
    <div className="so-doc-footer">
      <p className="so-doc-footer__thanks">Thanks for your order</p>
      <span className="so-doc-footer__number">{order.order_number}</span>
    </div>
  );
}

function OrderItemsTable({ items, currency }) {
  return (
    <div className="so-doc-section">
      <h4>ITEMS</h4>
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Description</th>
              <th>Qty</th>
              <th>Unit Price</th>
              <th>Discount</th>
              <th>Tax</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {(items || []).map((item) => (
              <tr key={item.item_id}>
                <td>{item.description}</td>
                <td>{item.quantity}</td>
                <td>{formatCurrency(item.unit_price, currency)}</td>
                <td>
                  {item.discount_type === 'PERCENTAGE' ? `${item.discount_value}%` :
                   item.discount_type === 'FIXED' ? formatCurrency(item.discount_value, currency) : '—'}
                </td>
                <td>{item.tax_rate}%</td>
                <td style={{ fontWeight: 600 }}>{formatCurrency(item.line_total, currency)}</td>
              </tr>
            ))}
            {(!items || items.length === 0) && (
              <tr><td colSpan="6" style={{ textAlign: 'center', color: 'var(--color-text-muted)' }}>No items</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function OrderTotals({ order }) {
  const { currency } = order;
  return (
    <div className="so-doc-totals">
      <div className="so-doc-totals__row"><span>Subtotal</span><span>{formatCurrency(order.subtotal, currency)}</span></div>
      {order.discount_amount > 0 && <div className="so-doc-totals__row so-doc-totals__row--discount"><span>Discount</span><span>-{formatCurrency(order.discount_amount, currency)}</span></div>}
      {order.tax_amount > 0 && <div className="so-doc-totals__row"><span>Tax</span><span>{formatCurrency(order.tax_amount, currency)}</span></div>}
      {order.additional_charges > 0 && <div className="so-doc-totals__row"><span>Additional Charges</span><span>{formatCurrency(order.additional_charges, currency)}</span></div>}
      <div className="so-doc-totals__row so-doc-totals__row--total"><span>Grand Total</span><span>{formatCurrency(order.grand_total, currency)}</span></div>
      <div className="so-doc-totals__row"><span>Amount Paid</span><span style={{ color: 'var(--color-success)' }}>{formatCurrency(order.amount_paid, currency)}</span></div>
      <div className="so-doc-totals__row so-doc-totals__row--balance"><span>Balance Due</span><span style={{ color: order.balance_due > 0 ? 'var(--color-warning)' : 'var(--color-text-muted)' }}>{formatCurrency(order.balance_due, currency)}</span></div>
    </div>
  );
}

export function SalesOrderWorkspacePage() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { notify } = useToast();
  const { hasPermission } = useAuth();
  const canUpdate = hasPermission(PERMISSIONS.SALES_ORDER_UPDATE);
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('details');
  const [payments, setPayments] = useState([]);
  const [receipts, setReceipts] = useState([]);
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [paymentForm, setPaymentForm] = useState({ amount: '', payment_method: 'MPESA', notes: '' });
  const [itemDrawerOpen, setItemDrawerOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [receiptPreview, setReceiptPreview] = useState(null);
  const abortRef = useRef(null);

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true); setError(null);
    try {
      const data = await getSalesOrder(orderId);
      setOrder(data);
    } catch (err) {
      if (err.name !== 'AbortError') setError(err);
    } finally {
      if (!abortRef.current || abortRef.current.signal === controller.signal) setLoading(false);
    }
  }, [orderId]);

  const loadPayments = useCallback(async () => { try { setPayments(await listPayments(orderId)); } catch {} }, [orderId]);
  const loadReceipts = useCallback(async () => { try { setReceipts(await listReceipts(orderId)); } catch {} }, [orderId]);

  useEffect(() => {
    load(); loadPayments(); loadReceipts();
    return () => abortRef.current?.abort();
  }, [load, loadPayments, loadReceipts]);

  const handleWorkflowAction = async (action) => {
    try {
      let result;
      switch (action) {
        case 'submit_approval':
          if (!window.confirm('Submit this order for approval?')) return;
          result = await submitForApprovalSO(orderId); notify('Order submitted for approval', { variant: 'success' }); break;
        case 'approve':
          if (!window.confirm('Approve this order?')) return;
          result = await approveSalesOrder(orderId); notify('Order approved', { variant: 'success' }); break;
        case 'confirm':
          if (!window.confirm('Confirm this order?')) return;
          result = await confirmSalesOrder(orderId); notify('Order confirmed', { variant: 'success' }); break;
        case 'processing':
          result = await markProcessingSO(orderId); notify('Order now processing', { variant: 'success' }); break;
        case 'fulfilled':
          result = await markFulfilledSO(orderId); notify('Order fulfilled', { variant: 'success' }); break;
        case 'cancel':
          if (!window.confirm('Cancel this order?')) return;
          result = await cancelSalesOrder(orderId); notify('Order cancelled', { variant: 'success' }); break;
        default: return;
      }
      if (result) { setOrder(result); loadPayments(); loadReceipts(); }
    } catch (err) { notify('Action failed', { message: err.message, variant: 'error' }); }
  };

  const handleItemAdded = async (itemData) => {
    try {
      await addSalesOrderItem(orderId, itemData);
      setItemDrawerOpen(false); setEditingItem(null);
      notify('Item added', { variant: 'success' }); load();
    } catch (err) { notify('Failed to add item', { message: err.message, variant: 'error' }); }
  };
  const handleItemUpdated = async (itemData) => {
    if (!editingItem) return;
    try {
      await updateSalesOrderItem(orderId, editingItem.item_id, itemData);
      setItemDrawerOpen(false); setEditingItem(null);
      notify('Item updated', { variant: 'success' }); load();
    } catch (err) { notify('Failed to update item', { message: err.message, variant: 'error' }); }
  };
  const handleItemRemoved = async (itemId) => {
    if (!window.confirm('Remove this item?')) return;
    try {
      await removeSalesOrderItem(orderId, itemId);
      notify('Item removed', { variant: 'success' }); load();
    } catch (err) { notify('Failed to remove item', { message: err.message, variant: 'error' }); }
  };
  const handleEditItem = (item) => { setEditingItem(item); setItemDrawerOpen(true); };
  const handleAddItem = () => { setEditingItem(null); setItemDrawerOpen(true); };

  const handleRecordPayment = async () => {
    try {
      const amount = parseFloat(paymentForm.amount);
      if (isNaN(amount) || amount <= 0) { notify('Invalid amount', { variant: 'error' }); return; }
      await recordPayment({ order_id: parseInt(orderId, 10), amount, payment_method: paymentForm.payment_method, notes: paymentForm.notes || undefined });
      setPaymentDialogOpen(false); setPaymentForm({ amount: '', payment_method: 'MPESA', notes: '' });
      notify('Payment recorded', { variant: 'success' }); load(); loadPayments(); loadReceipts();
    } catch (err) { notify('Payment failed', { message: err.message, variant: 'error' }); }
  };
  const handleConfirmPayment = async (paymentId) => {
    try { await confirmPayment(paymentId); notify('Payment confirmed', { variant: 'success' }); load(); loadPayments(); loadReceipts(); }
    catch (err) { notify('Confirm failed', { message: err.message, variant: 'error' }); }
  };
  const handleReversePayment = async (paymentId) => {
    if (!window.confirm('Reverse this payment?')) return;
    try { await reversePayment(paymentId); notify('Payment reversed', { variant: 'success' }); load(); loadPayments(); loadReceipts(); }
    catch (err) { notify('Reverse failed', { message: err.message, variant: 'error' }); }
  };
  const handleVoidReceipt = async (receiptId) => {
    if (!window.confirm('Void this receipt?')) return;
    try { await voidReceipt(receiptId); notify('Receipt voided', { variant: 'success' }); load(); loadReceipts(); setReceiptPreview(null); }
    catch (err) { notify('Void failed', { message: err.message, variant: 'error' }); }
  };
  const handleViewReceipt = async (receiptId) => {
    try {
      const receipt = await getReceipt(receiptId);
      setReceiptPreview(receipt);
    } catch (err) { notify('Failed to load receipt', { message: err.message, variant: 'error' }); }
  };
  const handlePrintReceipt = (receiptId) => { window.open(`/sales-orders/receipts/${receiptId}/pdf/`, '_blank'); };

  if (loading) return <div className="page-loading">Loading order...</div>;
  if (error) return (
    <div>
      <PageHeader title="Sales Order" subtitle="Could not load order" />
      <div className="form-error-banner" role="alert">{error.message}</div>
      <Button variant="secondary" onClick={() => navigate('/sales-orders')}>Back to Orders</Button>
    </div>
  );
  if (!order) return null;

  const editable = canEditOrder(order.status);

  return (
    <div className="so-doc-container">
      <div className="so-doc-header-fixed">
        <PageHeader
          title={order.order_number}
          subtitle={
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <span className="badge badge--neutral">{getSourceLabel(order.source)}</span>
              <StatusBadge label={getOrderStatusLabel(order.status)} style={{ background: getOrderStatusColor(order.status).bg, color: getOrderStatusColor(order.status).text }} />
            </span>
          }
          actions={
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <Link to="/sales-orders" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>← Back to Orders</Link>
              <SalesOrderActionBar status={order.status} onAction={handleWorkflowAction} canEdit={editable} />
            </div>
          }
        />
      </div>

      <div className="so-doc-scroll">
        <div className="so-doc">
        <OrderDocumentHeader order={order} />

        {/* Tabs — Activity removed per spec */}
        <div className="so-doc-tabs">
          <button className={`tab${activeTab === 'details' ? ' is-active' : ''}`} onClick={() => setActiveTab('details')}>Details</button>
          <button className={`tab${activeTab === 'payments' ? ' is-active' : ''}`} onClick={() => setActiveTab('payments')}>Payments ({payments.length})</button>
          <button className={`tab${activeTab === 'receipts' ? ' is-active' : ''}`} onClick={() => setActiveTab('receipts')}>Receipts ({receipts.length})</button>
        </div>

        {activeTab === 'details' && (
          <div className="so-doc-content">
            <OrderItemsTable items={order.items} currency={order.currency} />
            <OrderTotals order={order} />

            {(order.notes || order.internal_notes) && (
              <div className="so-doc-section">
                <h4>Notes</h4>
                {order.notes && <div className="so-doc-notes"><strong>Customer Notes:</strong> {order.notes}</div>}
                {order.internal_notes && <div className="so-doc-notes so-doc-notes--internal"><strong>Internal Notes:</strong> {order.internal_notes}</div>}
              </div>
            )}

            {editable && (
              <div className="so-doc-actions">
                <PermissionGate permission={PERMISSIONS.SALES_ORDER_UPDATE}>
                  <Button variant="secondary" size="sm" onClick={handleAddItem}>Add Item</Button>
                </PermissionGate>
              </div>
            )}
          </div>
        )}

        {activeTab === 'payments' && (
          <div className="so-doc-content">
            {!['FULFILLED', 'CANCELLED'].includes(cleanEnum(order.status)) && (
              <div className="so-doc-actions">
                <PermissionGate permission={PERMISSIONS.SALES_ORDER_UPDATE}>
                  <Button variant="primary" size="sm" onClick={() => setPaymentDialogOpen(true)}>Record Payment</Button>
                </PermissionGate>
              </div>
            )}
            {payments.length === 0 ? (
              <div className="so-doc-empty">No payments recorded yet.</div>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead><tr><th>Reference</th><th>Method</th><th>Amount</th><th>Status</th><th>Date</th><th></th></tr></thead>
                  <tbody>
                    {payments.map((p) => (
                      <tr key={p.payment_id}>
                        <td className="cell-secondary">{p.payment_reference || '—'}</td>
                        <td><span className="badge badge--neutral">{PAYMENT_METHOD_LABELS[p.payment_method] || p.payment_method}</span></td>
                        <td style={{ fontWeight: 600 }}>{formatCurrency(p.amount, p.currency)}</td>
                        <td><StatusBadge label={getPaymentStatusLabel(p.status)} style={{ background: getPaymentStatusColor(p.status).bg, color: getPaymentStatusColor(p.status).text }} /></td>
                        <td className="cell-secondary cell-nowrap">{formatDate(p.received_at || p.created_at)}</td>
                        <td>
                          {canUpdate && p.status === 'PENDING' && <Button variant="ghost" size="sm" onClick={() => handleConfirmPayment(p.payment_id)}>Confirm</Button>}
                          {canUpdate && p.status === 'CONFIRMED' && <Button variant="ghost" size="sm" onClick={() => handleReversePayment(p.payment_id)} style={{ color: 'var(--color-danger)' }}>Reverse</Button>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'receipts' && (
          <div className="so-doc-content">
            {receipts.length === 0 ? (
              <div className="so-doc-empty">No receipts issued yet. Receipts are generated when payments are confirmed.</div>
            ) : (
              <div className="so-receipt-list">
                {receipts.map((r) => (
                  <div key={r.receipt_id} className="so-receipt-card">
                    <div className="so-receipt-card__info">
                      <div className="so-receipt-card__number">{r.receipt_number}</div>
                      <div className="so-receipt-card__amount">{formatCurrency(r.amount, r.currency)}</div>
                      <StatusBadge label={getReceiptStatusLabel(r.status)} style={{ background: getReceiptStatusColor(r.status).bg, color: getReceiptStatusColor(r.status).text }} />
                      <div className="so-receipt-card__date">Issued {formatDate(r.issued_at)}</div>
                    </div>
                    <div className="so-receipt-card__actions">
                      <Button variant="secondary" size="sm" onClick={() => handleViewReceipt(r.receipt_id)}>View Receipt</Button>
                      <Button variant="ghost" size="sm" onClick={() => handlePrintReceipt(r.receipt_id)}>Print</Button>
                      <a href={`/api/sales-orders/receipts/${r.receipt_id}/pdf/`} target="_blank" rel="noopener noreferrer">
                        <Button variant="ghost" size="sm">Download PDF</Button>
                      </a>
                      {canUpdate && r.status === 'VALID' && (
                        <Button variant="ghost" size="sm" onClick={() => handleVoidReceipt(r.receipt_id)} style={{ color: 'var(--color-danger)' }}>Void</Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <OrderDocumentFooter order={order} />
      </div>
      </div>

      <SalesOrderItemFormDrawer
        open={itemDrawerOpen}
        onClose={() => { setItemDrawerOpen(false); setEditingItem(null); }}
        item={editingItem}
        onSave={editingItem ? handleItemUpdated : handleItemAdded}
        currency={order.currency}
      />

      {/* Receipt Preview Modal */}
      <Modal
        open={!!receiptPreview}
        onClose={() => setReceiptPreview(null)}
        title="Receipt Preview"
        footer={<>
          <Button variant="ghost" onClick={() => setReceiptPreview(null)}>Close</Button>
          {canUpdate && receiptPreview && receiptPreview.status === 'VALID' && (
            <Button variant="danger" size="sm" onClick={() => handleVoidReceipt(receiptPreview.receipt_id)}>Void Receipt</Button>
          )}
        </>}
      >
        {receiptPreview && (
          <ReceiptPreview receipt={receiptPreview} order={order} />
        )}
      </Modal>

      <Modal
        open={paymentDialogOpen}
        onClose={() => setPaymentDialogOpen(false)}
        title="Record Payment"
        footer={<>
          <Button variant="ghost" onClick={() => setPaymentDialogOpen(false)}>Cancel</Button>
          <PermissionGate permission={PERMISSIONS.SALES_ORDER_UPDATE}>
            <Button variant="primary" onClick={handleRecordPayment}>Record Payment</Button>
          </PermissionGate>
        </>}
      >
        <Field label="Amount" required>
          <input type="number" className="field__input" value={paymentForm.amount} onChange={(e) => setPaymentForm((f) => ({ ...f, amount: e.target.value }))} placeholder="0.00" min="0" step="0.01" />
        </Field>
        <Field label="Payment Method" required>
          <select className="field__input" value={paymentForm.payment_method} onChange={(e) => setPaymentForm((f) => ({ ...f, payment_method: e.target.value }))}>
            <option value="MPESA">M-Pesa</option><option value="BANK_TRANSFER">Bank Transfer</option><option value="CARD">Card</option><option value="CASH">Cash</option><option value="CHEQUE">Cheque</option><option value="OTHER">Other</option>
          </select>
        </Field>
        <Field label="Notes">
          <textarea className="field__input field__input--textarea" value={paymentForm.notes} onChange={(e) => setPaymentForm((f) => ({ ...f, notes: e.target.value }))} rows={2} placeholder="Optional notes..." />
        </Field>
      </Modal>
    </div>
  );
}

export default SalesOrderWorkspacePage;
