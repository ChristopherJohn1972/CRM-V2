import { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { getQuote, updateQuote, addQuoteItem, updateQuoteItem, removeQuoteItem, createQuote, generateQuotePdf } from '../../api/quotes';
import Button from '../../components/Button';
import Field from '../../components/Field';
import CustomerSelector from '../../components/quotes/CustomerSelector';
import QuoteItemsTable from '../../components/quotes/QuoteItemsTable';
import ItemFormDrawer from '../../components/quotes/ItemFormDrawer';
import QuoteA4Preview from '../../components/quotes/QuoteA4Preview';
import { useToast } from '../../components/Toast';
import { formatCurrency } from '../../utils/format';

const STEPS = [
  { key: 1, label: 'Customer & Quote Details' },
  { key: 2, label: 'Quote Items' },
  { key: 3, label: 'Pricing, Terms & Review' },
];

export function QuoteStudioPage() {
  const { quoteId } = useParams();
  const navigate = useNavigate();
  const { notify } = useToast();
  const { user: staff } = useAuth();
  const isNew = !quoteId || quoteId === 'new';

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(!isNew);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);

  const [quote, setQuote] = useState({
    quote_number: '',
    title: '',
    currency: 'KES',
    valid_until: '',
    quote_date: new Date().toISOString().split('T')[0],
    notes: '',
    internal_notes: '',
    items: [],
    subtotal: 0,
    discount_amount: 0,
    tax_amount: 0,
    installation_charge: 0,
    delivery_charge: 0,
    grand_total: 0,
    status: 'DRAFT',
  });

  const [customer, setCustomer] = useState(null);
  const [itemDrawerOpen, setItemDrawerOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [errors, setErrors] = useState({});

  const loadQuote = useCallback(async () => {
    if (isNew) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getQuote(quoteId);
      setQuote(data);
      setCustomer(data.customer || null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [quoteId, isNew]);

  useEffect(() => {
    loadQuote();
  }, [loadQuote]);

  const setFormField = (key) => (e) => {
    setQuote((q) => ({ ...q, [key]: e.target.value }));
    if (errors[key]) {
      setErrors((prev) => { const n = { ...prev }; delete n[key]; return n; });
    }
  };

  const handleCustomerChange = (c) => {
    setCustomer(c);
    setQuote((q) => ({ ...q, customer_id: c ? c.customer_id : null }));
  };

  const handleAddItem = () => {
    setEditingItem(null);
    setItemDrawerOpen(true);
  };

  const handleEditItem = (item) => {
    setEditingItem(item);
    setItemDrawerOpen(true);
  };

  const handleItemSaved = async (itemData) => {
    try {
      if (editingItem) {
        const updated = await updateQuoteItem(quote.quote_id, editingItem.item_id, itemData);
        setQuote((q) => ({
          ...q,
          items: q.items.map((i) => (i.item_id === editingItem.item_id ? updated : i)),
        }));
        notify('Item updated', { variant: 'success' });
      } else {
        if (isNew && !quote.quote_id) {
          const created = await createQuote({
            quote_type: 'PRODUCT',
            customer_id: customer?.customer_id,
            title: quote.title,
            currency: quote.currency,
            valid_until: quote.valid_until,
          });
          setQuote(created);
          const newItem = await addQuoteItem(created.quote_id, itemData);
          setQuote((q) => ({ ...q, items: [...(q.items || []), newItem] }));
          navigate(`/studio/${created.quote_id}`, { replace: true });
        } else {
          const newItem = await addQuoteItem(quote.quote_id, itemData);
          setQuote((q) => ({ ...q, items: [...(q.items || []), newItem] }));
        }
        notify('Item added', { variant: 'success' });
      }
      setItemDrawerOpen(false);
      setEditingItem(null);
    } catch (err) {
      notify('Failed to save item', { message: err.message, variant: 'error' });
    }
  };

  const handleRemoveItem = async (itemId) => {
    if (!window.confirm('Remove this item?')) return;
    try {
      await removeQuoteItem(quote.quote_id, itemId);
      setQuote((q) => ({ ...q, items: q.items.filter((i) => i.item_id !== itemId) }));
      notify('Item removed', { variant: 'success' });
    } catch (err) {
      notify('Failed to remove item', { message: err.message, variant: 'error' });
    }
  };

  const handleDuplicateItem = async (item) => {
    try {
      const newItem = await addQuoteItem(quote.quote_id, {
        item_type: item.item_type,
        description: `${item.description} (copy)`,
        sku: item.sku,
        quantity: item.quantity,
        unit_price: item.unit_price,
        discount_type: item.discount_type,
        discount_value: item.discount_value,
        tax_code: item.tax_code,
        tax_rate: item.tax_rate,
        unit_of_measure: item.unit_of_measure,
      });
      setQuote((q) => ({ ...q, items: [...(q.items || []), newItem] }));
      notify('Item duplicated', { variant: 'success' });
    } catch (err) {
      notify('Failed to duplicate item', { message: err.message, variant: 'error' });
    }
  };

  const saveQuote = async () => {
    if (isNew && !quote.quote_id) return null;
    setSaving(true);
    try {
      const updated = await updateQuote(quote.quote_id, {
        title: quote.title,
        currency: quote.currency,
        valid_until: quote.valid_until,
        installation_charge: parseFloat(quote.installation_charge) || 0,
        delivery_charge: parseFloat(quote.delivery_charge) || 0,
        notes: quote.notes,
        internal_notes: quote.internal_notes,
      });
      setQuote(updated);
      return updated;
    } catch (err) {
      notify('Save failed', { message: err.message, variant: 'error' });
      return null;
    } finally {
      setSaving(false);
    }
  };

  const validateStep1 = () => {
    const p = {};
    if (!customer) p.customer = 'Customer is required.';
    if (!quote.title?.trim()) p.title = 'Quote title is required.';
    if (!quote.valid_until) p.valid_until = 'Valid until date is required.';
    setErrors(p);
    return Object.keys(p).length === 0;
  };

  const validateStep2 = () => {
    const p = {};
    if (!quote.items || quote.items.length === 0) p.items = 'At least one item is required.';
    setErrors(p);
    return Object.keys(p).length === 0;
  };

  const handleNext = async () => {
    if (step === 1 && !validateStep1()) return;
    if (step === 2 && !validateStep2()) return;

    if (isNew && !quote.quote_id && step === 1) {
      setSaving(true);
      try {
        const created = await createQuote({
          quote_type: 'PRODUCT',
          customer_id: customer.customer_id,
          title: quote.title,
          currency: quote.currency,
          valid_until: quote.valid_until,
          notes: quote.notes,
        });
        setQuote(created);
        navigate(`/studio/${created.quote_id}`, { replace: true });
      } catch (err) {
        notify('Failed to create quote', { message: err.message, variant: 'error' });
        setSaving(false);
        return;
      } finally {
        setSaving(false);
      }
    }

    if (!isNew || quote.quote_id) {
      await saveQuote();
    }

    setStep((s) => Math.min(s + 1, 3));
  };

  const handleBack = () => {
    setStep((s) => Math.max(s - 1, 1));
  };

  const handleGenerate = async () => {
    if (!quote.quote_id) return;
    setGenerating(true);
    try {
      await saveQuote();
      const result = await generateQuotePdf(quote.quote_id);
      notify('Quote document generated', { variant: 'success' });
      if (result.download_url) {
        window.open(result.download_url, '_blank');
      }
    } catch (err) {
      notify('Generation failed', { message: err.message, variant: 'error' });
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return <div className="page-loading">Loading quote...</div>;
  }

  if (error) {
    return (
      <div>
        <div className="form-error-banner" role="alert">{error.message}</div>
        <Button variant="secondary" onClick={() => navigate('/quotes')}>Back to Quotes</Button>
      </div>
    );
  }

  return (
    <div className="studio-layout">
      <div className="studio-wizard">
        <div className="studio-wizard__header">
          <Link to="/quotes" className="studio-wizard__back">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 12L6 8l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
            Quotes
          </Link>
          <div className="studio-wizard__title">
            {isNew && !quote.quote_id ? 'New Quote' : quote.quote_number || 'Edit Quote'}
          </div>
        </div>

        <div className="studio-steps">
          {STEPS.map((s) => (
            <div
              key={s.key}
              className={`studio-step${step === s.key ? ' is-active' : ''}${step > s.key ? ' is-done' : ''}`}
            >
              <div className="studio-step__number">
                {step > s.key ? (
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 8l3.5 3.5L13 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                ) : s.key}
              </div>
              <div className="studio-step__label">{s.label}</div>
            </div>
          ))}
        </div>

        <div className="studio-wizard__body">
          {step === 1 && (
            <div className="studio-step-content">
              <h3 className="studio-step-content__title">Customer & Quote Details</h3>

              <Field label="Customer Account" required error={errors} errorKey="customer">
                <CustomerSelector
                  value={customer}
                  onChange={handleCustomerChange}
                />
              </Field>

              {customer && (
                <div className="studio-customer-info">
                  <div className="studio-customer-info__row">
                    {customer.email && <span>{customer.email}</span>}
                    {customer.phone && <span>{customer.phone}</span>}
                  </div>
                  {customer.physical_address && (
                    <div className="studio-customer-info__address">{customer.physical_address}</div>
                  )}
                </div>
              )}

              <Field label="Quote Title" required error={errors} errorKey="title">
                <input
                  className="field__input"
                  value={quote.title}
                  onChange={setFormField('title')}
                  placeholder="e.g. Service Package, Equipment Supply"
                />
              </Field>

              <div className="form-row">
                <Field label="Currency">
                  <select className="field__input" value={quote.currency} onChange={setFormField('currency')}>
                    <option value="KES">KES</option>
                    <option value="USD">USD</option>
                    <option value="GBP">GBP</option>
                    <option value="EUR">EUR</option>
                  </select>
                </Field>
                <Field label="Valid Until" required error={errors} errorKey="valid_until">
                  <input
                    type="date"
                    className="field__input"
                    value={quote.valid_until}
                    onChange={setFormField('valid_until')}
                  />
                </Field>
              </div>

              <Field label="Customer Notes" hint="Visible on the quotation document.">
                <textarea
                  className="field__input field__input--textarea"
                  value={quote.notes}
                  onChange={setFormField('notes')}
                  rows={3}
                  placeholder="Notes visible to the customer..."
                />
              </Field>
            </div>
          )}

          {step === 2 && (
            <div className="studio-step-content">
              <div className="studio-step-content__header">
                <h3 className="studio-step-content__title">Quote Items</h3>
                <Button variant="primary" size="sm" onClick={handleAddItem}>+ Add Item</Button>
              </div>
              {errors.items && <div className="field__error">{errors.items}</div>}
              <QuoteItemsTable
                items={quote.items || []}
                currency={quote.currency}
                canEdit={true}
                onEdit={handleEditItem}
                onRemove={handleRemoveItem}
                onDuplicate={handleDuplicateItem}
              />
            </div>
          )}

          {step === 3 && (
            <div className="studio-step-content">
              <h3 className="studio-step-content__title">Pricing, Terms & Review</h3>

              <div className="form-row">
                <Field label={`Installation Charge (${quote.currency})`}>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    className="field__input"
                    value={quote.installation_charge || ''}
                    onChange={setFormField('installation_charge')}
                    placeholder="0.00"
                  />
                </Field>
                <Field label={`Delivery Charge (${quote.currency})`}>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    className="field__input"
                    value={quote.delivery_charge || ''}
                    onChange={setFormField('delivery_charge')}
                    placeholder="0.00"
                  />
                </Field>
              </div>

              <div className="studio-review-summary">
                <div className="studio-review-row">
                  <span>Items</span>
                  <span>{(quote.items || []).length} line item(s)</span>
                </div>
                <div className="studio-review-row">
                  <span>Subtotal</span>
                  <span>{formatCurrency(quote.subtotal || 0, quote.currency)}</span>
                </div>
                {(quote.discount_amount || 0) > 0 && (
                  <div className="studio-review-row">
                    <span>Discount</span>
                    <span>-{formatCurrency(quote.discount_amount, quote.currency)}</span>
                  </div>
                )}
                {(quote.tax_amount || 0) > 0 && (
                  <div className="studio-review-row">
                    <span>Tax</span>
                    <span>{formatCurrency(quote.tax_amount, quote.currency)}</span>
                  </div>
                )}
                {(quote.installation_charge || 0) > 0 && (
                  <div className="studio-review-row">
                    <span>Installation</span>
                    <span>{formatCurrency(quote.installation_charge, quote.currency)}</span>
                  </div>
                )}
                {(quote.delivery_charge || 0) > 0 && (
                  <div className="studio-review-row">
                    <span>Delivery</span>
                    <span>{formatCurrency(quote.delivery_charge, quote.currency)}</span>
                  </div>
                )}
                <div className="studio-review-row studio-review-row--total">
                  <span>Total</span>
                  <span>{formatCurrency(quote.grand_total || 0, quote.currency)}</span>
                </div>
              </div>

              <div className="studio-payment-terms">
                <div className="studio-section-label">Payment Terms</div>
                <div className="studio-payment-text">To be shared</div>
              </div>
            </div>
          )}
        </div>

        <div className="studio-wizard__footer">
          {step > 1 && (
            <Button variant="ghost" onClick={handleBack}>Back</Button>
          )}
          <div className="studio-wizard__footer-right">
            {step < 3 ? (
              <Button variant="primary" onClick={handleNext} loading={saving}>
                {isNew && !quote.quote_id ? 'Create & Continue' : 'Next'}
              </Button>
            ) : (
              <Button variant="primary" onClick={handleGenerate} loading={generating}>
                Generate Final Quote
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="studio-preview">
        <QuoteA4Preview
          quote={quote}
          customer={customer}
          staff={staff}
          currency={quote.currency}
        />
      </div>

      <ItemFormDrawer
        open={itemDrawerOpen}
        onClose={() => { setItemDrawerOpen(false); setEditingItem(null); }}
        item={editingItem}
        onSave={handleItemSaved}
        currency={quote.currency}
      />
    </div>
  );
}

export default QuoteStudioPage;
