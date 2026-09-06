import { useCallback, useEffect, useState } from 'react';
import { getNotifications } from '../../api/customers';
import StatusBadge from '../../components/StatusBadge';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import SkeletonTable from '../../components/SkeletonTable';
import Pagination from '../../components/Pagination';
import { formatDateTime } from '../../utils/format';

const CHANNEL_LABELS = {
  sms: 'SMS',
  email: 'Email',
};

const STATUS_VARIANTS = {
  SENT: 'success',
  DELIVERED: 'success',
  FAILED: 'danger',
  QUEUED: 'warning',
  PENDING: 'warning',
  REJECTED: 'danger',
  UNKNOWN: 'neutral',
};

export function NotificationsTab({ customerId }) {
  const [items, setItems] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [channelFilter, setChannelFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const pageSize = 20;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getNotifications(customerId, {
        channel: channelFilter || undefined,
        status: statusFilter || undefined,
        page,
        page_size: pageSize,
      });
      setItems(res.results || []);
      setCount(res.count ?? 0);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [customerId, channelFilter, statusFilter, page]);

  useEffect(() => {
    load();
  }, [load]);

  const resetPage = (setter) => (value) => {
    setter(value);
    setPage(1);
  };

  if (loading && items.length === 0) return <SkeletonTable columns={6} rows={8} />;
  if (error) return <ErrorState title="Could not load notifications" body={error.message} onRetry={load} />;

  return (
    <div className="form" style={{ gap: 20 }}>
      <div className="filter-bar">
        <label className="sr-only" htmlFor="notif-channel">Channel</label>
        <select id="notif-channel" value={channelFilter} onChange={(e) => resetPage(setChannelFilter)(e.target.value)}>
          <option value="">All channels</option>
          <option value="sms">SMS</option>
          <option value="email">Email</option>
        </select>

        <label className="sr-only" htmlFor="notif-status">Status</label>
        <select id="notif-status" value={statusFilter} onChange={(e) => resetPage(setStatusFilter)(e.target.value)}>
          <option value="">All statuses</option>
          <option value="SENT">Sent</option>
          <option value="DELIVERED">Delivered</option>
          <option value="FAILED">Failed</option>
          <option value="QUEUED">Queued</option>
          <option value="PENDING">Pending</option>
        </select>

        <span className="field__hint">{count} notification{count === 1 ? '' : 's'}</span>
      </div>

      {items.length === 0 ? (
        <div className="table-wrap">
          <EmptyState
            title="No notifications"
            body="SMS and email send history for this customer will appear here."
          />
        </div>
      ) : (
        <>
          <div className="table-wrap">
            <table className="data-table data-table--desktop">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Channel</th>
                  <th>Recipient</th>
                  <th>Subject / Preview</th>
                  <th>Status</th>
                  <th>Provider Ref</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.notification_id}>
                    <td className="cell-nowrap">{formatDateTime(item.sent_at || item.created_at)}</td>
                    <td>
                      <span className="badge badge--neutral">{CHANNEL_LABELS[item.channel] || item.channel}</span>
                    </td>
                    <td className="cell-nowrap">{item.recipient || '—'}</td>
                    <td>
                      {item.subject ? (
                        <span style={{ fontWeight: 500 }}>{item.subject}</span>
                      ) : (
                        <span className="cell-secondary">{item.content_preview || '—'}</span>
                      )}
                    </td>
                    <td>
                      <StatusBadge
                        variant={STATUS_VARIANTS[item.delivery_status] || 'neutral'}
                        dot={false}
                      >
                        {item.delivery_status || '—'}
                      </StatusBadge>
                      {item.failure_reason && (
                        <div className="cell-secondary" style={{ fontSize: 12, marginTop: 2, color: 'var(--color-danger)' }}>
                          {item.failure_reason}
                        </div>
                      )}
                    </td>
                    <td className="cell-monospace cell-secondary cell-nowrap">{item.provider_reference || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {count > pageSize && (
            <Pagination
              page={page}
              pageSize={pageSize}
              count={count}
              onPageChange={setPage}
            />
          )}
        </>
      )}
    </div>
  );
}

export default NotificationsTab;
