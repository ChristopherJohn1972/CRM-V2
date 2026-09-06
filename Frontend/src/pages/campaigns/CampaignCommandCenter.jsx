import { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { listCampaigns, deleteCampaign } from '../../api/campaigns';
import { useAuth } from '../../auth/AuthContext';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import SkeletonTable from '../../components/SkeletonTable';
import { formatEnumLabel } from '../../utils/format';
import {
  CAMPAIGN_STATUS_LABELS,
  CAMPAIGN_TYPE_LABELS,
  PERMISSIONS,
} from '../../utils/constants';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  ...Object.entries(CAMPAIGN_STATUS_LABELS).map(([value, label]) => ({ value, label })),
];

export default function CampaignCommandCenter() {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [openMenuId, setOpenMenuId] = useState(null);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const menuRef = useRef(null);

  const canUpdate = hasPermission(PERMISSIONS.CAMPAIGN_UPDATE);
  const canDelete = hasPermission(PERMISSIONS.CAMPAIGN_DELETE);

  useEffect(() => { loadCampaigns(); }, [page, statusFilter, search]);

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

  async function loadCampaigns() {
    setLoading(true);
    setError(null);
    try {
      const data = await listCampaigns({ search, status: statusFilter, page, page_size: 20 });
      setCampaigns(data.results || []);
      setCount(data.count || 0);
    } catch (err) {
      setError(err.message || 'Failed to load campaigns');
    } finally {
      setLoading(false);
    }
  }

  function toggleMenu(campaignId, buttonEl) {
    if (openMenuId === campaignId) {
      setOpenMenuId(null);
      return;
    }
    const rect = buttonEl.getBoundingClientRect();
    const menuHeight = 120;
    const spaceBelow = window.innerHeight - rect.bottom;
    const openAbove = spaceBelow < menuHeight;
    const top = openAbove ? rect.top - menuHeight - 4 : rect.bottom + 4;
    const left = rect.left - 120;
    setMenuPos({ top, left: Math.max(8, left) });
    setOpenMenuId(campaignId);
  }

  function handleConfirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    deleteCampaign(deleteTarget.campaign_id)
      .then(() => {
        setDeleteTarget(null);
        setOpenMenuId(null);
        loadCampaigns();
      })
      .catch(err => {
        alert(err.message || 'Failed to delete campaign');
      })
      .finally(() => setDeleting(false));
  }

  const showActions = canUpdate || canDelete;

  return (
    <div className="page">
      <PageHeader
        title="Campaigns"
        subtitle="Create, launch, monitor and compare campaigns"
        actions={
          <Link to="/campaigns/new" className="btn btn--primary">
            + New Campaign
          </Link>
        }
      />

      <div className="campaign-list">
        <div className="toolbar">
          <div className="toolbar__search">
            <input
              type="text"
              className="field__input"
              placeholder="Search campaigns..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              style={{ maxWidth: 420, height: 38 }}
            />
          </div>
          <div className="toolbar__filters">
            <select
              className="field__input"
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              style={{ width: 235, height: 38 }}
            >
              {STATUS_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>

        {loading ? (
          <SkeletonTable rows={5} cols={5} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadCampaigns} />
        ) : campaigns.length === 0 ? (
          <EmptyState
            title="No campaigns yet"
            description="Create your first campaign to start tracking leads and conversions."
            action={
              <Link to="/campaigns/new" className="btn btn--primary">
                + New Campaign
              </Link>
            }
          />
        ) : (
          <div className="campaign-list__table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Campaign</th>
                  <th>Status</th>
                  <th>Type</th>
                  <th>Start Date</th>
                  <th>End Date</th>
                  {showActions && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {campaigns.map(c => (
                  <tr key={c.campaign_id}>
                    <td>
                      <Link to={`/campaigns/${c.campaign_id}`} className="accent-link">
                        {c.name}
                      </Link>
                    </td>
                    <td>
                      <StatusBadge status={c.status}>{CAMPAIGN_STATUS_LABELS[c.status] || formatEnumLabel(c.status)}</StatusBadge>
                    </td>
                    <td>{CAMPAIGN_TYPE_LABELS[c.campaign_type] || formatEnumLabel(c.campaign_type)}</td>
                    <td>{c.start_date || '--'}</td>
                    <td>{c.end_date || '--'}</td>
                    {showActions && (
                      <td>
                        <div className="lead-actions-cell">
                          <button
                            className="lead-menu-trigger"
                            onClick={(e) => { e.stopPropagation(); toggleMenu(c.campaign_id, e.currentTarget); }}
                          >
                            ⋮
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
          <button className="lead-menu__item" onClick={() => { navigate(`/campaigns/${openMenuId}`); setOpenMenuId(null); }}>
            View Campaign
          </button>
          {canUpdate && (
            <button className="lead-menu__item" onClick={() => { navigate(`/campaigns/${openMenuId}/edit`); setOpenMenuId(null); }}>
              Edit Campaign
            </button>
          )}
          {canDelete && (
            <button className="lead-menu__item lead-menu__item--danger" onClick={() => {
              const c = campaigns.find(x => x.campaign_id === openMenuId);
              setDeleteTarget(c);
              setOpenMenuId(null);
            }}>
              Delete Campaign
            </button>
          )}
        </div>
      )}

      {deleteTarget && (
        <div className="modal-overlay" onClick={() => setDeleteTarget(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="modal__title">Delete Campaign?</h3>
            </div>
            <div className="modal__body">
              <p>
                Are you sure you want to delete <strong>{deleteTarget.name}</strong>?
              </p>
              <p style={{ color: 'var(--color-text-secondary, #6B7280)', fontSize: 13, marginTop: 8 }}>
                This action cannot be undone.
              </p>
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => setDeleteTarget(null)} disabled={deleting}>
                Cancel
              </button>
              <button className="btn btn--danger" onClick={handleConfirmDelete} disabled={deleting}>
                {deleting ? 'Deleting...' : 'Delete Campaign'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
