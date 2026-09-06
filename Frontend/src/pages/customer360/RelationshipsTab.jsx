import { useCallback, useEffect, useState } from 'react';
import { getRelationships, createRelationship, removeRelationship, getCustomer } from '../../api/customers';
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
import { PERMISSIONS } from '../../utils/constants';

export function RelationshipsTab({ customerId }) {
  const { notify } = useToast();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [drawer, setDrawer] = useState(false);
  const [form, setForm] = useState({ related_customer_id: '', relationship_type: '', description: '' });
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getRelationships(customerId));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setForm({ related_customer_id: '', relationship_type: '', description: '' });
    setErrors({});
    setDrawer(true);
  };

  const submit = async (e) => {
    e.preventDefault();
    const problems = {};
    if (!form.relationship_type.trim()) problems.relationship_type = 'Relationship type is required.';
    if (!form.related_customer_id) problems.related_customer_id = 'Related customer is required.';
    if (Object.keys(problems).length) { setErrors(problems); return; }

    setSaving(true);
    try {
      await createRelationship(customerId, {
        related_customer_id: Number(form.related_customer_id),
        relationship_type: form.relationship_type.trim(),
        description: form.description.trim() || null,
      });
      notify('Relationship added', { variant: 'success' });
      setDrawer(false);
      load();
    } catch (err) {
      setErrors(err.fieldErrors || {});
      notify('Could not add relationship', { message: err.message, variant: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const confirmRemove = async (rel) => {
    if (!window.confirm('Remove this relationship?')) return;
    try {
      await removeRelationship(customerId, rel.relationship_id);
      notify('Relationship removed', { variant: 'success' });
      load();
    } catch (err) {
      notify('Could not remove relationship', { message: err.message, variant: 'error' });
    }
  };

  const openRelated = async (id) => {
    try {
      const related = await getCustomer(id);
      window.open(`/customers/${related.customer_id}`, '_blank');
    } catch {
      notify('Related customer is not accessible with your permissions.', { variant: 'warning' });
    }
  };

  if (loading) return <SkeletonTable columns={4} rows={5} />;
  if (error) return <ErrorState title="Could not load relationships" body={error.message} onRetry={load} />;

  return (
    <div className="form" style={{ gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <PermissionGate permission={PERMISSIONS.RELATIONSHIP_CREATE}>
          <Button variant="primary" size="sm" onClick={openCreate}>Add relationship</Button>
        </PermissionGate>
      </div>

      {data.length === 0 ? (
        <div className="table-wrap">
          <EmptyState title="No relationships yet" body="Link this customer to another customer record, such as a parent company or partner." />
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table data-table--desktop">
            <thead>
              <tr>
                <th>Related customer</th>
                <th>Relationship type</th>
                <th>Description</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((r) => (
                <tr key={r.relationship_id}>
                  <td>
                    <div className="person-cell">
                      <div className="person-cell__meta">
                        <div className="person-cell__name">
                          <button type="button" className="data-table__accent" onClick={() => openRelated(r.related_customer_id)}>
                            {r.related_display_name || `Customer #${r.related_customer_id}`}
                          </button>
                        </div>
                        <div className="person-cell__sub cell-monospace">{r.related_account_number || ''}</div>
                      </div>
                    </div>
                  </td>
                  <td><StatusBadge variant="info" dot={false}>{titleCase(r.relationship_type)}</StatusBadge></td>
                  <td><span className="cell-secondary">{r.description || '—'}</span></td>
                  <td style={{ textAlign: 'right' }}>
                    <PermissionGate permission={PERMISSIONS.RELATIONSHIP_DELETE}>
                      <Button variant="ghost" size="sm" onClick={() => confirmRemove(r)} style={{ color: 'var(--color-danger)' }}>Remove</Button>
                    </PermissionGate>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Drawer
        open={drawer}
        onClose={() => setDrawer(false)}
        title="Add relationship"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDrawer(false)} disabled={saving}>Cancel</Button>
            <Button variant="primary" onClick={submit} loading={saving}>Add relationship</Button>
          </>
        }
      >
        <form className="form" onSubmit={(e) => { e.preventDefault(); submit(e); }} noValidate>
          <Field label="Related customer ID" required htmlFor="rel-cid" hint="The customer account this record is related to." error={errors} errorKey="related_customer_id">
            <input id="rel-cid" type="number" min="1" className="field__input" value={form.related_customer_id} onChange={(e) => setForm((f) => ({ ...f, related_customer_id: e.target.value }))} />
          </Field>
          <Field label="Relationship type" required htmlFor="rel-type" hint="Configured relationship codes, e.g. PARENT_COMPANY, AFFILIATE, SUPPLIER." error={errors} errorKey="relationship_type">
            <input id="rel-type" className="field__input" value={form.relationship_type} onChange={(e) => setForm((f) => ({ ...f, relationship_type: e.target.value }))} />
          </Field>
          <Field label="Description" htmlFor="rel-desc" className="field--span-2">
            <textarea id="rel-desc" className="field__input" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
          </Field>
        </form>
      </Drawer>
    </div>
  );
}

export default RelationshipsTab;