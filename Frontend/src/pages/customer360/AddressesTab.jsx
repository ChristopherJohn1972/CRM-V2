import { useCallback, useEffect, useState } from 'react';
import { getAddresses, createAddress, updateAddress, deleteAddress } from '../../api/customers';
import Button from '../../components/Button';
import Drawer from '../../components/Drawer';
import Field from '../../components/Field';
import StatusBadge from '../../components/StatusBadge';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import SkeletonTable from '../../components/SkeletonTable';
import { PermissionGate } from '../../components/PermissionGate';
import { useToast } from '../../components/Toast';
import { buildAddressForm, buildAddressPayload } from '../../utils/customerForm';
import { ADDRESS_TYPES, PERMISSIONS } from '../../utils/constants';

export function AddressesTab({ customerId }) {
  const { notify } = useToast();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [drawer, setDrawer] = useState(null);
  const [form, setForm] = useState(buildAddressForm());
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getAddresses(customerId));
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
    setForm(buildAddressForm());
    setErrors({});
    setDrawer({ id: null });
  };

  const openEdit = (address) => {
    setForm(buildAddressForm(address));
    setErrors({});
    setDrawer({ id: address.address_id });
  };

  const set = (key) => (e) => {
    setForm((f) => ({ ...f, [key]: e.target.value }));
    setErrors((prev) => {
      if (!prev[key]) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!form.address.trim()) {
      setErrors({ address: 'Address is required.' });
      return;
    }
    const payload = buildAddressPayload(form);
    setSaving(true);
    try {
      if (drawer?.id) {
        await updateAddress(customerId, drawer.id, payload);
        notify('Address updated', { variant: 'success' });
      } else {
        await createAddress(customerId, payload);
        notify('Address added', { variant: 'success' });
      }
      setDrawer(null);
      load();
    } catch (err) {
      setErrors(err.fieldErrors || {});
      notify('Could not save address', { message: err.message, variant: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async (address) => {
    if (!window.confirm('Delete this address? This cannot be undone.')) return;
    try {
      await deleteAddress(customerId, address.address_id);
      notify('Address deleted', { variant: 'success' });
      load();
    } catch (err) {
      notify('Could not delete address', { message: err.message, variant: 'error' });
    }
  };

  if (loading) return <SkeletonTable columns={5} rows={5} />;
  if (error) return <ErrorState title="Could not load addresses" body={error.message} onRetry={load} />;

  return (
    <div className="form" style={{ gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <PermissionGate permission={PERMISSIONS.ADDRESS_WRITE}>
          <Button variant="primary" size="sm" onClick={openCreate}>Add address</Button>
        </PermissionGate>
      </div>

      {data.length === 0 ? (
        <div className="table-wrap">
          <EmptyState title="No addresses yet" body="Add a billing, shipping or office address for this customer." />
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table data-table--desktop">
            <thead>
              <tr>
                <th>Type</th>
                <th>Address</th>
                <th>City</th>
                <th>Country</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((a) => (
                <tr key={a.address_id}>
                  <td><span className="cell-secondary">{ADDRESS_TYPES[a.address_type] || a.address_type}</span></td>
                  <td>
                    <div>{a.address || '—'}</div>
                    <div className="cell-secondary" style={{ fontSize: 12 }}>{a.postal_code || ''}</div>
                  </td>
                  <td>{a.city || '—'}</td>
                  <td>{a.country || '—'}</td>
                  <td>{a.is_primary ? <StatusBadge variant="info">Primary</StatusBadge> : <StatusBadge variant="muted">Secondary</StatusBadge>}</td>
                  <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                    <PermissionGate permission={PERMISSIONS.ADDRESS_WRITE}>
                      <Button variant="ghost" size="sm" onClick={() => openEdit(a)}>Edit</Button>
                      <Button variant="ghost" size="sm" onClick={() => confirmDelete(a)} style={{ color: 'var(--color-danger)' }}>Delete</Button>
                    </PermissionGate>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Drawer
        open={Boolean(drawer)}
        onClose={() => setDrawer(null)}
        title={drawer?.id ? 'Edit address' : 'Add address'}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDrawer(null)} disabled={saving}>Cancel</Button>
            <Button variant="primary" onClick={submit} loading={saving}>{drawer?.id ? 'Save changes' : 'Add address'}</Button>
          </>
        }
      >
        <form className="form" onSubmit={(e) => { e.preventDefault(); submit(e); }} noValidate>
          <div className="form-grid">
            <Field label="Address type" htmlFor="ad-type">
              <select id="ad-type" className="field__input" value={form.address_type} onChange={set('address_type')}>
                {Object.entries(ADDRESS_TYPES).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
              </select>
            </Field>
            <Field label="Primary address" htmlFor="ad-primary">
              <select id="ad-primary" className="field__input" value={form.is_primary ? 'yes' : 'no'} onChange={(e) => setForm((f) => ({ ...f, is_primary: e.target.value === 'yes' }))}>
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </select>
            </Field>
            <Field label="Address" required htmlFor="ad-address" error={errors} errorKey="address" className="field--span-2">
              <textarea id="ad-address" className="field__input" rows={2} value={form.address} onChange={set('address')} />
            </Field>
            <Field label="City" htmlFor="ad-city">
              <input id="ad-city" className="field__input" value={form.city} onChange={set('city')} />
            </Field>
            <Field label="Postal code" htmlFor="ad-postal">
              <input id="ad-postal" className="field__input" value={form.postal_code} onChange={set('postal_code')} />
            </Field>
            <Field label="Country" htmlFor="ad-country">
              <input id="ad-country" className="field__input" value={form.country} onChange={set('country')} />
            </Field>
          </div>
        </form>
      </Drawer>
    </div>
  );
}

export default AddressesTab;