import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchComplaintDetail, replyToComplaint } from '../api/portal';
import { formatDate, formatDateTime } from '../utils/format';
import { COMPLAINT_STATUSES } from '../utils/constants';
import PageHeader from '../components/PageHeader';
import Button from '../components/Button';
import { SkeletonTable } from '../components/Skeleton';
import { ErrorState } from '../components/States';
import { useToast } from '../components/Toast';

export function ComplaintDetailPage() {
  const { complaintId } = useParams();
  const [complaint, setComplaint] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reply, setReply] = useState('');
  const [replying, setReplying] = useState(false);
  const toast = useToast();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchComplaintDetail(complaintId);
      setComplaint(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [complaintId]);

  const handleReply = async (e) => {
    e.preventDefault();
    if (!reply.trim()) return;
    setReplying(true);
    try {
      await replyToComplaint(complaintId, reply.trim());
      toast.success('Reply sent.');
      setReply('');
      load();
    } catch (err) {
      toast.error(err.message || 'Failed to send reply.');
    } finally {
      setReplying(false);
    }
  };

  if (loading) return <div><PageHeader title="Complaint Details" /><SkeletonTable rows={3} cols={2} /></div>;
  if (error) return <div><PageHeader title="Complaint Details" /><ErrorState detail={error} onRetry={load} /></div>;
  if (!complaint) return null;

  const currentStepIndex = COMPLAINT_STATUSES.indexOf(complaint.status);

  return (
    <div>
      <PageHeader title={complaint.subject} subtitle={complaint.id}>
        <Link to="/complaints" className="btn btn--ghost">Back to Complaints</Link>
      </PageHeader>

      {/* Status Tracker */}
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="card__body">
          <div className="complaint-tracker">
            {COMPLAINT_STATUSES.map((status, i) => (
              <div key={status} style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                <div className="complaint-step">
                  <div className={`complaint-step__dot${i < currentStepIndex ? ' complaint-step__dot--done' : i === currentStepIndex ? ' complaint-step__dot--active' : ''}`} />
                  <span className={`complaint-step__label${i < currentStepIndex ? ' complaint-step__label--done' : i === currentStepIndex ? ' complaint-step__label--active' : ''}`}>
                    {status}
                  </span>
                </div>
                {i < COMPLAINT_STATUSES.length - 1 && (
                  <div className={`complaint-step__connector${i < currentStepIndex ? ' complaint-step__connector--done' : ''}`} />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid-2">
        {/* Details */}
        <div className="card">
          <div className="card__header"><h2 className="card__title">Details</h2></div>
          <div className="card__body">
            <dl className="def-list">
              <dt>Reference</dt><dd className="cell-monospace">{complaint.id}</dd>
              <dt>Status</dt><dd><span className="badge badge--info">{complaint.status}</span></dd>
              <dt>Category</dt><dd>{complaint.category}</dd>
              <dt>Priority</dt><dd><span className={`badge badge--${complaint.priority === 'High' ? 'danger' : complaint.priority === 'Medium' ? 'warning' : 'muted'}`}>{complaint.priority}</span></dd>
              <dt>Created</dt><dd>{formatDateTime(complaint.created)}</dd>
              <dt>Preferred Contact</dt><dd>{complaint.preferred_contact}</dd>
            </dl>
            <div style={{ marginTop: 'var(--space-5)' }}>
              <strong style={{ fontSize: 'var(--text-sm)' }}>Description</strong>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', marginTop: 'var(--space-2)' }}>{complaint.description}</p>
            </div>
          </div>
        </div>

        {/* Timeline */}
        <div className="card">
          <div className="card__header"><h2 className="card__title">Timeline</h2></div>
          <div className="card__body">
            <div className="timeline">
              {complaint.timeline.map((t, i) => (
                <div key={i} className="timeline-item">
                  <div className={`timeline-item__dot${i === complaint.timeline.length - 1 ? '' : ''}`} />
                  <div className="timeline-item__content">
                    <div className="timeline-item__summary">{t.status}</div>
                    <div className="timeline-item__meta"><span>{formatDateTime(t.date)}</span></div>
                    {t.note && <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: 'var(--space-1)' }}>{t.note}</div>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="card" style={{ marginTop: 'var(--space-6)' }}>
        <div className="card__header"><h2 className="card__title">Messages</h2></div>
        <div className="card__body" style={{ padding: 0 }}>
          <div className="list-strip">
            {complaint.messages.map((m) => (
              <div key={m.id} className="list-strip__item" style={{ padding: 'var(--space-4) var(--space-5)' }}>
                <div>
                  <div style={{ fontWeight: 500, fontSize: 'var(--text-sm)' }}>{m.sender}</div>
                  <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', marginTop: 'var(--space-1)' }}>{m.text}</div>
                </div>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>{formatDateTime(m.date)}</span>
              </div>
            ))}
          </div>
        </div>
        {complaint.status !== 'Closed' && complaint.status !== 'Resolved' && (
          <div className="card__footer">
            <form onSubmit={handleReply} style={{ display: 'flex', gap: 'var(--space-3)' }}>
              <input
                className="field__input"
                placeholder="Type your reply..."
                value={reply}
                onChange={(e) => setReply(e.target.value)}
                style={{ flex: 1 }}
              />
              <Button type="submit" variant="primary" loading={replying} disabled={!reply.trim()}>Reply</Button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

export default ComplaintDetailPage;
