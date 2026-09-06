import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { createSalesOrder, calculateSalesOrder } from '../../api/salesOrders';
import { listCustomers } from '../../api/customers';
import PageHeader from '../../components/PageHeader';
import Button from '../../components/Button';
import Field from '../../components/Field';
import { useToast } from '../../components/Toast';
import { useDebouncedValue } from '../../utils/useDebouncedValue';
import { CUSTOMER_TYPES } from '../../utils/constants';
import { formatCurrency } from '../../utils/format';
import SalesOrderItemFormDrawer from '../../components/salesOrders/SalesOrderItemFormDrawer';

const STEPS = ['Order Setup', 'Order Items', 'Review'];

export function CreateSalesOrderPage() {
  const navigate = useNavigate();
  const { notify } = useToast();
  const [step, setStep] = useState(0);
  const [banner, setBanner] = useState(null);

  // Step 1 — Order Setup
  const [form, setForm] = useState({ customer_id: '', order_date: '', expected_delivery_date: '', currency: 'KES' });
  const [errors, setErrors] = useState({});
  const [customerSearch, setCustomerSearch] = useState('');
  const debouncedCustomerSearch = useDebouncedValue(customerSearch, 350);
  const [customerResults, setCustomerResults] = useState([]);
  const [customerDropdownOpen, setCustomerDropdownOpen] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const customerDropdownRef = useRef(null);

  // Step 2 — Order Items
  const [items, setItems] = useState([]);
  const [itemDrawerOpen, setItemDrawerOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [calculations, setCalculations] = useState(null);

  // Step 2 — Notes
  const [notes, setNotes] = useState('');
  const [internalNotes, setInternalNotes] = useState('');
  const [notesExpanded, setNotesExpanded] = useState(false);

  const [submitting, setSubmitting] = useState(false);

  // ---- Customer search ----
  const loadCustomers = useCallback(async () => {
    if (!debouncedCustomerSearch || debouncedCustomerSearch.length < 2) { setCustomerResults([]); return; }
    try {
      const res = await listCustomers({ search: debouncedCustomerSearch, page_size: 10 });
      setCustomerResults(res.results || []); setCustomerDropdownOpen(true);
    } catch {}
  }, [debouncedCustomerSearch]);
  useEffect(() => { loadCustomers(); }, [loadCustomers]);
  useEffect(() => {
    const handleClick = (e) => { if (customerDropdownRef.current && !customerDropdownRef.current.contains(e.target)) setCustomerDropdownOpen(false); };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleCustomerSelect = (customer) => {
    setSelectedCustomer(customer);
    setForm((f) => ({ ...f, customer_id: customer.customer_id }));
    setCustomerSearch(`${customer.account_number} - ${customer.business_name || customer.full_name || ''}`);
    setCustomerDropdownOpen(false);
    if (errors.customer_id) setErrors((prev) => { const next = { ...prev }; delete next.customer_id; return next; });
  };

  const setField = (key) => (e) => {
    setForm((f) => ({ ...f, [key]: e.target.value }));
    if (errors[key]) setErrors((prev) => { const next = { ...prev }; delete next[key]; return next; });
    setBanner(null);
  };

  // ---- Step validation ----
  const validateStep1 = () => {
    const p = {};
    if (!form.customer_id) p.customer_id = 'Customer is required.';
    return p;
  };

  // ---- Navigation ----
  const goNext = () => {
    if (step === 0) {
      const problems = validateStep1();
      if (Object.keys(problems).length) { setErrors(problems); return; }
      setStep(1);
    } else if (step === 1) {
      if (items.length === 0) { setBanner('Add at least one order item.'); return; }
      setBanner(null);
      runCalculation();
      setStep(2);
    }
  };

  const goBack = () => { setStep((s) => s - 1); setBanner(null); };

  // ---- Items ----
  const handleItemAdded = (itemData) => {
    setItems((prev) => [...prev, { ...itemData, _localId: Date.now() }]);
    setItemDrawerOpen(false);
    setEditingItem(null);
  };

  const handleItemUpdated = (itemData) => {
    if (editingItem == null) return;
    setItems((prev) => prev.map((it) => it._localId === editingItem._localId ? { ...it, ...itemData } : it));
    setItemDrawerOpen(false);
    setEditingItem(null);
  };

  const handleRemoveItem = (localId) => {
    setItems((prev) => prev.filter((it) => it._localId !== localId));
  };

  const handleEditItem = (item) => { setEditingItem(item); setItemDrawerOpen(true); };
  const handleAddItem = () => { setEditingItem(null); setItemDrawerOpen(true); };

  // ---- Calculation ----
  async function runCalculation() {
    try {
      const result = await calculateSalesOrder({
        currency: form.currency,
        items: items.map((it) => ({
          description: it.description,
          sku: it.sku || undefined,
          quantity: it.quantity,
          unit_price: it.unit_price,
          discount_type: it.discount_type || undefined,
          discount_value: it.discount_value || 0,
          tax_rate: it.tax_rate || 0,
        })),
      });
      setCalculations(result);
    } catch {
      // Fallback: compute locally (backend is authoritative on submit)
      let subtotal = 0, discount = 0, tax = 0;
      for (const it of items) {
        const qty = parseFloat(it.quantity) || 1;
        const price = parseFloat(it.unit_price) || 0;
        const rate = parseFloat(it.tax_rate) || 0;
        const dType = it.discount_type;
        const dVal = parseFloat(it.discount_value) || 0;
        const line = qty * price;
        let lineDiscount = 0;
        if (dType === 'PERCENTAGE') lineDiscount = line * (dVal / 100);
        else if (dType === 'FIXED') lineDiscount = dVal;
        const lineSub = line - lineDiscount;
        tax += lineSub * (rate / 100);
        subtotal += line;
        discount += lineDiscount;
      }
      setCalculations({ subtotal, discount_amount: discount, tax_amount: tax, additional_charges: 0, grand_total: subtotal - discount + tax });
    }
  }

  // ---- Submit ----
  const handleSubmit = async (asDraft = false) => {
    setBanner(null);
    setSubmitting(true);
    try {
      const payload = {
        customer_id: parseInt(form.customer_id, 10),
        currency: form.currency,
        order_date: form.order_date || undefined,
        expected_delivery_date: form.expected_delivery_date || undefined,
        notes: notes || undefined,
        internal_notes: internalNotes || undefined,
        items: items.map((it) => ({
          description: it.description,
          sku: it.sku || undefined,
          quantity: it.quantity,
          unit_price: it.unit_price,
          discount_type: it.discount_type || undefined,
          discount_value: it.discount_value || 0,
          tax_rate: it.tax_rate || 0,
          notes: it.notes || undefined,
        })),
      };
      const created = await createSalesOrder(payload);
      notify(asDraft ? 'Draft saved' : 'Order created', { message: `${created.order_number} created successfully.`, variant: 'success' });
      navigate(`/sales-orders/${created.order_id}`);
    } catch (err) {
      setBanner(err.message || 'Could not create order.');
      if (err.fieldErrors) setErrors(err.fieldErrors);
    } finally { setSubmitting(false); }
  };

  // ---- Render ----
  const step1Valid = !!form.customer_id;
  const step2Valid = items.length > 0;
  const grandTotal = calculations?.grand_total ?? items.reduce((sum, it) => {
    const qty = parseFloat(it.quantity) || 1;
    const price = parseFloat(it.unit_price) || 0;
    return sum + qty * price;
  }, 0);

  return (
    <div>
      <PageHeader
        title="Create Sales Order"
        subtitle="Step-by-step order creation"
        actions={<Button variant="ghost" onClick={() => navigate('/sales-orders')}>Back to Orders</Button>}
      />

      {/* Stepper */}
      <div className="so-stepper">
        {STEPS.map((label, i) => (
          <div key={label} className={`so-stepper__step ${i < step ? 'so-stepper__step--done' : ''} ${i === step ? 'so-stepper__step--active' : ''}`}>
            <div className="so-stepper__indicator">
              {i < step ? '✓' : i + 1}
            </div>
            <span className="so-stepper__label">{label}</span>
          </div>
        ))}
      </div>

      {banner && <div className="form-error-banner" role="alert">{banner}</div>}

      {/* -------- Step 0: Order Setup -------- */}
      {step === 0 && (
        <div className="so-step">
          <div className="so-step__card">
            <h3 className="so-step__title">Order Setup</h3>

            <Field label="Customer" required error={errors} errorKey="customer_id">
              <div className="customer-search-wrapper" ref={customerDropdownRef}>
                <input
                  type="text"
                  className="field__input"
                  value={customerSearch}
                  onChange={(e) => { setCustomerSearch(e.target.value); setSelectedCustomer(null); setForm((f) => ({ ...f, customer_id: '' })); }}
                  onFocus={() => customerResults.length > 0 && setCustomerDropdownOpen(true)}
                  placeholder="Search customer or account number..."
                  autoComplete="off"
                />
                {customerDropdownOpen && customerResults.length > 0 && (
                  <div className="customer-search-dropdown">
                    {customerResults.map((c) => (
                      <button key={c.customer_id} type="button" className="customer-search-item" onClick={() => handleCustomerSelect(c)}>
                        <span className="customer-search-item__account">{c.account_number}</span>
                        <span className="customer-search-item__name">{c.business_name || c.full_name || 'N/A'}</span>
                        <span className="customer-search-item__type">{CUSTOMER_TYPES[c.customer_type] || c.customer_type}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </Field>

            {selectedCustomer && (
              <div className="so-selected-customer">
                <span className="badge badge--success">Selected</span>
                <span>{selectedCustomer.account_number} — {selectedCustomer.business_name || selectedCustomer.full_name}</span>
              </div>
            )}

            <div className="form-row form-row--2">
              <Field label="Order Date">
                <input type="date" className="field__input" value={form.order_date} onChange={setField('order_date')} />
              </Field>
              <Field label="Expected Delivery Date">
                <input type="date" className="field__input" value={form.expected_delivery_date} onChange={setField('expected_delivery_date')} />
              </Field>
            </div>

            <Field label="Currency">
              <select className="field__input" value={form.currency} onChange={setField('currency')}>
                <option value="KES">KES</option><option value="USD">USD</option><option value="GBP">GBP</option><option value="EUR">EUR</option>
              </select>
            </Field>
          </div>

          <div className="so-step__actions">
            <Button variant="ghost" onClick={() => navigate('/sales-orders')}>Cancel</Button>
            <Button variant="primary" onClick={goNext} disabled={!step1Valid}>Next →</Button>
          </div>
        </div>
      )}

      {/* -------- Step 1: Order Items -------- */}
      {step === 1 && (
        <div className="so-step">
          {/* Compact header summary */}
          <div className="so-order-header">
            <div className="so-order-header__row">
              <span className="so-order-header__customer">{selectedCustomer?.business_name || selectedCustomer?.full_name || 'Customer'}</span>
            </div>
            <div className="so-order-header__meta">
              <span>Order Date: {form.order_date || '—'}</span>
              <span>Delivery: {form.expected_delivery_date || '—'}</span>
              <span>Currency: {form.currency}</span>
            </div>
          </div>

          {/* Items table */}
          <div className="so-items-section">
            <div className="so-items-section__header">
              <h3>Order Items</h3>
              <Button variant="primary" size="sm" onClick={handleAddItem}>+ Add Item</Button>
            </div>

            {items.length === 0 ? (
              <div className="so-items-empty">
                <p>No items added yet.</p>
                <Button variant="secondary" onClick={handleAddItem}>Add first item</Button>
              </div>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Description</th>
                      <th>Qty</th>
                      <th>Unit Price</th>
                      <th>Discount</th>
                      <th>Tax</th>
                      <th>Amount</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((it) => {
                      const qty = parseFloat(it.quantity) || 1;
                      const price = parseFloat(it.unit_price) || 0;
                      const rate = parseFloat(it.tax_rate) || 0;
                      const dVal = parseFloat(it.discount_value) || 0;
                      const line = qty * price;
                      let lineDiscount = 0;
                      if (it.discount_type === 'PERCENTAGE') lineDiscount = line * (dVal / 100);
                      else if (it.discount_type === 'FIXED') lineDiscount = dVal;
                      const amt = line - lineDiscount + ((line - lineDiscount) * rate / 100);
                      return (
                        <tr key={it._localId}>
                          <td>{it.description}</td>
                          <td>{qty}</td>
                          <td>{formatCurrency(price, form.currency)}</td>
                          <td>{it.discount_type === 'PERCENTAGE' ? `${dVal}%` : it.discount_type === 'FIXED' ? formatCurrency(dVal, form.currency) : '—'}</td>
                          <td>{rate}%</td>
                          <td style={{ fontWeight: 600 }}>{formatCurrency(amt, form.currency)}</td>
                          <td>
                            <button className="btn btn--ghost btn--sm" onClick={() => handleEditItem(it)}>Edit</button>
                            <button className="btn btn--ghost btn--sm btn--danger" onClick={() => handleRemoveItem(it._localId)}>Remove</button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Financial summary */}
          {calculations && (
            <div className="so-summary">
              <div className="so-summary__row"><span>Subtotal</span><span>{formatCurrency(calculations.subtotal, form.currency)}</span></div>
              {calculations.discount_amount > 0 && <div className="so-summary__row so-summary__row--discount"><span>Discount</span><span>-{formatCurrency(calculations.discount_amount, form.currency)}</span></div>}
              {calculations.tax_amount > 0 && <div className="so-summary__row"><span>Tax</span><span>{formatCurrency(calculations.tax_amount, form.currency)}</span></div>}
              {calculations.additional_charges > 0 && <div className="so-summary__row"><span>Additional Charges</span><span>{formatCurrency(calculations.additional_charges, form.currency)}</span></div>}
              <div className="so-summary__row so-summary__row--total"><span>Grand Total</span><span>{formatCurrency(calculations.grand_total, form.currency)}</span></div>
            </div>
          )}

          {/* Notes — collapsible */}
          <div className="so-notes">
            <button className="so-notes__toggle" onClick={() => setNotesExpanded((v) => !v)}>
              Additional Information {notesExpanded ? '▴' : '▾'}
            </button>
            {notesExpanded && (
              <div className="so-notes__body">
                <Field label="Customer Notes" hint="Visible to the customer.">
                  <textarea className="field__input field__input--textarea" value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} placeholder="Notes visible to the customer..." />
                </Field>
                <Field label="Internal Notes" hint="Internal only.">
                  <textarea className="field__input field__input--textarea" value={internalNotes} onChange={(e) => setInternalNotes(e.target.value)} rows={2} placeholder="Internal notes..." />
                </Field>
              </div>
            )}
          </div>

          <div className="so-step__actions">
            <Button variant="ghost" onClick={goBack}>← Back</Button>
            <Button variant="primary" onClick={goNext} disabled={!step2Valid}>Next →</Button>
          </div>
        </div>
      )}

      {/* -------- Step 2: Review -------- */}
      {step === 2 && (
        <div className="so-step">
          <div className="so-review">
            <div className="so-review__section">
              <h4>Customer</h4>
              <p>{selectedCustomer?.business_name || selectedCustomer?.full_name || '—'}</p>
              <p className="text-muted">Account: {selectedCustomer?.account_number || '—'}</p>
            </div>

            <div className="so-review__section">
              <h4>Order Information</h4>
              <dl className="detail-list">
                <dt>Order Date</dt><dd>{form.order_date || '—'}</dd>
                <dt>Expected Delivery</dt><dd>{form.expected_delivery_date || '—'}</dd>
                <dt>Currency</dt><dd>{form.currency}</dd>
                <dt>Source</dt><dd>Direct Order</dd>
              </dl>
            </div>

            <div className="so-review__section">
              <h4>Items</h4>
              <table className="data-table">
                <thead>
                  <tr><th>Description</th><th>Qty</th><th>Unit Price</th><th>Discount</th><th>Tax</th><th>Total</th></tr>
                </thead>
                <tbody>
                  {items.map((it) => {
                    const qty = parseFloat(it.quantity) || 1;
                    const price = parseFloat(it.unit_price) || 0;
                    const rate = parseFloat(it.tax_rate) || 0;
                    const dVal = parseFloat(it.discount_value) || 0;
                    const line = qty * price;
                    let lineDiscount = 0;
                    if (it.discount_type === 'PERCENTAGE') lineDiscount = line * (dVal / 100);
                    else if (it.discount_type === 'FIXED') lineDiscount = dVal;
                    const amt = line - lineDiscount + ((line - lineDiscount) * rate / 100);
                    return (
                      <tr key={it._localId}>
                        <td>{it.description}</td>
                        <td>{qty}</td>
                        <td>{formatCurrency(price, form.currency)}</td>
                        <td>{it.discount_type === 'PERCENTAGE' ? `${dVal}%` : it.discount_type === 'FIXED' ? formatCurrency(dVal, form.currency) : '—'}</td>
                        <td>{rate}%</td>
                        <td style={{ fontWeight: 600 }}>{formatCurrency(amt, form.currency)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {calculations && (
              <div className="so-review__totals">
                <div className="so-summary__row"><span>Subtotal</span><span>{formatCurrency(calculations.subtotal, form.currency)}</span></div>
                {calculations.discount_amount > 0 && <div className="so-summary__row so-summary__row--discount"><span>Discount</span><span>-{formatCurrency(calculations.discount_amount, form.currency)}</span></div>}
                {calculations.tax_amount > 0 && <div className="so-summary__row"><span>Tax</span><span>{formatCurrency(calculations.tax_amount, form.currency)}</span></div>}
                <div className="so-summary__row so-summary__row--total"><span>Grand Total</span><span>{formatCurrency(calculations.grand_total, form.currency)}</span></div>
              </div>
            )}

            {notes && (
              <div className="so-review__section">
                <h4>Customer Notes</h4>
                <p>{notes}</p>
              </div>
            )}
          </div>

          <div className="so-step__actions">
            <Button variant="ghost" onClick={goBack}>← Back</Button>
            <Button variant="secondary" onClick={() => handleSubmit(true)} loading={submitting}>Save Draft</Button>
            <Button variant="primary" onClick={() => handleSubmit(false)} loading={submitting}>Create Order</Button>
          </div>
        </div>
      )}

      <SalesOrderItemFormDrawer
        open={itemDrawerOpen}
        onClose={() => { setItemDrawerOpen(false); setEditingItem(null); }}
        item={editingItem}
        onSave={editingItem ? handleItemUpdated : handleItemAdded}
        currency={form.currency}
      />
    </div>
  );
}

export default CreateSalesOrderPage;
