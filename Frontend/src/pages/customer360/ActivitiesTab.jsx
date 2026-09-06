import { useCallback, useEffect, useState } from 'react';
import { getActivities, createActivity, completeActivity, getNotes, createNote } from '../../api/customers';
import Button from '../../components/Button';
import Drawer from '../../components/Drawer';
import Field from '../../components/Field';
import StatusBadge from '../../components/StatusBadge';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import SkeletonTable from '../../components/SkeletonTable';
import { PermissionGate } from '../../components/PermissionGate';
import { titleCase } from '../../utils/format';
import { useToast } from '../../components/Toast';
import { formatDateTime } from '../../utils/format';
import { ACTIVITY_STATUS, NOTE_VISIBILITY, PERMISSIONS } from '../../utils/constants';

const EMPTY = { activity_type: 'FOLLOW_UP', subject: '', description: '', status: 'OPEN', priority: '', due_at: '', assigned_to: '' };
const NOTE_EMPTY = { body: '', visibility: 'TEAM' };

export function ActivitiesTab({ customerId }) {
  const { notify } = useToast();
  const [activities, setActivities] = useState([]);
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [activityDrawer, setActivityDrawer] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const [noteDrawer, setNoteDrawer] = useState(false);
  const [noteForm, setNoteForm] = useState(NOTE_EMPTY);
  const [noteSaving, setNoteSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [acts, notesData] = await Promise.all([
        getActivities(customerId, { page_size: 50 }),
        getNotes(customerId),
      ]);
      setActivities(acts.results || acts);
      setNotes(notesData.results || notesData);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    load();
  }, [load]);

  const submitActivity = async (e) => {
    e.preventDefault();
    if (!form.subject.trim()) { setErrors({ subject: 'Subject is required.' }); return; }
    setSaving(true);
    try {
      await createActivity(customerId, {
        activity_type: form.activity_type,
        subject: form.subject.trim(),
        description: form.description.trim() || '',
        status: 'OPEN',
        priority: form.priority || null,
        due_at: form.due_at || null,
        assigned_to: form.assigned_to ? Number(form.assigned_to) : null,
      });
      notify('Activity created', { variant: 'success' });
      setActivityDrawer(false);
      load();
    } catch (err) {
      setErrors(err.fieldErrors || {});
      notify('Could not create activity', { message: err.message, variant: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const markComplete = async (activity) => {
    try {
      await completeActivity(customerId, activity.activity_id);
      notify('Activity completed', { variant: 'success' });
      load();
    } catch (err) {
      notify('Could not complete activity', { message: err.message, variant: 'error' });
    }
  };

  const submitNote = async (e) => {
    e.preventDefault();
    if (!noteForm.body.trim()) { setErrors({ body: 'Note content is required.' }); return; }
    setNoteSaving(true);
    setErrors({});
    try {
      await createNote(customerId, {
        body: noteForm.body.trim(),
        visibility: noteForm.visibility,
      });
      notify('Internal note added', { variant: 'success' });
      setNoteDrawer(false);
      load();
    } catch (err) {
      setErrors(err.fieldErrors || {});
    } finally {
      setNoteSaving(false);
    }
  };

  if (loading) return <SkeletonTable columns={5} rows={6} />;
  if (error) return <ErrorState title="Could not load activities" body={error.message} onRetry={load} />;

  return (
    <div className="form" style={{ gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
        <PermissionGate permission={PERMISSIONS.NOTE_CREATE}>
          <Button variant="secondary" size="sm" onClick={() => { setNoteForm(NOTE_EMPTY); setErrors({}); setNoteDrawer(true); }}>Add note</Button>
        </PermissionGate>
        <PermissionGate permission={PERMISSIONS.ACTIVITY_CREATE}>
          <Button variant="primary" size="sm" onClick={() => { setForm({ ...EMPTY }); setErrors({}); setActivityDrawer(true); }}>Add activity</Button>
        </PermissionGate>
      </div>

      {activities.length === 0 ? (
        <div className="table-wrap">
          <EmptyState title="No activities yet" body="Activities such as follow-ups and tasks will appear here." />
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table data-table--desktop">
            <thead>
              <tr>
                <th>Subject</th>
                <th>Type</th>
                <th>Status</th>
                <th>Due</th>
                <th>Priority</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {activities.map((a) => (
                <tr key={a.activity_id}>
                  <td>
                    <div style={{ fontWeight: 500 }}>{a.subject}</div>
                    {a.description && <div className="cell-secondary" style={{ fontSize: 12 }}>{a.description}</div>}
                  </td>
                  <td><span className="cell-secondary">{titleCase(a.activity_type)}</span></td>
                   <td>
                    <StatusBadge
                      variant={a.status?.split('.').pop() === 'COMPLETED' ? 'success' : a.status?.split('.').pop() === 'CANCELLED' ? 'muted' : a.status?.split('.').pop() === 'IN_PROGRESS' ? 'info' : 'warning'}
                    >
                      {ACTIVITY_STATUS[a.status?.split('.').pop()] || a.status?.split('.').pop() || a.status || 'Open'}
                    </StatusBadge>
                  </td>
                  <td className="cell-nowrap">{a.due_at ? formatDateTime(a.due_at) : '—'}</td>
                  <td><span className="cell-secondary">{a.priority || '—'}</span></td>
                  <td style={{ textAlign: 'right' }}>
                    {a.status?.split('.').pop() !== 'COMPLETED' && (
                      <PermissionGate permission={PERMISSIONS.ACTIVITY_UPDATE}>
                        <Button variant="ghost" size="sm" onClick={() => markComplete(a)}>Complete</Button>
                      </PermissionGate>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <section className="card">
        <div className="card__header"><h2 className="card__title">Internal notes</h2></div>
        <div className="card__body">
          {notes.length === 0 ? (
            <p className="field__hint">No internal notes yet.</p>
          ) : (
            <div className="list-strip">
              {notes.map((n) => (
                <div className="list-strip__item" key={n.note_id}>
                  <div style={{ maxWidth: '75%' }}>
                    <div>{n.body}</div>
                    {n.author_name && <div className="cell-secondary" style={{ fontSize: 12, marginTop: 4 }}>{n.author_name} · {formatDateTime(n.created_at)}</div>}
                  </div>
                  <StatusBadge variant={n.visibility === 'PUBLIC' ? 'success' : n.visibility === 'TEAM' ? 'info' : 'muted'} dot={false}>
                    {NOTE_VISIBILITY[n.visibility] || n.visibility}
                  </StatusBadge>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <Drawer
        open={activityDrawer}
        onClose={() => setActivityDrawer(false)}
        title="Add activity"
        footer={
          <>
            <Button variant="secondary" onClick={() => setActivityDrawer(false)} disabled={saving}>Cancel</Button>
            <Button variant="primary" onClick={submitActivity} loading={saving}>Create activity</Button>
          </>
        }
      >
        <form className="form" onSubmit={(e) => { e.preventDefault(); submitActivity(e); }} noValidate>
          <Field label="Activity type" htmlFor="act-type">
            <select id="act-type" className="field__input" value={form.activity_type} onChange={(e) => setForm((f) => ({ ...f, activity_type: e.target.value }))}>
              <option value="FOLLOW_UP">Follow-up</option>
              <option value="CALL">Call</option>
              <option value="MEETING">Meeting</option>
              <option value="TASK">Task</option>
              <option value="EMAIL">Email</option>
            </select>
          </Field>
          <Field label="Subject" required htmlFor="act-subject" error={errors} errorKey="subject">
            <input id="act-subject" className="field__input" value={form.subject} onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))} />
          </Field>
          <Field label="Description" htmlFor="act-desc">
            <textarea id="act-desc" className="field__input" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
          </Field>
          <div className="form-grid">
            <Field label="Priority" htmlFor="act-priority">
              <select id="act-priority" className="field__input" value={form.priority} onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))}>
                <option value="">None</option>
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="URGENT">Urgent</option>
              </select>
            </Field>
            <Field label="Due date" htmlFor="act-due">
              <input id="act-due" type="datetime-local" className="field__input" value={form.due_at} onChange={(e) => setForm((f) => ({ ...f, due_at: e.target.value }))} />
            </Field>
            <Field label="Assigned user ID" htmlFor="act-assigned">
              <input id="act-assigned" type="number" min="1" className="field__input" value={form.assigned_to} onChange={(e) => setForm((f) => ({ ...f, assigned_to: e.target.value }))} />
            </Field>
          </div>
        </form>
      </Drawer>

      <Drawer
        open={noteDrawer}
        onClose={() => setNoteDrawer(false)}
        title="Add internal note"
        footer={
          <>
            <Button variant="secondary" onClick={() => setNoteDrawer(false)} disabled={noteSaving}>Cancel</Button>
            <Button variant="primary" onClick={submitNote} loading={noteSaving}>Add note</Button>
          </>
        }
      >
        <form className="form" onSubmit={(e) => { e.preventDefault(); submitNote(e); }} noValidate>
          <Field label="Visibility" htmlFor="note-vis" hint="Internal notes are not visible to external portal users.">
            <select id="note-vis" className="field__input" value={noteForm.visibility} onChange={(e) => setNoteForm((f) => ({ ...f, visibility: e.target.value }))}>
              <option value="TEAM">Team</option>
              <option value="PRIVATE">Private</option>
              <option value="PUBLIC">Public (internal)</option>
            </select>
          </Field>
          <Field label="Note" required htmlFor="note-body" error={errors} errorKey="body">
            <textarea id="note-body" className="field__input" value={noteForm.body} onChange={(e) => setNoteForm((f) => ({ ...f, body: e.target.value }))} />
          </Field>
        </form>
      </Drawer>
    </div>
  );
}

export default ActivitiesTab;