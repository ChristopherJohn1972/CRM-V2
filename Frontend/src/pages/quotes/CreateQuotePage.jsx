import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { createQuote, listTemplates, listQuotes, duplicateQuote } from '../../api/quotes';
import { listCustomers } from '../../api/customers';
import PageHeader from '../../components/PageHeader';
import Button from '../../components/Button';
import QuoteTypeSelector from '../../components/quotes/QuoteTypeSelector';
import Field from '../../components/Field';
import FormSection from '../../components/FormSection';
import SearchBar from '../../components/SearchBar';
import StatusBadge from '../../components/StatusBadge';
import EmptyState from '../../components/EmptyState';
import { useToast } from '../../components/Toast';
import { useDebouncedValue } from '../../utils/useDebouncedValue';
import { formatCurrency, formatDate } from '../../utils/format';
import { CUSTOMER_TYPES, TEMPLATE_TYPE_LABELS } from '../../utils/constants';
import { getQuoteStatusLabel, getQuoteTypeLabel, getQuoteTypeColor, getQuoteStatusColor } from '../../utils/quotes';

export function CreateQuotePage() {
  const navigate = useNavigate();
  const { notify } = useToast();
  const [step, setStep] = useState('start');
  const [startMode, setStartMode] = useState(null);
  const [quoteType, setQuoteType] = useState(null);

  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [templateSearch, setTemplateSearch] = useState('');
  const debouncedTemplateSearch = useDebouncedValue(templateSearch, 350);

  const [sourceQuotes, setSourceQuotes] = useState([]);
  const [sourceQuoteSearch, setSourceQuoteSearch] = useState('');
  const debouncedSourceSearch = useDebouncedValue(sourceQuoteSearch, 350);
  const [sourceQuotePage, setSourceQuotePage] = useState(1);
  const [sourceQuoteTotal, setSourceQuoteTotal] = useState(0);
  const SOURCE_PAGE_SIZE = 10;

  // Customer search
  const [customerSearch, setCustomerSearch] = useState('');
  const debouncedCustomerSearch = useDebouncedValue(customerSearch, 350);
  const [customerResults, setCustomerResults] = useState([]);
  const [customerDropdownOpen, setCustomerDropdownOpen] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const customerDropdownRef = useRef(null);

  const [form, setForm] = useState({
    title: '',
    customer_id: '',
    currency: 'KES',
    valid_until: '',
    notes: '',
    internal_notes: '',
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [banner, setBanner] = useState(null);

  const loadTemplates = useCallback(async () => {
    try {
      const res = await listTemplates({ search: debouncedTemplateSearch || undefined, status: 'ACTIVE' });
      setTemplates(res.results || []);
    } catch (err) {
      // silent
    }
  }, [debouncedTemplateSearch]);

  const loadSourceQuotes = useCallback(async () => {
    try {
      const res = await listQuotes({
        search: debouncedSourceSearch || undefined,
        page: sourceQuotePage,
        page_size: SOURCE_PAGE_SIZE,
      });
      setSourceQuotes(res.results || []);
      setSourceQuoteTotal(res.count || 0);
    } catch (err) {
      // silent
    }
  }, [debouncedSourceSearch, sourceQuotePage]);

  useEffect(() => {
    if (step === 'template') loadTemplates();
    if (step === 'duplicate') loadSourceQuotes();
  }, [step, loadTemplates, loadSourceQuotes]);

  // Customer search
  const loadCustomers = useCallback(async () => {
    if (!debouncedCustomerSearch || debouncedCustomerSearch.length < 2) {
      setCustomerResults([]);
      return;
    }
    try {
      const res = await listCustomers({ search: debouncedCustomerSearch, page_size: 10 });
      setCustomerResults(res.results || []);
      setCustomerDropdownOpen(true);
    } catch { /* silent */ }
  }, [debouncedCustomerSearch]);

  useEffect(() => { loadCustomers(); }, [loadCustomers]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e) => {
      if (customerDropdownRef.current && !customerDropdownRef.current.contains(e.target)) {
        setCustomerDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleStartMode = (mode) => {
    setStartMode(mode);
    if (mode === 'blank') {
      setStep('type');
    } else if (mode === 'template') {
      setStep('template');
    } else {
      setStep('duplicate');
    }
  };

  const handleTypeSelect = (type) => {
    setQuoteType(type);
    setStep('details');
  };

  const handleTemplateSelect = (template) => {
    setSelectedTemplate(template);
    setQuoteType(template.template_type || 'SERVICE');
    setForm((f) => ({
      ...f,
      title: template.name || '',
      currency: template.currency || 'KES',
      notes: template.description || f.notes,
    }));
    setStep('details');
  };

  const handleDuplicateSelect = async (quote) => {
    setSubmitting(true);
    try {
      const newQuote = await duplicateQuote(quote.quote_id);
      notify('Quote duplicated', { message: `${newQuote.quote_number} created as a copy.`, variant: 'success' });
      navigate(`/quotes/${newQuote.quote_id}`);
    } catch (err) {
      setBanner(err.message || 'Could not duplicate quote.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCustomerSelect = (customer) => {
    setSelectedCustomer(customer);
    setForm((f) => ({ ...f, customer_id: customer.customer_id }));
    setCustomerSearch(`${customer.account_number} - ${customer.business_name || customer.full_name || ''}`);
    setCustomerDropdownOpen(false);
    if (errors.customer_id) {
      setErrors((prev) => { const next = { ...prev }; delete next.customer_id; return next; });
    }
  };

  const set = (key) => (e) => {
    setForm((f) => ({ ...f, [key]: e.target.value }));
    if (errors[key]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    }
    setBanner(null);
  };

  const validate = () => {
    const problems = {};
    if (!form.customer_id) problems.customer_id = 'Customer is required.';
    return problems;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setBanner(null);

    const problems = validate();
    if (Object.keys(problems).length) {
      setErrors(problems);
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        quote_type: quoteType,
        customer_id: parseInt(form.customer_id, 10),
        title: form.title || undefined,
        currency: form.currency || undefined,
        valid_until: form.valid_until || undefined,
        notes: form.notes || undefined,
        internal_notes: form.internal_notes || undefined,
      };
      if (selectedTemplate) {
        payload.template_id = selectedTemplate.template_id;
      }
      const created = await createQuote(payload);
      notify('Quote created', { message: `${created.quote_number} created successfully.`, variant: 'success' });
      navigate(`/quotes/${created.quote_id}`);
    } catch (err) {
      setBanner(err.message || 'Could not create quote.');
      if (err.fieldErrors) setErrors(err.fieldErrors);
    } finally {
      setSubmitting(false);
    }
  };

  const backToStart = () => {
    setStep('start');
    setStartMode(null);
    setSelectedTemplate(null);
    setQuoteType(null);
    setForm({ title: '', customer_id: '', currency: 'KES', valid_until: '', notes: '', internal_notes: '' });
    setSelectedCustomer(null);
    setCustomerSearch('');
    setErrors({});
    setBanner(null);
  };

  return (
    <div>
      <PageHeader
        title="Create Quote"
        subtitle={
          step === 'start' ? 'How would you like to start?' :
          step === 'type' ? 'Select the type of quotation.' :
          step === 'template' ? 'Choose a template to start from.' :
          step === 'duplicate' ? 'Select a quote to duplicate.' :
          `Creating a ${quoteType?.toLowerCase()} quote`
        }
        actions={
          step !== 'start' ? (
            <Button variant="ghost" onClick={() => {
              if (step === 'details') setStep(selectedTemplate ? 'template' : 'type');
              else backToStart();
            }}>
              Back
            </Button>
          ) : undefined
        }
      />

      {step === 'start' && (
        <div className="form-section">
          <div className="form-section__header">
            <h2 className="form-section__title">How would you like to start?</h2>
            <p className="form-section__desc">Choose an option to create your quotation.</p>
          </div>
          <div className="quote-type-selector__grid">
            <button className="quote-type-card" onClick={() => handleStartMode('blank')}>
              <div className="quote-type-card__icon">
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
                  <rect x="6" y="4" width="20" height="24" rx="2" stroke="currentColor" strokeWidth="2" />
                  <path d="M12 16h8M16 12v8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <div className="quote-type-card__content">
                <div className="quote-type-card__title">Blank Quote</div>
                <div className="quote-type-card__description">Start from scratch with an empty quotation.</div>
              </div>
            </button>

            <button className="quote-type-card" onClick={() => handleStartMode('template')}>
              <div className="quote-type-card__icon">
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
                  <rect x="4" y="4" width="24" height="24" rx="2" stroke="currentColor" strokeWidth="2" />
                  <path d="M10 10h12M10 16h12M10 22h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <div className="quote-type-card__content">
                <div className="quote-type-card__title">From Template</div>
                <div className="quote-type-card__description">Use a reusable template as your starting point.</div>
              </div>
            </button>

            <button className="quote-type-card" onClick={() => handleStartMode('duplicate')}>
              <div className="quote-type-card__icon">
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
                  <rect x="8" y="8" width="16" height="16" rx="2" stroke="currentColor" strokeWidth="2" />
                  <path d="M8 12H6a2 2 0 01-2-2V6a2 2 0 012-2h4a2 2 0 012 2v2" stroke="currentColor" strokeWidth="2" />
                  <path d="M14 14h4M14 18h4M14 22h4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <div className="quote-type-card__content">
                <div className="quote-type-card__title">Duplicate Existing Quote</div>
                <div className="quote-type-card__description">Copy an existing quote as a starting point.</div>
              </div>
            </button>
          </div>
        </div>
      )}

      {step === 'type' && (
        <QuoteTypeSelector selected={quoteType} onSelect={handleTypeSelect} />
      )}

      {step === 'template' && (
        <div className="form-section">
          <div className="form-section__header">
            <h2 className="form-section__title">Select Template</h2>
            <p className="form-section__desc">Choose an active template to pre-populate your quote.</p>
          </div>
          <div className="toolbar" style={{ marginBottom: 'var(--space-4)' }}>
            <div className="toolbar__search">
              <SearchBar
                value={templateSearch}
                onChange={(v) => { setTemplateSearch(v); setSourceQuotePage(1); }}
                placeholder="Search templates..."
                label="Search templates"
              />
            </div>
          </div>
          {templates.length === 0 ? (
            <EmptyState
              title="No active templates"
              body="Create a template first, or start with a blank quote."
              action={<Button variant="secondary" onClick={backToStart}>Go Back</Button>}
            />
          ) : (
            <div className="quote-type-selector__grid">
              {templates.map((t) => (
                <button key={t.template_id} className="quote-type-card" onClick={() => handleTemplateSelect(t)}>
                  <div className="quote-type-card__content">
                    <div className="quote-type-card__title">{t.name}</div>
                    <div className="quote-type-card__description">
                      {t.template_type && <span className="badge badge--neutral" style={{ marginRight: 8 }}>{TEMPLATE_TYPE_LABELS[t.template_type] || t.template_type}</span>}
                      {t.description || 'No description'}
                    </div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-2)' }}>
                      Version {t.version || 1}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {step === 'duplicate' && (
        <div className="form-section">
          <div className="form-section__header">
            <h2 className="form-section__title">Select Quote to Duplicate</h2>
            <p className="form-section__desc">Choose an existing quote to copy. All items and details will be carried over.</p>
          </div>
          {banner && <div className="form-error-banner" role="alert">{banner}</div>}
          <div className="toolbar" style={{ marginBottom: 'var(--space-4)' }}>
            <div className="toolbar__search">
              <SearchBar
                value={sourceQuoteSearch}
                onChange={(v) => { setSourceQuoteSearch(v); setSourceQuotePage(1); }}
                placeholder="Search by quote number or title..."
                label="Search quotes"
              />
            </div>
          </div>
          {sourceQuotes.length === 0 ? (
            <EmptyState
              title="No quotes found"
              body="Create a new quote first, or adjust your search."
              action={<Button variant="secondary" onClick={backToStart}>Go Back</Button>}
            />
          ) : (
            <div className="card-stack">
              {sourceQuotes.map((q) => (
                <div key={q.quote_id} className="card quote-duplicate-card">
                  <div className="card__header">
                    <div className="card__title">{q.quote_number}</div>
                    <StatusBadge
                      label={getQuoteStatusLabel(q.status)}
                      style={{ background: getQuoteStatusColor(q.status).bg, color: getQuoteStatusColor(q.status).text }}
                    />
                  </div>
                  {q.title && <div className="card__subtitle">{q.title}</div>}
                  <div className="card__meta">
                    {q.quote_type && <span className="badge" style={{ background: getQuoteTypeColor(q.quote_type).bg, color: getQuoteTypeColor(q.quote_type).text }}>{getQuoteTypeLabel(q.quote_type)}</span>}
                    {q.total_amount != null && <span>{formatCurrency(q.total_amount, q.currency)}</span>}
                    {q.quote_date && <span>{formatDate(q.quote_date)}</span>}
                  </div>
                  <div className="card__actions">
                    <Button
                      variant="primary"
                      size="sm"
                      loading={submitting}
                      onClick={() => handleDuplicateSelect(q)}
                    >
                      Duplicate
                    </Button>
                  </div>
                </div>
              ))}
              {sourceQuoteTotal > SOURCE_PAGE_SIZE && (
                <div className="pagination">
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={sourceQuotePage <= 1}
                    onClick={() => setSourceQuotePage((p) => p - 1)}
                  >
                    Previous
                  </Button>
                  <span className="pagination__info">
                    Page {sourceQuotePage} of {Math.ceil(sourceQuoteTotal / SOURCE_PAGE_SIZE)}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={sourceQuotePage * SOURCE_PAGE_SIZE >= sourceQuoteTotal}
                    onClick={() => setSourceQuotePage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {step === 'details' && (
        <form className="form" onSubmit={handleSubmit} noValidate>
          {banner && <div className="form-error-banner" role="alert">{banner}</div>}

          {selectedTemplate && (
            <div className="muted-banner">
              Starting from template: <strong>{selectedTemplate.name}</strong> (v{selectedTemplate.version || 1})
            </div>
          )}

          <FormSection title="Customer" description="Select the customer for this quotation.">
            <Field label="Customer" required htmlFor="cq-customer" error={errors} errorKey="customer_id">
              <div className="customer-search-wrapper" ref={customerDropdownRef}>
                <input
                  id="cq-customer"
                  type="text"
                  className="field__input"
                  value={customerSearch}
                  onChange={(e) => {
                    setCustomerSearch(e.target.value);
                    setSelectedCustomer(null);
                    setForm((f) => ({ ...f, customer_id: '' }));
                  }}
                  onFocus={() => customerResults.length > 0 && setCustomerDropdownOpen(true)}
                  placeholder="Search by account number or name..."
                  autoComplete="off"
                />
                {customerDropdownOpen && customerResults.length > 0 && (
                  <div className="customer-search-dropdown">
                    {customerResults.map((c) => (
                      <button
                        key={c.customer_id}
                        type="button"
                        className="customer-search-item"
                        onClick={() => handleCustomerSelect(c)}
                      >
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
              <div className="customer-selected-info">
                <span className="badge badge--success">Selected</span>
                <span>{selectedCustomer.account_number} — {selectedCustomer.business_name || selectedCustomer.full_name}</span>
              </div>
            )}
          </FormSection>

          <FormSection title="Quote Details" description="Basic information about this quotation.">
            <Field label="Title" htmlFor="cq-title" hint="Optional description for internal reference.">
              <input
                id="cq-title"
                className="field__input"
                value={form.title}
                onChange={set('title')}
                placeholder="e.g. Service Package, Equipment Supply"
              />
            </Field>

            <div className="form-row">
              <Field label="Currency" htmlFor="cq-currency">
                <select id="cq-currency" className="field__input" value={form.currency} onChange={set('currency')}>
                  <option value="KES">KES</option>
                  <option value="USD">USD</option>
                  <option value="GBP">GBP</option>
                  <option value="EUR">EUR</option>
                </select>
              </Field>

              <Field label="Valid Until" htmlFor="cq-valid-until">
                <input
                  id="cq-valid-until"
                  type="date"
                  className="field__input"
                  value={form.valid_until}
                  onChange={set('valid_until')}
                />
              </Field>
            </div>
          </FormSection>

          <FormSection title="Notes" description="Optional notes for this quotation.">
            <Field label="Customer Notes" htmlFor="cq-notes" hint="Visible to the customer on the quotation document.">
              <textarea
                id="cq-notes"
                className="field__input field__input--textarea"
                value={form.notes}
                onChange={set('notes')}
                rows={3}
                placeholder="Notes visible to the customer..."
              />
            </Field>

            <Field label="Internal Notes" htmlFor="cq-internal-notes" hint="Internal only. Never included in the customer document.">
              <textarea
                id="cq-internal-notes"
                className="field__input field__input--textarea"
                value={form.internal_notes}
                onChange={set('internal_notes')}
                rows={3}
                placeholder="Internal notes..."
              />
            </Field>
          </FormSection>

          <div className="form-actions">
            <Button type="button" variant="ghost" onClick={() => navigate('/quotes')}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={submitting}>
              Create Quote
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}

export default CreateQuotePage;
