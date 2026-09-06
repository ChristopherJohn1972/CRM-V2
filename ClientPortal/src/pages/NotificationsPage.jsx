import { useState, useEffect, useMemo } from 'react';
import { fetchNotifications, markNotificationRead, markAllNotificationsRead } from '../api/portal';
import { NOTIFICATION_TYPES } from '../utils/constants';
import PageHeader from '../components/PageHeader';
import Button from '../components/Button';
import { SkeletonTable } from '../components/Skeleton';
import { ErrorState, EmptyState } from '../components/States';
import { useToast } from '../components/Toast';

const CATEGORY_ICONS = {
  payment: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="1.5" y="3.5" width="13" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.5" /><path d="M1.5 6.5h13" stroke="currentColor" strokeWidth="1.5" /></svg>
  ),
  complaint: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 1.5l5.5 3v4c0 3.3-2.4 5.4-5.5 6.5-3.1-1.1-5.5-3.2-5.5-6.5v-4L8 1.5z" stroke="currentColor" strokeWidth="1.5" /></svg>
  ),
  document: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M9.5 1.5H4a1.5 1.5 0 00-1.5 1.5v10A1.5 1.5 0 004 14.5h8A1.5 1.5 0 0013.5 13V5.5L9.5 1.5z" stroke="currentColor" strokeWidth="1.5" /></svg>
  ),
  momentum: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 1.5l1.8 3.7 4 .6-2.9 2.8.7 4L8 10.6 4.4 12.6l.7-4L2.2 5.8l4-.6L8 1.5z" stroke="currentColor" strokeWidth="1.5" /></svg>
  ),
  security: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 1.5l5.5 2v4c0 3.5-2.5 5.5-5.5 6.5-3-1-5.5-3-5.5-6.5v-4L8 1.5z" stroke="currentColor" strokeWidth="1.5" /></svg>
  ),
  account: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5.5" r="3" stroke="currentColor" strokeWidth="1.5" /><path d="M2.5 14.5c0-3 2.5-5 5.5-5s5.5 2 5.5 5" stroke="currentColor" strokeWidth="1.5" /></svg>
  ),
};

export function NotificationsPage() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const toast = useToast();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchNotifications();
      setNotifications(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    if (filter === 'all') return notifications;
    if (filter === 'unread') return notifications.filter((n) => n.unread);
    return notifications.filter((n) => n.type === filter);
  }, [notifications, filter]);

  const unreadCount = notifications.filter((n) => n.unread).length;

  const handleMarkRead = async (id) => {
    try {
      await markNotificationRead(id);
      setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, unread: false } : n));
    } catch { /* ignore */ }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, unread: false })));
      toast.success('All notifications marked as read.');
    } catch { /* ignore */ }
  };

  return (
    <div>
      <PageHeader title="Notifications" subtitle={unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}>
        {unreadCount > 0 && (
          <Button variant="ghost" size="sm" onClick={handleMarkAllRead}>Mark all read</Button>
        )}
      </PageHeader>

      {/* Filter tabs */}
      <div className="tabs" style={{ marginBottom: 'var(--space-6)' }}>
        {[
          { key: 'all', label: 'All' },
          { key: 'unread', label: 'Unread' },
          { key: 'payment', label: 'Payments' },
          { key: 'complaint', label: 'Complaints' },
          { key: 'document', label: 'Documents' },
          { key: 'momentum', label: 'Momentum' },
          { key: 'security', label: 'Security' },
        ].map((f) => (
          <button key={f.key} className={`tab${filter === f.key ? ' is-active' : ''}`} onClick={() => setFilter(f.key)}>
            {f.label}
          </button>
        ))}
      </div>

      {loading && <SkeletonTable rows={5} cols={1} />}
      {error && <ErrorState detail={error} onRetry={load} />}
      {!loading && !error && filtered.length === 0 && (
        <EmptyState title="No notifications" body={filter === 'unread' ? "You're all caught up!" : 'Notifications will appear here.'} />
      )}
      {!loading && !error && filtered.length > 0 && (
        <div className="card">
          <div style={{ padding: 0 }}>
            {filtered.map((n) => (
              <div
                key={n.id}
                className={`notification-item${n.unread ? ' is-unread' : ''}`}
                onClick={() => n.unread && handleMarkRead(n.id)}
                style={{ cursor: n.unread ? 'pointer' : 'default' }}
              >
                <div className="notification-item__icon">
                  {CATEGORY_ICONS[n.type] || CATEGORY_ICONS.account}
                </div>
                <div className="notification-item__body">
                  <div className="notification-item__title">{n.title}</div>
                  <div className="notification-item__text">{n.text}</div>
                  <div className="notification-item__time">{n.time}</div>
                </div>
                {n.unread && (
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--color-primary)', flexShrink: 0 }} />
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default NotificationsPage;
