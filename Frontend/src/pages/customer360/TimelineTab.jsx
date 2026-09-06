import { useCallback, useEffect, useMemo, useState } from 'react';
import { getTimeline } from '../../api/customers';
import TimelineItem from '../../components/TimelineItem';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import SkeletonTable from '../../components/SkeletonTable';
import Button from '../../components/Button';
import { titleCase } from '../../utils/format';

export function TimelineTab({ customerId }) {
  const [rows, setRows] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [sourceFilter, setSourceFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTimeline(customerId, { page_size: 100 });
      setRows(data.results || []);
      setCount(data.count ?? data.results?.length ?? 0);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    load();
  }, [load]);

  const sources = useMemo(() => [...new Set(rows.map((r) => r.source_module).filter(Boolean))], [rows]);
  const categories = useMemo(() => [...new Set(rows.map((r) => r.event_type).filter(Boolean))], [rows]);

  const filtered = useMemo(
    () =>
      rows.filter(
        (r) =>
          (!sourceFilter || r.source_module === sourceFilter) &&
          (!categoryFilter || r.event_type === categoryFilter)
      ),
    [rows, sourceFilter, categoryFilter]
  );

  if (loading) return <SkeletonTable columns={3} rows={8} />;
  if (error) return <ErrorState title="Could not load the timeline" body={error.message} onRetry={load} />;

  return (
    <div className="form" style={{ gap: 20 }}>
      <div className="filter-bar">
        {sources.length > 1 && (
          <>
            <label className="sr-only" htmlFor="tl-source">Source</label>
            <select id="tl-source" value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
              <option value="">All sources</option>
              {sources.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
            </select>
          </>
        )}
        {categories.length > 1 && (
          <>
            <label className="sr-only" htmlFor="tl-cat">Category</label>
            <select id="tl-cat" value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
              <option value="">All categories</option>
              {categories.map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}
            </select>
          </>
        )}
        <span className="field__hint">{count} event{count === 1 ? '' : 's'} · business record</span>
      </div>

      {filtered.length === 0 ? (
        <div className="table-wrap">
          <EmptyState
            title="No timeline events"
            body="Events such as customer creation, assignment changes and contact updates will appear here."
          />
        </div>
      ) : (
        <section className="card">
          <div className="card__body">
            <div className="timeline">
              {filtered.map((t) => (
                <TimelineItem
                  key={t.event_id}
                  summary={t.summary || t.event_type}
                  occurredAt={t.occurred_at}
                  actorLabel={t.actor_label || t.actor_type}
                  sourceModule={t.source_module}
                />
              ))}
            </div>
            {count > filtered.length && (
              <div className="card__footer" style={{ padding: '12px 0 0' }}>
                <span className="field__hint">
                  Showing a subset of timeline events. The backend loads history progressively.
                </span>
              </div>
            )}
          </div>
        </section>
      )}

      <div>
        <Button variant="ghost" size="sm" onClick={load}>Refresh timeline</Button>
      </div>
    </div>
  );
}

export default TimelineTab;