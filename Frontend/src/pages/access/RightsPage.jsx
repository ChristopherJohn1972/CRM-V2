import { useCallback, useEffect, useMemo, useState } from 'react';
import { getRightsCatalogue } from '../../api/iam';
import PageHeader from '../../components/PageHeader';
import SearchBar from '../../components/SearchBar';
import ErrorState from '../../components/ErrorState';
import { groupByResource } from '../../utils/iam';

export function RightsPage() {
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [collapsed, setCollapsed] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getRightsCatalogue();
      setPermissions(res.permissions || []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const grouped = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = q
      ? permissions.filter((p) =>
          [p.code, p.name, p.resource, p.action, p.description]
            .filter(Boolean)
            .join(' ')
            .toLowerCase()
            .includes(q),
        )
      : permissions;
    return groupByResource(filtered);
  }, [permissions, search]);

  const toggleGroup = (resource) => {
    setCollapsed((prev) => ({ ...prev, [resource]: !prev[resource] }));
  };

  if (error) {
    return <ErrorState title="Could not load the rights catalogue" body={error.message} onRetry={load} />;
  }

  return (
    <div>
      <PageHeader
        title="Rights"
        subtitle="The catalogue of permissions. Rights are bundled into roles; use the search to find what a capability enables."
      />

      <div className="toolbar">
        <div className="toolbar__search">
          <SearchBar value={search} onChange={setSearch} placeholder="Search rights by resource, action or name…" label="Search rights" />
        </div>
      </div>

      {loading && permissions.length === 0 ? (
        <p className="cell-secondary">Loading rights…</p>
      ) : Object.keys(grouped).length === 0 ? (
        <p className="cell-secondary">No rights match your search.</p>
      ) : (
        <div className="rights-catalogue">
          {Object.entries(grouped).map(([resource, items]) => {
            const isCollapsed = collapsed[resource];
            return (
              <section key={resource} className="card">
                <button type="button" className="rights-catalogue__toggle" aria-expanded={!isCollapsed} onClick={() => toggleGroup(resource)}>
                  <span className={`rights-catalogue__chevron${isCollapsed ? ' is-collapsed' : ''}`} aria-hidden="true">⌄</span>
                  <h3 className="card__title">{resource}</h3>
                  <span className="badge badge--neutral badge--small">{items.length} rights</span>
                </button>
                {!isCollapsed && (
                  <div className="card__body" style={{ padding: 0 }}>
                    <table className="data-table data-table--desktop">
                      <tbody>
                        {items.map((p) => (
                          <tr key={p.permission_id}>
                            <td style={{ width: '40%' }}>
                              <div style={{ fontWeight: 500 }}>{p.name}</div>
                            </td>
                            <td>
                              <code>{p.code}</code>
                            </td>
                            <td>
                              <span className="cell-secondary">{p.description || '—'}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default RightsPage;
