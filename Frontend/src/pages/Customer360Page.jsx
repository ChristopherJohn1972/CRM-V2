import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { getCustomer360, getCustomer, changeStatus, deleteCustomer } from '../api/customers';
import PageHeader from '../components/PageHeader';
import StatusBadge from '../components/StatusBadge';
import StatusSelect from '../components/StatusSelect';
import Button from '../components/Button';
import Tabs from '../components/Tabs';
import Modal from '../components/Modal';
import Field from '../components/Field';
import ErrorState from '../components/ErrorState';
import SkeletonTable from '../components/SkeletonTable';
import { useToast } from '../components/Toast';
import { PermissionGate } from '../components/PermissionGate';
import { CUSTOMER_STATUS, CUSTOMER_TYPES, PERMISSIONS } from '../utils/constants';
import { customerDisplayName } from '../utils/customers';

import OverviewTab from './customer360/OverviewTab';
import ProfileTab from './customer360/ProfileTab';
import ContactsTab from './customer360/ContactsTab';
import AddressesTab from './customer360/AddressesTab';
import AccountingTab from './customer360/AccountingTab';
import PortalAccessTab from './customer360/PortalAccessTab';
import NotificationsTab from './customer360/NotificationsTab';

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'profile', label: 'Profile' },
  { key: 'contacts', label: 'Contacts' },
  { key: 'addresses', label: 'Addresses' },
  { key: 'portal', label: 'Portal Access' },
  { key: 'notifications', label: 'Notifications' },
  { key: 'accounting', label: 'Accounting' },
];

