import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getQuote, updateQuote, addQuoteItem, updateQuoteItem, removeQuoteItem, recalculateQuote, submitForApproval, approveQuote, rejectQuote, sendQuote, cancelQuote, duplicateQuote, getQuoteActivity, getQuoteApprovals } from '../../api/quotes';
import PageHeader from '../../components/PageHeader';
import Button from '../../components/Button';
import Field from '../../components/Field';
import FormSection from '../../components/FormSection';
import StatusBadge from '../../components/StatusBadge';
import { useToast } from '../../components/Toast';
import CustomerSelector from '../../components/quotes/CustomerSelector';
import QuoteSummaryPanel from '../../components/quotes/QuoteSummaryPanel';
import QuoteItemsTable from '../../components/quotes/QuoteItemsTable';
import ItemFormDrawer from '../../components/quotes/ItemFormDrawer';
import QuoteActivityTimeline from '../../components/quotes/QuoteActivityTimeline';
import SendDialog from '../../components/quotes/SendDialog';
import { formatDate } from '../../utils/format';
import { QUOTE_STATUS_LABELS, QUOTE_TYPE_LABELS } from '../../utils/constants';
import { getQuoteStatusLabel, getQuoteStatusColor, getQuoteTypeLabel, getQuoteTypeColor, canEdit, canSubmitForApproval, canApprove, canSend, canCancel } from '../../utils/quotes';

