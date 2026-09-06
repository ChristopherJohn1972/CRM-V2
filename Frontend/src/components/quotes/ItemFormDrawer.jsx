import { useState, useEffect } from 'react';
import Drawer from '../../components/Drawer';
import Button from '../../components/Button';
import Field from '../../components/Field';
import { listTaxRules } from '../../api/quotes';

function ItemFormDrawer({ open, onClose, item, onSave, currency = 'KES' }) {
  const [form, setForm] = useState({
    item_type: 'CUSTOM',
    description: '',
    sku: '',
    quantity: '1',
    unit_price: '0',
    discount_type: '',
    discount_value: '0',
    tax_code: '',
    tax_rate: '0',
    unit_of_measure: '',
    notes: '',
  });
  const [taxRules, setTaxRules] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (open) {
      if (item) {
        setForm({
          item_type: item.item_type || 'CUSTOM',
          description: item.description || '',
          sku: item.sku || '',
          quantity: String(item.quantity || 1),
          unit_price: String(item.unit_price || 0),
          discount_type: item.discount_type || '',
          discount_value: String(item.discount_value || 0),
          tax_code: item.tax_code || '',
          tax_rate: String(item.tax_rate || 0),
          unit_of_measure: item.unit_of_measure || '',
          notes: item.notes || '',
        });
      } else {
        setForm({
          item_type: 'CUSTOM',
          description: '',
          sku: '',
          quantity: '1',
          unit_price: '0',
          discount_type: '',
          discount_value: '0',
          tax_code: '',
          tax_rate: '0',
          unit_of_measure: '',
          notes: '',
        });
      }
      setErrors({});
      listTaxRules().then(setTaxRules).catch(() => {});
    }
  }, [open, item]);

  const set = (key) => (e) => {
    setForm((f) => ({ ...f, [key]: e.target.value }));
    if (errors[key]) {
      setErrors((prev) => { const n = { ...prev }; delete n[key]; return n; });
    }
  };

  const handleTaxCodeChange = (e) => {
    const code = e.target.value;
    const rule = taxRules.find((r) => r.code === code);
    setForm((f) => ({
      ...f,
      tax_code: code,
      tax_rate: rule ? String(rule.rate) : '0',
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.description.trim()) {
      setErrors({ description: 'Description is required.' });
      return;
    }
    setSubmitting(true);
    try {
      await onSave({
        item_type: form.item_type,
        description: form.description.trim(),
        sku: form.sku || undefined,
        quantity: parseFloat(form.quantity) || 1,
        unit_price: parseFloat(form.unit_price) || 0,
        discount_type: form.discount_type || undefined,
        discount_value: parseFloat(form.discount_value) || 0,
        tax_code: form.tax_code || undefined,
        tax_rate: parseFloat(form.tax_rate) || 0,
        unit_of_measure: form.unit_of_measure || undefined,
        notes: form.notes || undefined,
      });
    } catch (err) {
      if (err.fieldErrors) setErrors(err.fieldErrors);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Drawer open={open} onClose={onClose} title={item ? 'Edit Item' : 'Add Item'}>
      <form className="form" onSubmit={handleSubmit}>
        <Field label="Item Type" htmlFor="if-type">
          <select id="if-type" className="field__input" value={form.item_type} onChange={set('item_type')}>
            <option value="CUSTOM">Custom Item</option>
            <option value="PRODUCT">Product</option>
            <option value="SERVICE">Service</option>
          </select>
        </Field>

        <Field label="Description" required htmlFor="if-desc" error={errors} errorKey="description">
          <input id="if-desc" className="field__input" value={form.description} onChange={set('description')} placeholder="Item description" />
        </Field>

        <Field label="SKU / Code" htmlFor="if-sku">
          <input id="if-sku" className="field__input" value={form.sku} onChange={set('sku')} placeholder="Optional SKU or code" />
        </Field>

        <div className="form-row">
          <Field label="Quantity" htmlFor="if-qty">
            <input id="if-qty" type="number" step="0.01" min="0" className="field__input" value={form.quantity} onChange={set('quantity')} />
          </Field>
          <Field label={`Unit Price (${currency})`} htmlFor="if-price">
            <input id="if-price" type="number" step="0.01" min="0" className="field__input" value={form.unit_price} onChange={set('unit_price')} />
          </Field>
        </div>

        <div className="form-row">
          <Field label="Discount Type" htmlFor="if-disc-type">
            <select id="if-disc-type" className="field__input" value={form.discount_type} onChange={set('discount_type')}>
              <option value="">None</option>
              <option value="PERCENTAGE">Percentage (%)</option>
              <option value="FIXED">Fixed Amount</option>
            </select>
          </Field>
          <Field label="Discount Value" htmlFor="if-disc-val">
            <input id="if-disc-val" type="number" step="0.01" min="0" className="field__input" value={form.discount_value} onChange={set('discount_value')} disabled={!form.discount_type} />
          </Field>
        </div>

        <Field label="Tax Code" htmlFor="if-tax">
          <select id="if-tax" className="field__input" value={form.tax_code} onChange={handleTaxCodeChange}>
            <option value="">No tax</option>
            {taxRules.map((r) => (
              <option key={r.code} value={r.code}>{r.name} ({r.rate}%)</option>
            ))}
          </select>
        </Field>

        <Field label="Unit of Measure" htmlFor="if-uom">
          <input id="if-uom" className="field__input" value={form.unit_of_measure} onChange={set('unit_of_measure')} placeholder="e.g. pcs, hours, kg" />
        </Field>

        <Field label="Notes" htmlFor="if-notes">
          <textarea id="if-notes" className="field__input field__input--textarea" value={form.notes} onChange={set('notes')} rows={2} placeholder="Optional item notes" />
        </Field>

        <div className="drawer__footer">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={submitting}>{item ? 'Save Changes' : 'Add Item'}</Button>
        </div>
      </form>
    </Drawer>
  );
}

export default ItemFormDrawer;
