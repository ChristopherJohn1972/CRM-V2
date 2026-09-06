import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { portalListQuotes } from '../../api/portal';
import StatusBadge from '../../components/StatusBadge';
import SearchBar from '../../components/SearchBar';
import FilterBar from '../../components/FilterBar';
import Pagination from '../../components/Pagination';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import { getQuoteStatusLabel, getQuoteStatusColor, getQuoteTypeLabel, getQuoteTypeColor, formatQuoteAmount, getExpiryWarning } from '../../utils/quotes';
import { formatDate } from '../../utils/format';
import { useDebouncedValue } from '../../utils/useDebouncedValue';

export function PortalQuotesPage() {
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search, 350);
  const [filters, setFilters] = useState({ status: '', quote_type: '' });
  const [data, setData] = useState({ count: 0, results: [] });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const abortRef = useRef(null);

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const res = await portalListQuotes({
        search: debouncedSearch || undefined,
        status: filters.status || undefined,
        quote_type: filters.quote_type || undefined,
        page,
        page_size: pageSize,
      });
      setData(res);
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
      render: (r) => (
        <Link className="data-table__accent" to={`/portal/quotes/${r.quote_id}`}>
          {r.quote_number}
        </Link>
      ),
    },
    {
      key: 'title',
      header: 'Title',
      render: (r) => <span style={{ fontWeight: 500 }}>{r.title || getQuoteTypeLabel(r.quote_type)}</span>,
    },
    {
      key: 'quote_type',
      header: 'Type',
      render: (r) => <span className="badge" style={{ background: getQuoteTypeColor(r.quote_type).bg, color: getQuoteTypeColor(r.quote_type).text }}>{getQuoteTypeLabel(r.quote_type)}</span>,
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
      render: (r) => <span style={{ fontWeight: 600 }}>{formatQuoteAmount(r.grand_total, r.currency)}</span>,
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
  ];

  const emptyTitle = debouncedSearch || filters.status || filters.quote_type
    ? 'No quotes match your search'
    : 'No quotes yet';
  const emptyBody = debouncedSearch || filters.status || filters.quote_type
    ? 'Try adjusting your search or filters.'
    : 'Your quotes will appear here once they are shared with you.';

  return (
    <div>
      <div className="page-header">
        <div className="page-header__content">
          <h1 className="page-header__title">My Quotes</h1>
          <p className="page-header__subtitle">View and manage your quotations.</p>
        </div>
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
              <option value="SENT">Sent</option>
              <option value="VIEWED">Viewed</option>
              <option value="ACCEPTED">Accepted</option>
              <option value="REJECTED">Rejected</option>
              <option value="EXPIRED">Expired</option>
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
        <ErrorState title="Could not load quotes" body={error.message} onRetry={load} />
      ) : loading && data.results.length === 0 ? (
        <div className="table-wrap"><table className="data-table"><tbody><tr><td colSpan={7} className="cell-secondary">Loading...</td></tr></tbody></table></div>
      ) : data.results.length === 0 ? (
        <EmptyState title={emptyTitle} body={emptyBody} />
      ) : (
        <>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  {columns.map((col) => (
                    <th key={col.key}>{col.header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.results.map((row) => (
                  <tr key={row.quote_id}>
                    {columns.map((col) => (
                      <td key={col.key}>
                        {col.render ? col.render(row) : row[col.key]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: 16 }}>
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

export default PortalQuotesPage;
