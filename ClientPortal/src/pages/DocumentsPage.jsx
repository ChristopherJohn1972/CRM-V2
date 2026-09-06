import { useState, useEffect, useMemo } from 'react';
import { fetchDocuments } from '../api/portal';
import { formatDate } from '../utils/format';
import { DOCUMENT_CATEGORIES } from '../utils/constants';
import PageHeader from '../components/PageHeader';
import { SkeletonTable } from '../components/Skeleton';
import { ErrorState, EmptyState } from '../components/States';

export function DocumentsPage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [sort, setSort] = useState('newest');

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDocuments();
      setDocuments(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    let list = [...documents];
    if (search) {
      const q = search.toLowerCase();
      list = list.filter((d) => d.name.toLowerCase().includes(q) || d.category.toLowerCase().includes(q));
    }
    if (category) list = list.filter((d) => d.category === category);
    list.sort((a, b) => sort === 'newest' ? new Date(b.date) - new Date(a.date) : sort === 'oldest' ? new Date(a.date) - new Date(b.date) : a.name.localeCompare(b.name));
    return list;
  }, [documents, search, category, sort]);

  return (
    <div>
      <PageHeader title="Documents" subtitle="Access your invoices, receipts, statements, and other documents" />

      <div className="toolbar">
        <div className="toolbar__search">
          <div className="search-bar">
            <span className="search-bar__icon">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="6.5" cy="6.5" r="5" stroke="currentColor" strokeWidth="1.5" /><path d="M10.5 10.5L14.5 14.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
            </span>
            <input className="search-bar__input" placeholder="Search documents..." value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
        </div>
        <div className="toolbar__filters">
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All categories</option>
            {DOCUMENT_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="name">Name A-Z</option>
          </select>
        </div>
      </div>

      {loading && <SkeletonTable rows={5} cols={5} />}
      {error && <ErrorState detail={error} onRetry={load} />}
      {!loading && !error && filtered.length === 0 && (
        <EmptyState title="No documents found" body={search || category ? 'Try adjusting your search or filters.' : 'Documents will appear here once available.'} />
      )}
      {!loading && !error && filtered.length > 0 && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Category</th>
                <th>Date</th>
                <th>Type</th>
                <th>Size</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d) => (
                <tr key={d.id}>
                  <td style={{ fontWeight: 500 }}>{d.name}</td>
                  <td><span className="badge badge--plain">{d.category}</span></td>
                  <td className="cell-nowrap">{formatDate(d.date)}</td>
                  <td className="cell-secondary">{d.type}</td>
                  <td className="cell-secondary">{d.size}</td>
                  <td>
                    <button className="btn btn--ghost btn--sm" onClick={() => alert('Document download will be available when backend is connected.')}>
                      Download
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default DocumentsPage;