function MoreActionsMenu({ status, onAction }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const items = [
    { key: 'duplicate', label: 'Duplicate Quote', show: true },
    { key: 'cancel', label: 'Cancel Quote', show: canCancel(status), danger: true },
  ].filter((i) => i.show);

  if (items.length === 0) return null;

  return (
    <div className="dropdown" ref={ref}>
      <button type="button" className="btn btn--ghost btn--sm" onClick={() => setOpen(!open)}>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="3" r="1.5" fill="currentColor"/><circle cx="8" cy="8" r="1.5" fill="currentColor"/><circle cx="8" cy="13" r="1.5" fill="currentColor"/></svg>
        More
      </button>
      {open && (
        <div className="dropdown__menu">
          {items.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`dropdown__item${item.danger ? ' dropdown__item--danger' : ''}`}
              onClick={() => { onAction(item.key); setOpen(false); }}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function QuoteWorkspacePage() {
  const { quoteId } = useParams();
  const navigate = useNavigate();
  const { notify } = useToast();

  const [quote, setQuote] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState('saved');

  const [editForm, setEditForm] = useState({});
  const [itemDrawerOpen, setItemDrawerOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [sendDialogOpen, setSendDialogOpen] = useState(false);
  const [activity, setActivity] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [activeTab, setActiveTab] = useState('items');

  const abortRef = useRef(null);
  const saveTimerRef = useRef(null);

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const data = await getQuote(quoteId);
      setQuote(data);
      setEditForm({
        title: data.title || '',
        quote_date: data.quote_date || '',
        valid_until: data.valid_until || '',
        currency: data.currency || 'KES',
        notes: data.notes || '',
        internal_notes: data.internal_notes || '',
        terms_and_conditions: data.terms_and_conditions || '',
      });
      setSaveStatus('saved');
    } catch (err) {
      if (err.name !== 'AbortError') setError(err);
    } finally {
      if (!abortRef.current || abortRef.current.signal === controller.signal) setLoading(false);
    }
  }, [quoteId]);

  const loadActivity = useCallback(async () => {
    try {
      const data = await getQuoteActivity(quoteId);
      setActivity(data);
    } catch { /* silent */ }
  }, [quoteId]);

  const loadApprovals = useCallback(async () => {
    try {
      const data = await getQuoteApprovals(quoteId);
      setApprovals(data);
    } catch { /* silent */ }
  }, [quoteId]);

  useEffect(() => {
    load();
    loadActivity();
    loadApprovals();
    return () => abortRef.current?.abort();
  }, [load, loadActivity, loadApprovals]);

  const setFormField = (key) => (e) => {
    setEditForm((f) => ({ ...f, [key]: e.target.value }));
    setSaveStatus('unsaved');
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => handleSave(), 2000);
  };

  const handleSave = async () => {
    if (!quote) return;
    setSaving(true);
    try {
      const updated = await updateQuote(quoteId, {
        title: editForm.title || undefined,
        quote_date: editForm.quote_date || undefined,
        valid_until: editForm.valid_until || undefined,
        currency: editForm.currency || undefined,
        notes: editForm.notes || undefined,
        internal_notes: editForm.internal_notes || undefined,
        terms_and_conditions: editForm.terms_and_conditions || undefined,
      });
      setQuote(updated);
      setSaveStatus('saved');
    } catch (err) {
      notify('Save failed', { message: err.message, variant: 'error' });
      setSaveStatus('error');
    } finally {
      setSaving(false);
    }
  };

  const handleCustomerChange = async (customer) => {
    try {
      const updated = await updateQuote(quoteId, {
        customer_id: customer ? customer.customer_id : null,
      });
      setQuote(updated);
      setSaveStatus('saved');
    } catch (err) {
      notify('Failed to update customer', { message: err.message, variant: 'error' });
    }
  };

  const handleItemAdded = async (itemData) => {
    try {
      const newItem = await addQuoteItem(quoteId, itemData);
      setQuote((q) => ({ ...q, items: [...(q.items || []), newItem] }));
      setItemDrawerOpen(false);
      setEditingItem(null);
      notify('Item added', { variant: 'success' });
      load();
    } catch (err) {
      notify('Failed to add item', { message: err.message, variant: 'error' });
    }
  };

  const handleItemUpdated = async (itemData) => {
    if (!editingItem) return;
    try {
      const updated = await updateQuoteItem(quoteId, editingItem.item_id, itemData);
      setQuote((q) => ({
        ...q,
        items: q.items.map((i) => (i.item_id === editingItem.item_id ? updated : i)),
      }));
      setItemDrawerOpen(false);
      setEditingItem(null);
      notify('Item updated', { variant: 'success' });
      load();
    } catch (err) {
      notify('Failed to update item', { message: err.message, variant: 'error' });
    }
  };

  const handleItemRemoved = async (itemId) => {
    if (!window.confirm('Remove this item?')) return;
    try {
      await removeQuoteItem(quoteId, itemId);
      setQuote((q) => ({ ...q, items: q.items.filter((i) => i.item_id !== itemId) }));
      notify('Item removed', { variant: 'success' });
      load();
    } catch (err) {
      notify('Failed to remove item', { message: err.message, variant: 'error' });
    }
  };

  const handleDuplicateItem = async (item) => {
    try {
      const newItem = await addQuoteItem(quoteId, {
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
      load();
    } catch (err) {
      notify('Failed to duplicate item', { message: err.message, variant: 'error' });
    }
  };

  const handleEditItem = (item) => {
    setEditingItem(item);
    setItemDrawerOpen(true);
  };

  const handleAddItem = () => {
    setEditingItem(null);
    setItemDrawerOpen(true);
  };

  const handleWorkflowAction = async (action) => {
    try {
      let result;
      switch (action) {
        case 'submit-approval':
          result = await submitForApproval(quoteId);
          notify('Submitted for approval', { variant: 'success' });
          break;
        case 'approve':
          result = await approveQuote(quoteId);
          notify('Quote approved', { variant: 'success' });
          break;
        case 'reject':
          result = await rejectQuote(quoteId);
          notify('Quote rejected', { variant: 'success' });
          break;
        case 'send':
          setSendDialogOpen(true);
          return;
        case 'cancel':
          if (!window.confirm('Cancel this quote?')) return;
          result = await cancelQuote(quoteId);
          notify('Quote cancelled', { variant: 'success' });
          break;
        case 'duplicate':
          result = await duplicateQuote(quoteId);
          notify('Quote duplicated', { variant: 'success' });
          navigate(`/quotes/${result.quote_id}`);
          return;
        default:
          return;
      }
      if (result) {
        setQuote(result);
        loadActivity();
        loadApprovals();
      }
    } catch (err) {
      notify('Action failed', { message: err.message, variant: 'error' });
    }
  };

  const handleSendConfirm = async (customerId) => {
    try {
      const result = await sendQuote(quoteId, { customer_account_id: customerId });
      setQuote(result);
      setSendDialogOpen(false);
      notify('Quote sent', { variant: 'success' });
      loadActivity();
    } catch (err) {
      notify('Send failed', { message: err.message, variant: 'error' });
    }
  };

  const getPrimaryAction = () => {
    if (!quote) return null;
    if (canSubmitForApproval(quote.status)) {
      return { label: 'Submit for Approval', action: 'submit-approval', variant: 'primary' };
    }
    if (canSend(quote.status)) {
      return { label: 'Send to Customer', action: 'send', variant: 'primary' };
    }
    if (canApprove(quote.status)) {
      return { label: 'Approve Quote', action: 'approve', variant: 'primary' };
    }
    return null;
  };

  if (loading) {
    return <div className="page-loading">Loading quote...</div>;
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Quote" subtitle="Could not load quote" />
        <div className="form-error-banner" role="alert">{error.message}</div>
        <Button variant="secondary" onClick={() => navigate('/quotes')}>Back to Quotes</Button>
      </div>
    );
  }

  if (!quote) return null;

  const statusColors = getQuoteStatusColor(quote.status);
  const primaryAction = getPrimaryAction();
  const isEdited = quote.updated_at && quote.created_at && quote.updated_at !== quote.created_at;

  return (
    <div className="quote-workspace">
      {/* Quote Header */}
      <div className="quote-header">
        <div className="quote-header__top">
          <Link to={`/quotes/${quoteId}/view`} className="quote-header__back">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 12L6 8l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
            Back to Quote
          </Link>
          <div className="quote-header__save-status">
            {saveStatus === 'saving' ? (
              <span className="quote-header__save-indicator quote-header__save-indicator--saving">Saving...</span>
            ) : saveStatus === 'unsaved' ? (
              <span className="quote-header__save-indicator quote-header__save-indicator--unsaved">Unsaved changes</span>
            ) : saveStatus === 'error' ? (
              <span className="quote-header__save-indicator quote-header__save-indicator--error">Save error</span>
            ) : (
              <span className="quote-header__save-indicator quote-header__save-indicator--saved">Saved</span>
            )}
          </div>
        </div>

        <div className="quote-header__main">
          <div className="quote-header__left">
            <div className="quote-header__number">{quote.quote_number}</div>
            <h1 className="quote-header__title">
              {isEdited ? 'Edit Quote' : 'Create Quote'}
            </h1>
          </div>
          <div className="quote-header__right">
            <div className="quote-header__badges">
              <span className="badge" style={{ background: getQuoteTypeColor(quote.quote_type).bg, color: getQuoteTypeColor(quote.quote_type).text }}>{getQuoteTypeLabel(quote.quote_type)}</span>
              <StatusBadge
                label={getQuoteStatusLabel(quote.status)}
                style={{ background: statusColors.bg, color: statusColors.text }}
              />
            </div>
            <div className="quote-header__meta">
              {quote.owner_name && <span className="quote-header__owner">{quote.owner_name}</span>}
              <span className="quote-header__date">Last saved {formatDate(quote.updated_at)}</span>
            </div>
            <div className="quote-header__actions">
              <MoreActionsMenu status={quote.status} onAction={handleWorkflowAction} />
              {primaryAction && (
                <Button variant={primaryAction.variant} size="sm" onClick={() => handleWorkflowAction(primaryAction.action)}>
                  {primaryAction.label}
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="quote-workspace__layout">
        <div className="quote-workspace__main">
          {/* Customer Selection */}
          <FormSection
            title="Customer"
            actions={
              canEdit(quote.status) ? (
                <Link to="/clients/new" className="btn btn--ghost btn--sm">+ New Customer</Link>
              ) : null
            }
          >
            <CustomerSelector
              value={quote.customer || null}
              onChange={handleCustomerChange}
              disabled={!canEdit(quote.status)}
            />
            {quote.customer && (
              <div className="quote-workspace__customer-details">
                <div className="quote-workspace__customer-detail">
                  <span className="field-display__label">Email</span>
                  <span className="field-display__value">{quote.customer.email || '—'}</span>
                </div>
                <div className="quote-workspace__customer-detail">
                  <span className="field-display__label">Phone</span>
                  <span className="field-display__value">{quote.customer.phone || '—'}</span>
                </div>
                <div className="quote-workspace__customer-detail">
                  <span className="field-display__label">Account</span>
                  <span className="field-display__value">{quote.customer.customer_number || '—'}</span>
                </div>
              </div>
            )}
          </FormSection>

          {/* Quote Details */}
          <FormSection title="Quote Details">
            <Field label="Title" htmlFor="qw-title">
              <input id="qw-title" className="field__input" value={editForm.title} onChange={setFormField('title')} placeholder="Quote title" />
            </Field>
            <div className="form-row">
              <Field label="Quote Date" htmlFor="qw-date">
                <input id="qw-date" type="date" className="field__input" value={editForm.quote_date} onChange={setFormField('quote_date')} />
              </Field>
              <Field label="Valid Until" htmlFor="qw-valid">
                <input id="qw-valid" type="date" className="field__input" value={editForm.valid_until} onChange={setFormField('valid_until')} />
              </Field>
            </div>
            <Field label="Currency" htmlFor="qw-currency">
              <select id="qw-currency" className="field__input" value={editForm.currency} onChange={setFormField('currency')}>
                <option value="KES">KES</option>
                <option value="USD">USD</option>
                <option value="GBP">GBP</option>
                <option value="EUR">EUR</option>
              </select>
            </Field>
          </FormSection>

          {/* Items */}
          <FormSection
            title="Items"
            actions={
              canEdit(quote.status) ? (
                <Button variant="primary" size="sm" onClick={handleAddItem}>+ Add Item</Button>
              ) : null
            }
          >
            <QuoteItemsTable
              items={quote.items || []}
              currency={quote.currency}
              canEdit={canEdit(quote.status)}
              onEdit={handleEditItem}
              onRemove={handleItemRemoved}
              onDuplicate={handleDuplicateItem}
            />
          </FormSection>

          {/* Notes & Terms */}
          <FormSection title="Notes & Terms">
            <Field label="Customer Notes" htmlFor="qw-notes">
              <textarea id="qw-notes" className="field__input field__input--textarea" value={editForm.notes} onChange={setFormField('notes')} rows={2} />
            </Field>
            <Field label="Internal Notes" htmlFor="qw-internal">
              <textarea id="qw-internal" className="field__input field__input--textarea" value={editForm.internal_notes} onChange={setFormField('internal_notes')} rows={2} />
            </Field>
            <Field label="Terms & Conditions" htmlFor="qw-terms">
              <textarea id="qw-terms" className="field__input field__input--textarea" value={editForm.terms_and_conditions} onChange={setFormField('terms_and_conditions')} rows={3} />
            </Field>
          </FormSection>

          {/* Activity */}
          <FormSection title="Activity">
            <QuoteActivityTimeline events={activity} />
          </FormSection>
        </div>

        {/* Right Summary Panel */}
        <div className="quote-workspace__sidebar">
          <QuoteSummaryPanel
            currency={quote.currency}
            subtotal={quote.subtotal}
            discountAmount={quote.discount_amount}
            taxAmount={quote.tax_amount}
            additionalCharges={quote.additional_charges}
            grandTotal={quote.grand_total}
            itemCount={(quote.items || []).length}
            discountType={quote.discount_type}
            discountValue={quote.discount_value}
          />

          {approvals.length > 0 && (
            <div className="quote-approvals-panel">
              <h4>Approvals</h4>
              {approvals.map((a) => (
                <div key={a.approval_id} className="quote-approval-row">
                  <StatusBadge
                    label={a.status?.split('.').pop() || a.status}
                    variant={a.status?.includes('APPROVED') ? 'success' : a.status?.includes('REJECTED') ? 'danger' : 'warning'}
                  />
                  <span className="quote-approval-row__date">{formatDate(a.requested_at)}</span>
                </div>
              ))}
            </div>
          )}

          {canApprove(quote.status) && (
            <div className="quote-approval-actions">
              <Button variant="primary" size="sm" block onClick={() => handleWorkflowAction('approve')}>Approve</Button>
              <Button variant="danger" size="sm" block onClick={() => handleWorkflowAction('reject')}>Reject</Button>
            </div>
          )}
        </div>
      </div>

      <ItemFormDrawer
        open={itemDrawerOpen}
        onClose={() => { setItemDrawerOpen(false); setEditingItem(null); }}
        item={editingItem}
        onSave={editingItem ? handleItemUpdated : handleItemAdded}
        currency={quote.currency}
      />

      <SendDialog
        open={sendDialogOpen}
        onClose={() => setSendDialogOpen(false)}
        onConfirm={handleSendConfirm}
        quote={quote}
      />
    </div>
  );
}

export default QuoteWorkspacePage;
