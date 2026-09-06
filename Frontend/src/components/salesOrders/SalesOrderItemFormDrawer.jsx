import { useState, useEffect } from 'react';
import Drawer from '../Drawer';
import Button from '../Button';
import Field from '../Field';

const EMPTY_ITEM = {
  description: '',
  sku: '',
  quantity: '1',
  unit_price: '0',
  discount_type: '',
  discount_value: '0',
  tax_rate: '0',
  notes: '',
};

export function SalesOrderItemFormDrawer({ open, onClose, item, onSave, currency = 'KES' }) {
  const [form, setForm] = useState(EMPTY_ITEM);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (item) {
      setForm({
        description: item.description || '',
        sku: item.sku || '',
        quantity: String(item.quantity || 1),
        unit_price: String(item.unit_price || 0),
        discount_type: item.discount_type || '',
        discount_value: String(item.discount_value || 0),
        tax_rate: String(item.tax_rate || 0),
        notes: item.notes || '',
      });
    } else {
      setForm(EMPTY_ITEM);
    }
    setErrors({});
  }, [item, open]);

  const set = (key) => (e) => {
    setForm((f) => ({ ...f, [key]: e.target.value }));
    if (errors[key]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    }
  };

  const validate = () => {
    const problems = {};
    if (!form.description.trim()) problems.description = 'Description is required.';
    return problems;
  };

  const handleSubmit = () => {
    const problems = validate();
    if (Object.keys(problems).length) {
      setErrors(problems);
      return;
    }
    onSave({
      description: form.description.trim(),
      sku: form.sku || undefined,
      quantity: parseFloat(form.quantity) || 1,
      unit_price: parseFloat(form.unit_price) || 0,
      discount_type: form.discount_type || undefined,
      discount_value: parseFloat(form.discount_value) || 0,
      tax_rate: parseFloat(form.tax_rate) || 0,
      notes: form.notes || undefined,
    });
  };

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={item ? 'Edit Item' : 'Add Item'}
      footer={
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={handleSubmit}>{item ? 'Update' : 'Add'} Item</Button>
        </div>
      }
    >
      <Field label="Description" required error={errors} errorKey="description">
        <input className="field__input" value={form.description} onChange={set('description')} placeholder="Item description" />
      </Field>

      <Field label="SKU">
        <input className="field__input" value={form.sku} onChange={set('sku')} placeholder="Stock keeping unit" />
      </Field>

      <div className="form-row">
        <Field label="Quantity">
          <input type="number" className="field__input" value={form.quantity} onChange={set('quantity')} min="0" step="0.01" />
        </Field>
        <Field label={`Unit Price (${currency})`}>
          <input type="number" className="field__input" value={form.unit_price} onChange={set('unit_price')} min="0" step="0.01" />
        </Field>
      </div>

      <div className="form-row">
        <Field label="Discount Type">
          <select className="field__input" value={form.discount_type} onChange={set('discount_type')}>
            <option value="">None</option>
            <option value="PERCENTAGE">Percentage (%)</option>
            <option value="FIXED">Fixed Amount</option>
          </select>
        </Field>
        <Field label="Discount Value">
          <input type="number" className="field__input" value={form.discount_value} onChange={set('discount_value')} min="0" step="0.01" disabled={!form.discount_type} />
        </Field>
      </div>

      <Field label="Tax Rate (%)">
        <input type="number" className="field__input" value={form.tax_rate} onChange={set('tax_rate')} min="0" max="100" step="0.01" />
      </Field>

      <Field label="Notes">
        <textarea className="field__input field__input--textarea" value={form.notes} onChange={set('notes')} rows={2} placeholder="Optional notes..." />
      </Field>
    </Drawer>
  );
}

export default SalesOrderItemFormDrawer;
