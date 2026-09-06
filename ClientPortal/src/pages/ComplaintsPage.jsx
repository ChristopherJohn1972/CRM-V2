import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { fetchComplaints, createComplaint } from '../api/portal';
import { formatDate } from '../utils/format';
import { COMPLAINT_CATEGORIES } from '../utils/constants';
import PageHeader from '../components/PageHeader';
import Button from '../components/Button';
import Field from '../components/Field';
import { SkeletonTable } from '../components/Skeleton';
import { ErrorState, EmptyState } from '../components/States';
import { useToast } from '../components/Toast';

export function ComplaintsPage() {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const toast = useToast();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchComplaints();
      setComplaints(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (formData) => {
    try {
      const result = await createComplaint(formData);
      toast.success(`Complaint ${result.id} submitted successfully.`);
      setShowForm(false);
      load();
    } catch (err) {
      toast.error(err.message || 'Failed to submit complaint.');
    }
  };

  const statusVariant = (s) => {
    if (s === 'Resolved' || s === 'Closed') return 'success';
    if (s === 'In Progress' || s === 'Assigned') return 'info';
    if (s === 'Submitted' || s === 'Under Review') return 'warning';
    return 'muted';
  };

  return (
    <div>
      <PageHeader title="Complaints" subtitle="Track and manage your service requests">
        <Button variant="primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : 'Raise Complaint'}
        </Button>
      </PageHeader>

      {showForm && <RaiseComplaintForm onSubmit={handleCreate} onCancel={() => setShowForm(false)} />}

      {loading && <SkeletonTable rows={3} cols={5} />}
      {error && <ErrorState detail={error} onRetry={load} />}
      {!loading && !error && complaints.length === 0 && (
        <EmptyState title="No complaints" body="You have not raised any complaints yet." />
      )}
      {!loading && !error && complaints.length > 0 && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Reference</th>
                <th>Subject</th>
                <th>Category</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Created</th>
                <th>Last Update</th>
              </tr>
            </thead>
            <tbody>
              {complaints.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link to={`/complaints/${c.id}`} className="data-table__accent cell-monospace">{c.id}</Link>
                  </td>
                  <td style={{ fontWeight: 500 }}>{c.subject}</td>
                  <td className="cell-secondary">{c.category}</td>
                  <td><span className={`badge badge--${statusVariant(c.status)}`}>{c.status}</span></td>
                  <td><span className={`badge badge--${c.priority === 'High' ? 'danger' : c.priority === 'Medium' ? 'warning' : 'muted'}`}>{c.priority}</span></td>
                  <td className="cell-nowrap">{formatDate(c.created)}</td>
                  <td className="cell-nowrap">{formatDate(c.last_update)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RaiseComplaintForm({ onSubmit, onCancel }) {
  const [subject, setSubject] = useState('');
  const [category, setCategory] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('Medium');
  const [preferredContact, setPreferredContact] = useState('Email');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!subject.trim() || !category || !description.trim()) return;
    setSubmitting(true);
    await onSubmit({ subject: subject.trim(), category, description: description.trim(), priority, preferred_contact: preferredContact });
    setSubmitting(false);
  };

  return (
    <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
      <div className="card__header"><h2 className="card__title">Raise a Complaint</h2></div>
      <div className="card__body">
        <form className="form" onSubmit={handleSubmit} noValidate>
          <div className="form-grid">
            <Field label="Subject" required htmlFor="cmp-subject">
              <input id="cmp-subject" className="field__input" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Brief description of the issue" />
            </Field>
            <Field label="Category" required htmlFor="cmp-category">
              <select id="cmp-category" className="field__input" value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="">Select category</option>
                {COMPLAINT_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
            <Field label="Priority" htmlFor="cmp-priority">
              <select id="cmp-priority" className="field__input" value={priority} onChange={(e) => setPriority(e.target.value)}>
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Urgent">Urgent</option>
              </select>
            </Field>
            <Field label="Preferred Contact" htmlFor="cmp-contact">
              <select id="cmp-contact" className="field__input" value={preferredContact} onChange={(e) => setPreferredContact(e.target.value)}>
                <option value="Email">Email</option>
                <option value="Phone">Phone</option>
              </select>
            </Field>
            <Field label="Description" required htmlFor="cmp-desc" className="field--span-2">
              <textarea id="cmp-desc" className="field__input" rows={4} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Provide details about your complaint..." />
            </Field>
          </div>
          <div className="form-actions">
            <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
            <Button type="submit" variant="primary" loading={submitting} disabled={!subject.trim() || !category || !description.trim()}>Submit Complaint</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ComplaintsPage;
