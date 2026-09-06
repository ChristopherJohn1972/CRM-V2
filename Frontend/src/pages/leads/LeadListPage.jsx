import { useState, useEffect, useCallback, useRef } from 'react';
import { listLeads, deleteLead } from '../../api/leads';
import PageHeader from '../../components/PageHeader';
import SearchBar from '../../components/SearchBar';
import FilterBar from '../../components/FilterBar';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import SkeletonTable from '../../components/SkeletonTable';
import LeadPanel from '../../components/leads/LeadPanel';

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'NEW', label: 'New' },
  { value: 'CONTACTED', label: 'Contacted' },
  { value: 'QUALIFIED', label: 'Qualified' },
  { value: 'UNQUALIFIED', label: 'Unqualified' },
  { value: 'CONVERTED', label: 'Converted' },
  { value: 'LOST', label: 'Lost' },
  { value: 'DISQUALIFIED', label: 'Disqualified' },
];

const STATUS_LABELS = {
  NEW: 'New',
  CONTACTED: 'Contacted',
  QUALIFIED: 'Qualified',
  UNQUALIFIED: 'Unqualified',
  CONVERTED: 'Converted',
  LOST: 'Lost',
};

const STATUS_COLORS = {
  NEW: '#3b82f6',
  CONTACTED: '#8b5cf6',
  QUALIFIED: '#22c55e',
  UNQUALIFIED: '#94a3b8',
  CONVERTED: '#16a34a',
  LOST: '#ef4444',
};

export default function LeadListPage() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);

  const [panelOpen, setPanelOpen] = useState(false);
  const [panelMode, setPanelMode] = useState('create');
  const [selectedLeadId, setSelectedLeadId] = useState(null);
  const [openMenuId, setOpenMenuId] = useState(null);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const menuRef = useRef(null);

  useEffect(() => { loadLeads(); }, [page, statusFilter, search]);

  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpenMenuId(null);
      }
    }
    if (openMenuId) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [openMenuId]);

  function toggleMenu(leadId, buttonEl) {
    if (openMenuId === leadId) {
      setOpenMenuId(null);
      return;
    }
    const rect = buttonEl.getBoundingClientRect();
    const menuHeight = 130;
    const spaceBelow = window.innerHeight - rect.bottom;
    const openAbove = spaceBelow < menuHeight;
    const top = openAbove ? rect.top - menuHeight - 4 : rect.bottom + 4;
    const left = rect.left - 120;
    setMenuPos({ top, left: Math.max(8, left) });
    setOpenMenuId(leadId);
  }

  async function loadLeads() {
    setLoading(true);
    setError(null);
    try {
      const data = await listLeads({ search, status: statusFilter, page, page_size: 20 });
      setLeads(data.results || []);
      setCount(data.count || 0);
    } catch (err) {
      setError(err.message || 'Failed to load leads');
    } finally {
      setLoading(false);
    }
  }

  function handleNewLead() {
    setSelectedLeadId(null);
    setPanelMode('create');
    setPanelOpen(true);
  }

  function handleViewLead(leadId) {
    setSelectedLeadId(leadId);
    setPanelMode('view');
    setPanelOpen(true);
    setOpenMenuId(null);
  }

  function handleEditLead(leadId) {
    setSelectedLeadId(leadId);
    setPanelMode('edit');
    setPanelOpen(true);
    setOpenMenuId(null);
  }

  async function handleDeleteLead(leadId) {
    setOpenMenuId(null);
    if (!confirm('Delete this lead? This cannot be undone.')) return;
    try {
      await deleteLead(leadId);
      loadLeads();
    } catch (err) {
      alert(err.message || 'Failed to delete lead');
    }
  }

  function handleClosePanel() {
    setPanelOpen(false);
    setSelectedLeadId(null);
  }

  function handleLeadCreated() {
    loadLeads();
  }

  function handleLeadUpdated() {
    loadLeads();
  }

  function handleLeadDeleted() {
    loadLeads();
  }

  return (
    <div className="page">
      <PageHeader
        title="Leads"
        subtitle="Capture, qualify and manage prospects"
        actions={
          <button className="btn btn--primary" onClick={handleNewLead}>+ New Lead</button>
        }
      />

      <div className="toolbar">
        <div className="toolbar__search">
          <SearchBar
            value={search}
            onChange={(v) => { setSearch(v); setPage(1); }}
            placeholder="Search leads..."
            label="Search leads"
          />
        </div>
        <div className="toolbar__filters">
          <FilterBar>
            <label className="sr-only" htmlFor="filter-status">Status</label>
            <select
              id="filter-status"
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            >
              {STATUS_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </FilterBar>
        </div>
      </div>

      <div className="table-wrap">
        {loading ? (
          <SkeletonTable rows={5} cols={7} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadLeads} />
        ) : leads.length === 0 ? (
          <EmptyState
            title="No leads yet"
            description="Capture your first lead to start tracking prospects."
            action={
              <button className="btn btn--primary" onClick={handleNewLead}>+ New Lead</button>
            }
          />
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Company</th>
                <th>Status</th>
                <th>Score</th>
                <th style={{ width: 80 }}></th>
              </tr>
            </thead>
            <tbody>
              {leads.map(l => (
                <tr key={l.lead_id}>
                  <td>
                    <button className="lead-name-btn" onClick={() => handleViewLead(l.lead_id)}>
                      {[l.first_name, l.last_name].filter(Boolean).join(' ') || 'Unnamed'}
                    </button>
                  </td>
                  <td>{l.email || '—'}</td>
                  <td>{l.phone || '—'}</td>
                  <td>{l.company || '—'}</td>
                  <td>
                    <span className="lead-status-chip" style={{ color: STATUS_COLORS[l.status] || '#3b82f6' }}>
                      <span className="lead-status-chip__dot" style={{ background: STATUS_COLORS[l.status] || '#3b82f6' }} />
                      {STATUS_LABELS[l.status] || l.status}
                    </span>
                  </td>
                  <td>{l.qualification_score ?? '—'}</td>
                  <td>
                    <div className="lead-actions-cell">
                      <button
                        className="lead-menu-trigger"
                        onClick={(e) => { e.stopPropagation(); toggleMenu(l.lead_id, e.currentTarget); }}
                      >
                        ⋮
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {count > 20 && (
          <div className="pagination">
            <button className="btn btn--secondary btn--sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
              Previous
            </button>
            <span>Page {page} of {Math.ceil(count / 20)}</span>
            <button className="btn btn--secondary btn--sm" disabled={page >= Math.ceil(count / 20)} onClick={() => setPage(p => p + 1)}>
              Next
            </button>
          </div>
        )}
      </div>

      {openMenuId && (
        <div
          ref={menuRef}
          className="lead-menu lead-menu--fixed"
          style={{ top: menuPos.top, left: menuPos.left }}
          onClick={(e) => e.stopPropagation()}
        >
          <button className="lead-menu__item" onClick={() => { handleViewLead(openMenuId); setOpenMenuId(null); }}>View Lead</button>
          <button className="lead-menu__item" onClick={() => { handleEditLead(openMenuId); setOpenMenuId(null); }}>Edit Lead</button>
          <button className="lead-menu__item lead-menu__item--danger" onClick={() => { handleDeleteLead(openMenuId); setOpenMenuId(null); }}>Delete Lead</button>
        </div>
      )}

      {panelOpen && (
        <LeadPanel
          leadId={selectedLeadId}
          mode={panelMode}
          onClose={handleClosePanel}
          onCreated={handleLeadCreated}
          onUpdated={handleLeadUpdated}
          onDeleted={handleLeadDeleted}
        />
      )}
    </div>
  );
}
