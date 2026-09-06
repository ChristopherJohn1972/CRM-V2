import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { listQuotes, cancelQuote, deleteQuote } from '../../api/quotes';
import { useAuth } from '../../auth/AuthContext';
import PageHeader from '../../components/PageHeader';
import Button from '../../components/Button';
import SearchBar from '../../components/SearchBar';
import FilterBar from '../../components/FilterBar';
import DataTable from '../../components/DataTable';
import StatusBadge from '../../components/StatusBadge';
import Pagination from '../../components/Pagination';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import { PermissionGate } from '../../components/PermissionGate';
import { useToast } from '../../components/Toast';
import { formatDate } from '../../utils/format';
import { QUOTE_PERMISSIONS } from '../../utils/constants';
import {
  getQuoteStatusLabel,
  getQuoteStatusColor,
  getQuoteTypeLabel,
  getQuoteTypeColor,
  formatQuoteAmount,
  getExpiryWarning,
} from '../../utils/quotes';
import { useDebouncedValue } from '../../utils/useDebouncedValue';

function StatCard({ label, value, variant = 'neutral' }) {
  return (
    <div className={`quote-stat-card quote-stat-card--${variant}`}>
      <div className="quote-stat-card__value">{value}</div>
      <div className="quote-stat-card__label">{label}</div>
    </div>
  );
}

function QuoteNumberLink({ quote }) {
  return (
    <Link className="data-table__accent" to={`/quotes/${quote.quote_id}/view`}>
      {quote.quote_number}
    </Link>
  );
}

function MobileQuoteCard({ quote }) {
  const expiry = getExpiryWarning(quote.valid_until);
  return (
    <div className="mobile-quote-card">
      <div className="mobile-quote-card__row">
        <Link className="data-table__accent" to={`/quotes/${quote.quote_id}/view`}>
          {quote.quote_number}
        </Link>
        <StatusBadge
          label={getQuoteStatusLabel(quote.status)}
          style={{
            background: getQuoteStatusColor(quote.status).bg,
            color: getQuoteStatusColor(quote.status).text,
          }}
        />
      </div>
      <div className="mobile-quote-card__meta">
        <span style={{ fontWeight: 600 }}>{quote.title || getQuoteTypeLabel(quote.quote_type)}</span>
      </div>
      <div className="mobile-quote-card__meta">
        <span>{formatQuoteAmount(quote.grand_total, quote.currency)}</span>
        <span>{formatDate(quote.quote_date)}</span>
      </div>
      {expiry === 'expiring-soon' && (
        <div className="mobile-quote-card__warning">Expiring soon</div>
      )}
    </div>
  );
}

