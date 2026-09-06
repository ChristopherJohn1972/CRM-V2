import { formatDateTime } from '../../utils/format';
import { STATUS_VARIANT, CUSTOMER_STATUS, CUSTOMER_TYPES } from '../../utils/constants';
import StatusBadge from '../../components/StatusBadge';
import EmptyState from '../../components/EmptyState';

function StatTile({ label, value, tab, onNavigateTab }) {
  const inner = (
    <>
      <div className="stat-tile__label">{label}</div>
      <div className="stat-tile__value">{value ?? '—'}</div>
    </>
  );
  if (tab && onNavigateTab) {
    return (
      <button type="button" className="stat-tile" style={{ textAlign: 'left', cursor: 'pointer', font: 'inherit', color: 'inherit', background: 'inherit' }} onClick={() => onNavigateTab(tab)}>
        {inner}
      </button>
    );
  }
  return <div className="stat-tile">{inner}</div>;
}

export function OverviewTab({ data, core, onNavigateTab }) {
  const comms = data.summary?.communications || {};

  return (
    <div className="form" style={{ gap: 24 }}>
      <div className="grid-2">
        <section className="card">
          <div className="card__header"><h2 className="card__title">Customer summary</h2></div>
          <div className="card__body">
            <dl className="def-list" style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '12px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(120px, 160px) 1fr', gap: 8 }}>
                <dt>Account number</dt>
                <dd><code>{data.account_number}</code></dd>
                <dt>Type</dt>
                <dd>{CUSTOMER_TYPES[data.customer_type] || data.customer_type}</dd>
                <dt>Status</dt>
                <dd><StatusBadge status={data.status}>{CUSTOMER_STATUS[data.status] || data.status}</StatusBadge></dd>
                <dt>Created</dt>
                <dd>{formatDateTime(core?.created_at)}</dd>
              </div>
            </dl>
          </div>
        </section>

        <section className="card">
          <div className="card__header"><h2 className="card__title">Summary</h2></div>
          <div className="card__body">
            <div className="grid-2" style={{ gap: 12 }}>
              <StatTile label="Contacts" value={data.summary?.contacts} tab="contacts" onNavigateTab={onNavigateTab} />
              <StatTile label="Notifications" value={(comms.sms || 0) + (comms.email || 0)} tab="notifications" onNavigateTab={onNavigateTab} />
            </div>
            <div className="list-strip" style={{ marginTop: 16 }}>
              <div className="list-strip__item"><span>SMS</span><b>{comms.sms ?? 0}</b></div>
              <div className="list-strip__item"><span>Emails</span><b>{comms.email ?? 0}</b></div>
              <div className="list-strip__item"><span>Calls</span><b>{comms.call ?? 0}</b></div>
            </div>
          </div>
        </section>
      </div>

      {data.portal_access?.provisioned && (
        <section className="card">
          <div className="card__header"><h2 className="card__title">Portal Access</h2></div>
          <div className="card__body">
            <dl className="def-list" style={{ display: 'grid', gridTemplateColumns: 'minmax(120px, 160px) 1fr', gap: '12px' }}>
              <dt>Portal users</dt>
              <dd>{data.portal_access.portal_users?.length || 0}</dd>
              <dt>Account status</dt>
              <dd>{data.portal_access.account_status || 'Active'}</dd>
            </dl>
            <div style={{ marginTop: 12 }}>
              <button type="button" className="btn btn--ghost" onClick={() => onNavigateTab && onNavigateTab('portal')}>
                Manage portal access
              </button>
            </div>
          </div>
        </section>
      )}

      {data.recent_notes?.length > 0 && (
        <section className="card">
          <div className="card__header"><h2 className="card__title">Recent notes</h2></div>
          <div className="card__body">
            <div className="list-strip">
              {data.recent_notes.slice(0, 5).map((n) => (
                <div className="list-strip__item" key={n.note_id}>
                  <div>
                    <div style={{ fontWeight: 500 }}>{n.body?.substring(0, 100)}{n.body?.length > 100 ? '...' : ''}</div>
                    <div className="cell-secondary" style={{ fontSize: 12 }}>
                      {n.visibility} · {formatDateTime(n.created_at)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

export default OverviewTab;