export function Customer360Page() {
  const { customerId } = useParams();
  const id = Number(customerId);
  const navigate = useNavigate();
  const { notify } = useToast();

  const [activeTab, setActiveTab] = useState('overview');
  const [data, setData] = useState(null);
  const [core, setCore] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [statusModal, setStatusModal] = useState(false);
  const [statusValue, setStatusValue] = useState('');
  const [statusReason, setStatusReason] = useState('');
  const [statusBusy, setStatusBusy] = useState(false);
  const [statusError, setStatusError] = useState(null);

  const [deleteModal, setDeleteModal] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [agg, detail] = await Promise.all([
        getCustomer360(id),
        getCustomer(id).catch(() => null),
      ]);
      setData(agg);
      setCore(detail);
    } catch (err) {
      setLoadError(err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const submitStatus = async () => {
    setStatusBusy(true);
    setStatusError(null);
    try {
      await changeStatus(id, statusValue, statusReason);
      notify('Status updated', {
        message: `Customer moved to ${CUSTOMER_STATUS[statusValue] || statusValue}.`,
        variant: 'success',
      });
      setStatusModal(false);
      load();
    } catch (err) {
      setStatusError(err.message);
    } finally {
      setStatusBusy(false);
    }
  };

  const handleDelete = async () => {
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await deleteCustomer(id);
      notify('Customer deleted', {
        message: `${data?.account_number || 'Customer'} has been permanently deleted.`,
        variant: 'success',
      });
      navigate('/clients');
    } catch (err) {
      setDeleteError(err.message || 'Could not delete the customer.');
    } finally {
      setDeleteBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="page">
        <SkeletonTable columns={3} rows={8} />
      </div>
    );
  }

  if (loadError || !data) {
    return (
      <div className="page">
        <ErrorState
          title="Could not open this customer"
          body={loadError?.message || 'The customer record could not be loaded.'}
          onRetry={load}
        />
      </div>
    );
  }

  const tabProps = { customerId: id, core, data, reloadCore: load, onNavigateTab: setActiveTab };
  const Panels = {
    overview: <OverviewTab {...tabProps} />,
    profile: <ProfileTab {...tabProps} />,
    contacts: <ContactsTab {...tabProps} />,
    addresses: <AddressesTab {...tabProps} />,
    portal: <PortalAccessTab {...tabProps} />,
    notifications: <NotificationsTab {...tabProps} />,
    accounting: <AccountingTab {...tabProps} />,
  };

  const panel = Panels[activeTab] || Panels.overview;
  const canEdit = data.permissions?.can_edit;
  const canDelete = data.permissions?.can_delete;

  return (
    <div className="page">
      <PageHeader
        breadcrumbs={[{ label: 'Clients', to: '/clients' }, { label: `Customer ${data.account_number}` }]}
      />

      <div className="c360-header">
        <div className="c360-header__identity">
          <h1>
            {customerDisplayName(core) !== '—' ? customerDisplayName(core) : (data.display_name || 'Unnamed customer')}
            <StatusBadge status={data.status}>{CUSTOMER_STATUS[data.status] || data.status}</StatusBadge>
          </h1>
          <div className="c360-header__meta">
            <span className="c360-header__account" title="Account number">{data.account_number}</span>
            <span>{CUSTOMER_TYPES[data.customer_type] || data.customer_type}</span>
          </div>
        </div>
        <div className="c360-header__actions">
          {canEdit && (
            <Link to={`/customers/${id}/edit`} className="btn btn--secondary" title="Edit customer">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ marginRight: 6, verticalAlign: 'middle' }}>
                <path d="M11.5 1.5L14.5 4.5L5 14H2V11L11.5 1.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Edit
            </Link>
          )}
          {canDelete && (
            <Button variant="danger" onClick={() => { setDeleteError(null); setDeleteModal(true); }} title="Delete customer permanently">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ marginRight: 6, verticalAlign: 'middle' }}>
                <path d="M2 4H14M5.33333 4V2.66667C5.33333 2 5.86667 1.33333 6.66667 1.33333H9.33333C10.1333 1.33333 10.6667 2 10.6667 2.66667V4M12.6667 4V13.3333C12.6667 14 12 14.6667 11.3333 14.6667H4.66667C4 14.6667 3.33333 14 3.33333 13.3333V4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Delete
            </Button>
          )}
          {data.permissions?.can_change_status && (
            <Button variant="ghost" onClick={() => { setStatusValue(data.status); setStatusReason(''); setStatusError(null); setStatusModal(true); }}>
              Change status ▾
            </Button>
          )}
        </div>
      </div>

      <div className="c360-content">
        <div className="c360-content__tabs">
          <Tabs
            tabs={TABS.map((t) => ({
              ...t,
              count: t.key === 'contacts' ? data.summary?.contacts : undefined,
            }))}
            activeKey={activeTab}
            onChange={setActiveTab}
          />
        </div>
        <div className="c360-content__panel" id={`panel-${activeTab}`} role="tabpanel">
          {panel}
        </div>
      </div>

      <Modal
        open={statusModal}
        onClose={() => setStatusModal(false)}
        title="Change customer status"
        footer={
          <>
            <Button variant="secondary" onClick={() => setStatusModal(false)} disabled={statusBusy}>Cancel</Button>
            <Button variant="primary" onClick={submitStatus} loading={statusBusy} disabled={!statusValue}>Save status</Button>
          </>
        }
      >
        <div className="form" style={{ gap: 16 }}>
          {statusError && <div className="form-error-banner" role="alert">{statusError}</div>}
          <Field label="New status" required htmlFor="st-change-status">
            <StatusSelect id="st-change-status" value={statusValue} onChange={(e) => setStatusValue(e.target.value)} placeholder="Select a status" />
          </Field>
          <Field label="Reason (optional)" htmlFor="st-change-reason">
            <textarea id="st-change-reason" className="field__input" value={statusReason} onChange={(e) => setStatusReason(e.target.value)} />
          </Field>
        </div>
      </Modal>

      <Modal
        open={deleteModal}
        onClose={() => setDeleteModal(false)}
        title="Delete Customer?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteModal(false)} disabled={deleteBusy}>Cancel</Button>
            <Button variant="danger" onClick={handleDelete} loading={deleteBusy}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ marginRight: 6, verticalAlign: 'middle' }}>
                <path d="M2 4H14M5.33333 4V2.66667C5.33333 2 5.86667 1.33333 6.66667 1.33333H9.33333C10.1333 1.33333 10.6667 2 10.6667 2.66667V4M12.6667 4V13.3333C12.6667 14 12 14.6667 11.3333 14.6667H4.66667C4 14.6667 3.33333 14 3.33333 13.3333V4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Delete Permanently
            </Button>
          </>
        }
      >
        <div className="form" style={{ gap: 16 }}>
          {deleteError && <div className="form-error-banner" role="alert">{deleteError}</div>}
          <p style={{ margin: 0, lineHeight: 1.6 }}>
            This will permanently delete this customer account and its associated data.
            This action cannot be undone.
          </p>
          <dl className="def-list" style={{ margin: '8px 0 0' }}>
            <dt>Account number</dt>
            <dd><code>{data.account_number}</code></dd>
            <dt>Customer</dt>
            <dd>{customerDisplayName(core) || data.display_name}</dd>
          </dl>
        </div>
      </Modal>
    </div>
  );
}

export default Customer360Page;