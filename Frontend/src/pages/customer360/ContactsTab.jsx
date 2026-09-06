import { useCallback, useEffect, useState } from 'react';
import { getContacts, createContact, updateContact, deactivateContact } from '../../api/customers';
import Button from '../../components/Button';
import Drawer from '../../components/Drawer';
import Field from '../../components/Field';
import StatusBadge from '../../components/StatusBadge';
import Avatar from '../../components/Avatar';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import SkeletonTable from '../../components/SkeletonTable';
import { PermissionGate } from '../../components/PermissionGate';
import { useToast } from '../../components/Toast';
import { PERMISSIONS } from '../../utils/constants';

const EMPTY = { first_name: '', last_name: '', job_title: '', email: '', phone: '', mobile: '', role_id: '', is_primary: false };

export function ContactsTab({ customerId }) {
  const { notify } = useToast();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [drawer, setDrawer] = useState(null); // null | {id, contact}
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getContacts(customerId));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    load();
  }, [load]);

  const openAdd = () => {
    setForm(EMPTY);
    setErrors({});
    setDrawer({ id: null, contact: null });
  };

  const openEdit = (contact) => {
    setForm({
      first_name: contact.first_name || '',
      last_name: contact.last_name || '',
      job_title: contact.job_title || '',
      email: contact.email || '',
      phone: contact.phone || '',
      mobile: contact.mobile || '',
      role_id: contact.role_id ? String(contact.role_id) : '',
      is_primary: Boolean(contact.is_primary),
    });
    setErrors({});
    setDrawer({ id: contact.contact_id, contact });
  };

  const set = (key) => (e) => {
    const value = key === 'is_primary' ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [key]: value }));
    setErrors((prev) => {
      if (!prev[key]) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const submit = async (e) => {
    e.preventDefault();
    const problems = {};
    if (!form.first_name.trim()) problems.first_name = 'First name is required.';
    if (!form.last_name.trim()) problems.last_name = 'Last name is required.';
    if (Object.keys(problems).length) { setErrors(problems); return; }

    const payload = {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      job_title: form.job_title.trim() || null,
      email: form.email.trim() || null,
      phone: form.phone.trim() || null,
      mobile: form.mobile.trim() || null,
      role_id: form.role_id ? Number(form.role_id) : null,
      is_primary: form.is_primary,
    };

    setSaving(true);
    try {
      if (drawer.id) {
        await updateContact(customerId, drawer.id, payload);
        notify('Contact updated', { variant: 'success' });
      } else {
        await createContact(customerId, payload);
        notify('Contact added', { variant: 'success' });
      }
      setDrawer(null);
      load();
    } catch (err) {
      setErrors(err.fieldErrors || {});
      notify('Could not save contact', { message: err.message, variant: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const confirmDeactivate = async (contact) => {
    if (!window.confirm(`Deactivate ${contact.first_name} ${contact.last_name}? This hides the contact from this customer.`)) return;
    try {
      await deactivateContact(customerId, contact.contact_id);
      notify('Contact deactivated', { variant: 'success' });
      load();
    } catch (err) {
      notify('Could not deactivate contact', { message: err.message, variant: 'error' });
    }
  };

  if (loading) return <SkeletonTable columns={5} rows={6} />;
  if (error) return <ErrorState title="Could not load contacts" body={error.message} onRetry={load} />;

  const primary = data.find((c) => c.is_primary);

  return (
    <div className="form" style={{ gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <PermissionGate permission={PERMISSIONS.CONTACT_CREATE}>
          <Button variant="primary" size="sm" onClick={openAdd}>Add contact</Button>
        </PermissionGate>
      </div>

      {data.length === 0 ? (
        <div className="table-wrap">
          <EmptyState title="No contacts yet" body="Add a contact such as the primary decision maker or a technical owner." />
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table data-table--desktop">
            <thead>
              <tr>
                <th>Contact</th>
                <th>Role</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((c) => (
                <tr key={c.contact_id}>
                  <td>
                    <div className="person-cell">
                      <Avatar name={`${c.first_name} ${c.last_name}`} />
                      <div className="person-cell__meta">
                        <div className="person-cell__name">{c.first_name} {c.last_name}{c.is_primary && ' ★'}</div>
                        <div className="person-cell__sub">{c.job_title || '—'}</div>
                      </div>
                    </div>
                  </td>
                  <td><span className="cell-secondary">{c.role_code || c.role_id || '—'}</span></td>
                  <td className="cell-nowrap">{c.email || '—'}</td>
                  <td className="cell-nowrap">{c.mobile || c.phone || '—'}</td>
                  <td>
                    {c.is_primary ? <StatusBadge variant="info">Primary</StatusBadge>
                      : <StatusBadge variant="muted">Contact</StatusBadge>}
                  </td>
                  <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                    <PermissionGate permission={PERMISSIONS.CONTACT_UPDATE}>
                      <Button variant="ghost" size="sm" onClick={() => openEdit(c)}>Edit</Button>
                    </PermissionGate>
                    <PermissionGate permission={PERMISSIONS.CONTACT_DELETE}>
                      <Button variant="ghost" size="sm" onClick={() => confirmDeactivate(c)} style={{ color: 'var(--color-danger)' }}>Deactivate</Button>
                    </PermissionGate>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="field__hint">Primary contact: {primary ? `${primary.first_name} ${primary.last_name}` : 'none set'}</p>

      <Drawer
        open={Boolean(drawer)}
        onClose={() => setDrawer(null)}
        title={drawer?.id ? 'Edit contact' : 'Add contact'}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDrawer(null)} disabled={saving}>Cancel</Button>
            <Button variant="primary" onClick={submit} loading={saving}>{drawer?.id ? 'Save changes' : 'Add contact'}</Button>
          </>
        }
      >
        <form className="form" onSubmit={(e) => { e.preventDefault(); submit(e); }} noValidate>
          <div className="form-grid">
            <Field label="First name" required htmlFor="ct-first" error={errors} errorKey="first_name">
              <input id="ct-first" className="field__input" value={form.first_name} onChange={set('first_name')} />
            </Field>
            <Field label="Last name" required htmlFor="ct-last" error={errors} errorKey="last_name">
              <input id="ct-last" className="field__input" value={form.last_name} onChange={set('last_name')} />
            </Field>
            <Field label="Job title" htmlFor="ct-title" className="field--span-2">
              <input id="ct-title" className="field__input" value={form.job_title} onChange={set('job_title')} />
            </Field>
            <Field label="Email" htmlFor="ct-email" error={errors} errorKey="email" className="field--span-2">
              <input id="ct-email" type="email" className="field__input" value={form.email} onChange={set('email')} />
            </Field>
            <Field label="Phone" htmlFor="ct-phone" error={errors} errorKey="phone">
              <input id="ct-phone" className="field__input" value={form.phone} onChange={set('phone')} />
            </Field>
            <Field label="Mobile" htmlFor="ct-mobile" error={errors} errorKey="mobile">
              <input id="ct-mobile" className="field__input" value={form.mobile} onChange={set('mobile')} />
            </Field>
            <Field label="Role ID" htmlFor="ct-role" hint="Contact role from the configured catalogue.">
              <input id="ct-role" type="number" min="1" className="field__input" value={form.role_id} onChange={set('role_id')} />
            </Field>
            <Field label="Primary contact" htmlFor="ct-primary">
              <select id="ct-primary" className="field__input" value={form.is_primary ? 'yes' : 'no'} onChange={(e) => setForm((f) => ({ ...f, is_primary: e.target.value === 'yes' }))}>
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </select>
            </Field>
          </div>
        </form>
      </Drawer>
    </div>
  );
}

export default ContactsTab;