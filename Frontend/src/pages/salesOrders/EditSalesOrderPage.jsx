import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getSalesOrder, updateSalesOrder } from '../../api/salesOrders';
import PageHeader from '../../components/PageHeader';
import Button from '../../components/Button';
import Field from '../../components/Field';
import ErrorState from '../../components/ErrorState';
import { useToast } from '../../components/Toast';
import { getOrderStatusLabel, getOrderStatusColor } from '../../utils/salesOrders';

export function EditSalesOrderPage() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { notify } = useToast();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    order_date: '',
    expected_delivery_date: '',
    currency: 'KES',
    notes: '',
    internal_notes: '',
    terms_and_conditions: '',
    discount_type: '',
    discount_value: '',
    additional_charges: '',
  });

  useEffect(() => {
    loadOrder();
  }, [orderId]);

  async function loadOrder() {
    setLoading(true);
    setError(null);
    try {
      const data = await getSalesOrder(orderId);
      setOrder(data);
      setForm({
        order_date: data.order_date || '',
        expected_delivery_date: data.expected_delivery_date || '',
        currency: data.currency || 'KES',
        notes: data.notes || '',
        internal_notes: data.internal_notes || '',
        terms_and_conditions: data.terms_and_conditions || '',
        discount_type: data.discount_type || '',
        discount_value: data.discount_value || '',
        additional_charges: data.additional_charges || '',
      });
    } catch (err) {
      setError(err.message || 'Failed to load order');
    } finally {
      setLoading(false);
    }
  }

  const setField = (key) => (e) => {
    setForm((f) => ({ ...f, [key]: e.target.value }));
  };

  async function handleSave() {
    setSaving(true);
    try {
      const payload = {
        order_date: form.order_date || undefined,
        expected_delivery_date: form.expected_delivery_date || undefined,
        currency: form.currency,
        notes: form.notes || undefined,
        internal_notes: form.internal_notes || undefined,
        terms_and_conditions: form.terms_and_conditions || undefined,
        discount_type: form.discount_type || undefined,
        discount_value: form.discount_value ? parseFloat(form.discount_value) : undefined,
        additional_charges: form.additional_charges ? parseFloat(form.additional_charges) : undefined,
        version: order.version,
      };
      await updateSalesOrder(orderId, payload);
      notify('Order updated', { variant: 'success' });
      navigate(`/sales-orders/${orderId}`);
    } catch (err) {
      notify(err.message || 'Failed to update order', { variant: 'error' });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div>
        <PageHeader title="Edit Sales Order" subtitle="Loading..." />
        <p className="cell-secondary">Loading order details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Edit Sales Order" subtitle="Error" />
        <ErrorState title="Could not load order" body={error} onRetry={loadOrder} />
      </div>
    );
  }

  if (!order) return null;

  const statusColor = getOrderStatusColor(order.status);

  return (
    <div>
      <PageHeader
        title="Edit Sales Order"
        subtitle={`Editing ${order.order_number}`}
        actions={
          <Button variant="ghost" onClick={() => navigate(`/sales-orders/${orderId}`)}>
            Back to Order
          </Button>
        }
      />

      <div className="so-step">
        <div className="so-step__card">
          <div className="so-edit-header">
            <span className="so-edit-header__number">{order.order_number}</span>
            <span
              className="badge"
              style={{ background: statusColor.bg, color: statusColor.text }}
            >
              {getOrderStatusLabel(order.status)}
            </span>
          </div>

          <div className="form-row form-row--2">
            <Field label="Order Date">
              <input
                type="date"
                className="field__input"
                value={form.order_date}
                onChange={setField('order_date')}
              />
            </Field>
            <Field label="Expected Delivery Date">
              <input
                type="date"
                className="field__input"
                value={form.expected_delivery_date}
                onChange={setField('expected_delivery_date')}
              />
            </Field>
          </div>

          <Field label="Currency">
            <select className="field__input" value={form.currency} onChange={setField('currency')}>
              <option value="KES">KES</option>
              <option value="USD">USD</option>
              <option value="GBP">GBP</option>
              <option value="EUR">EUR</option>
            </select>
          </Field>

          <div className="form-row form-row--2">
            <Field label="Order Discount Type">
              <select className="field__input" value={form.discount_type} onChange={setField('discount_type')}>
                <option value="">None</option>
                <option value="PERCENTAGE">Percentage</option>
                <option value="FIXED">Fixed Amount</option>
              </select>
            </Field>
            <Field label="Discount Value">
              <input
                type="number"
                className="field__input"
                value={form.discount_value}
                onChange={setField('discount_value')}
                placeholder="0.00"
                min="0"
                step="0.01"
                disabled={!form.discount_type}
              />
            </Field>
          </div>

          <Field label="Additional Charges">
            <input
              type="number"
              className="field__input"
              value={form.additional_charges}
              onChange={setField('additional_charges')}
              placeholder="0.00"
              min="0"
              step="0.01"
            />
          </Field>

          <Field label="Customer Notes" hint="Visible to the customer.">
            <textarea
              className="field__input field__input--textarea"
              value={form.notes}
              onChange={setField('notes')}
              rows={3}
              placeholder="Notes visible to the customer..."
            />
          </Field>

          <Field label="Internal Notes" hint="Internal only.">
            <textarea
              className="field__input field__input--textarea"
              value={form.internal_notes}
              onChange={setField('internal_notes')}
              rows={3}
              placeholder="Internal notes..."
            />
          </Field>

          <Field label="Terms and Conditions">
            <textarea
              className="field__input field__input--textarea"
              value={form.terms_and_conditions}
              onChange={setField('terms_and_conditions')}
              rows={3}
              placeholder="Terms and conditions..."
            />
          </Field>
        </div>

        <div className="so-step__actions">
          <Button variant="ghost" onClick={() => navigate(`/sales-orders/${orderId}`)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default EditSalesOrderPage;