export function QuoteListPage() {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const { notify } = useToast();
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search, 350);

  const [filters, setFilters] = useState({ status: '', quote_type: '' });
  const [data, setData] = useState({ count: 0, results: [] });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState({ total: 0, drafts: 0, pending: 0, sent: 0, accepted: 0, expiringSoon: 0 });

  const abortRef = useRef(null);

  const handleDelete = async (quote) => {
    const confirmed = window.confirm(
      `Delete Quote?\n\nAre you sure you want to delete ${quote.quote_number}?\n\nThis action will permanently remove the quote from the active quotes list.`
    );
    if (!confirmed) return;
    try {
      await deleteQuote(quote.quote_id);
      notify('Quote deleted successfully', { variant: 'success' });
      load();
    } catch (err) {
      notify('Delete failed', { message: err.message, variant: 'error' });
    }
  };

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const res = await listQuotes({
        search: debouncedSearch || undefined,
        status: filters.status || undefined,
        quote_type: filters.quote_type || undefined,
        page,
        page_size: pageSize,
      });
      setData(res);

      // Calculate summary from all results (use first page for quick stats)
      const counts = { total: res.count, drafts: 0, pending: 0, sent: 0, accepted: 0, expiringSoon: 0 };
      for (const q of res.results) {
        const s = q.status?.split('.').pop() || q.status;
        if (s === 'DRAFT') counts.drafts++;
        if (s === 'PENDING_APPROVAL') counts.pending++;
        if (s === 'SENT' || s === 'VIEWED') counts.sent++;
        if (s === 'ACCEPTED') counts.accepted++;
        if (getExpiryWarning(q.valid_until) === 'expiring-soon') counts.expiringSoon++;
      }
      setSummary(counts);
    } catch (err) {
      if (err.name !== 'AbortError') setError(err);
    } finally {
      if (!abortRef.current || abortRef.current.signal === controller.signal) setLoading(false);
    }
  }, [debouncedSearch, filters.status, filters.quote_type, page, pageSize]);

  useEffect(() => {
    load();
    return () => abortRef.current?.abort();
  }, [load]);

  const resetPage = (updater) => {
    setPage(1);
    updater();
  };

  const columns = [
    {
      key: 'quote_number',
      header: 'Quote #',
      render: (r) => <QuoteNumberLink quote={r} />,
    },
    {
      key: 'title',
      header: 'Title',
      render: (r) => (
        <span style={{ fontWeight: 500 }}>
          {r.title || getQuoteTypeLabel(r.quote_type)}
        </span>
      ),
    },
    {
      key: 'quote_type',
      header: 'Type',
      render: (r) => (
        <span className="badge" style={{ background: getQuoteTypeColor(r.quote_type).bg, color: getQuoteTypeColor(r.quote_type).text }}>{getQuoteTypeLabel(r.quote_type)}</span>
      ),
    },
    {
      key: 'quote_date',
      header: 'Date',
      render: (r) => <span className="cell-secondary cell-nowrap">{formatDate(r.quote_date)}</span>,
    },
    {
      key: 'valid_until',
      header: 'Valid Until',
      render: (r) => {
        const expiry = getExpiryWarning(r.valid_until);
        return (
          <span className={`cell-secondary cell-nowrap${expiry === 'expiring-soon' ? ' text-warning' : ''}`}>
            {formatDate(r.valid_until)}
          </span>
        );
      },
    },
    {
      key: 'grand_total',
      header: 'Amount',
      render: (r) => (
        <span style={{ fontWeight: 600 }}>
          {formatQuoteAmount(r.grand_total, r.currency)}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (r) => {
        const colors = getQuoteStatusColor(r.status);
        return (
          <StatusBadge
            label={getQuoteStatusLabel(r.status)}
            style={{ background: colors.bg, color: colors.text }}
          />
        );
      },
    },
    {
      key: 'actions',
      header: '',
      render: (r) => (
        <button
          type="button"
          className="icon-btn icon-btn--delete"
          title="Delete quote"
          onClick={(e) => { e.stopPropagation(); handleDelete(r); }}
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M5.333 4V2.667a1.333 1.333 0 011.334-1.334h2.666a1.333 1.333 0 011.334 1.334V4m2 0v9.333a1.333 1.333 0 01-1.334 1.334H4.667a1.333 1.333 0 01-1.334-1.334V4h9.334z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </button>
      ),
    },
  ];

  const createButton = (
    <PermissionGate permission={QUOTE_PERMISSIONS.CREATE}>
      <Button variant="primary" onClick={() => navigate('/studio')}>
        Create Quote
      </Button>
    </PermissionGate>
  );

  const emptyTitle = debouncedSearch || filters.status || filters.quote_type
    ? 'No quotes match your search'
    : 'No quotes yet';
  const emptyBody = debouncedSearch || filters.status || filters.quote_type
    ? 'Try adjusting your search or filters.'
    : 'Create your first quotation to get started with Quote Studio.';

  return (
    <div>
      <PageHeader
        title="Quote Studio"
        subtitle="Create, manage and send professional quotations."
        actions={
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <Button variant="primary" onClick={() => navigate('/studio')}>
              + New Quote
            </Button>
          </div>
        }
      />

      <div className="quote-stat-grid">
        <StatCard label="Total Quotes" value={summary.total} />
        <StatCard label="Drafts" value={summary.drafts} variant="muted" />
        <StatCard label="Pending Approval" value={summary.pending} variant="warning" />
        <StatCard label="Sent" value={summary.sent} variant="info" />
        <StatCard label="Accepted" value={summary.accepted} variant="success" />
        {summary.expiringSoon > 0 && (
          <StatCard label="Expiring Soon" value={summary.expiringSoon} variant="warning" />
        )}
      </div>

      <div className="toolbar">
        <div className="toolbar__search">
          <SearchBar
            value={search}
            onChange={(v) => setSearch(v)}
            placeholder="Search quote number, title..."
            label="Search quotes"
          />
        </div>
        <div className="toolbar__filters">
          <FilterBar>
            <label className="sr-only" htmlFor="filter-quote-status">Status</label>
            <select
              id="filter-quote-status"
              value={filters.status}
              onChange={(e) => resetPage(() => setFilters((f) => ({ ...f, status: e.target.value })))}
            >
              <option value="">All statuses</option>
              <option value="DRAFT">Draft</option>
              <option value="PENDING_APPROVAL">Pending Approval</option>
              <option value="APPROVED">Approved</option>
              <option value="SENT">Sent</option>
              <option value="VIEWED">Viewed</option>
              <option value="ACCEPTED">Accepted</option>
              <option value="REJECTED">Rejected</option>
              <option value="EXPIRED">Expired</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
            <label className="sr-only" htmlFor="filter-quote-type">Quote type</label>
            <select
              id="filter-quote-type"
              value={filters.quote_type}
              onChange={(e) => resetPage(() => setFilters((f) => ({ ...f, quote_type: e.target.value })))}
            >
              <option value="">All types</option>
              <option value="PRODUCT">Product</option>
              <option value="SERVICE">Service</option>
              <option value="PROJECT">Project</option>
            </select>
          </FilterBar>
        </div>
      </div>

      {error ? (
        <ErrorState
          title={error.status === 403 ? 'Access denied' : 'Could not load quotes'}
          body={error.status === 403
            ? 'You don\'t have permission to view quotes. Ask an administrator to grant your role the "quotes.quote.read" permission.'
            : error.message}
          detail={error.status === 403 ? 'Required permission: quotes.quote.read' : undefined}
          onRetry={load}
        />
      ) : loading && data.results.length === 0 ? (
        <DataTable columns={columns} rows={[]} loading />
      ) : data.results.length === 0 ? (
        <div className="table-wrap">
          <EmptyState
            title={emptyTitle}
            body={emptyBody}
            action={debouncedSearch || filters.status || filters.quote_type
              ? <Button variant="secondary" onClick={() => { setSearch(''); setFilters({ status: '', quote_type: '' }); setPage(1); }}>Clear filters</Button>
              : createButton}
          />
        </div>
      ) : (
        <>
          <DataTable columns={columns} rows={data.results} keyField="quote_id" />
          <div className="mobile-quotes">
            {data.results.map((q) => <MobileQuoteCard key={q.quote_id} quote={q} />)}
          </div>
          <div className="table-wrap" style={{ marginTop: 16 }}>
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

export default QuoteListPage;
