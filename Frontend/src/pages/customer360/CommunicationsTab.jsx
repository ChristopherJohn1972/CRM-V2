import { useCallback, useEffect, useState } from 'react';
import { getCommunications, sendSms, sendEmail } from '../../api/customers';
import Button from '../../components/Button';
import Drawer from '../../components/Drawer';
import Field from '../../components/Field';
import Tabs from '../../components/Tabs';
import StatusBadge from '../../components/StatusBadge';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import SkeletonTable from '../../components/SkeletonTable';
import { PermissionGate } from '../../components/PermissionGate';
import { useToast } from '../../components/Toast';
import { formatDateTime, truncate } from '../../utils/format';
import { COMMUNICATION_STATUS, PERMISSIONS } from '../../utils/constants';

const SMS_EMPTY = { to_number: '', body: '', from_number: '' };
const EMAIL_EMPTY = { to_address: '', subject: '', body: '', cc_address: '', bcc_address: '' };

function statusVariant(status) {
  if (!status) return 'muted';
  if (['SENT', 'DELIVERED'].includes(status)) return 'success';
  if (['FAILED', 'REJECTED'].includes(status)) return 'danger';
  return 'neutral';
}

export function CommunicationsTab({ customerId }) {
  const { notify } = useToast();
  const [mode, setMode] = useState('sms');
  const [combined, setCombined] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [sendDrawer, setSendDrawer] = useState(false);
  const [sendType, setSendType] = useState('sms');
  const [smsForm, setSmsForm] = useState(SMS_EMPTY);
  const [emailForm, setEmailForm] = useState(EMAIL_EMPTY);
  const [errors, setErrors] = useState({});
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setCombined(await getCommunications(customerId, { page_size: 50 }));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    load();
  }, [load]);

  const openSend = (type) => {
    setSendType(type);
    setErrors({});
    setSmsForm(SMS_EMPTY);
    setEmailForm(EMAIL_EMPTY);
    setSendDrawer(true);
  };

  const submitSms = async () => {
    const problems = {};
    if (!smsForm.to_number.trim()) problems.to_number = 'Recipient number is required.';
    if (!smsForm.body.trim()) problems.body = 'Message body is required.';
    setErrors(problems);
    if (Object.keys(problems).length) return;

    setSending(true);
    setErrors({});
    try {
      await sendSms(customerId, {
        to_number: smsForm.to_number.trim(),
        body: smsForm.body.trim(),
        from_number: smsForm.from_number.trim() || undefined,
      });
      notify('SMS queued for delivery', { variant: 'success' });
      setSendDrawer(false);
      load();
    } catch (err) {
      setErrors(err.fieldErrors || {});
      notify('Could not send SMS', { message: err.message, variant: 'error' });
    } finally {
      setSending(false);
    }
  };

  const submitEmail = async () => {
    const problems = {};
    if (!emailForm.to_address.trim()) problems.to_address = 'Recipient email is required.';
    setErrors(problems);
    if (Object.keys(problems).length) return;

    setSending(true);
    setErrors({});
    try {
      await sendEmail(customerId, {
        to_address: emailForm.to_address.trim(),
        subject: emailForm.subject.trim() || null,
        body: emailForm.body.trim() || null,
        cc_address: emailForm.cc_address.trim() || null,
        bcc_address: emailForm.bcc_address.trim() || null,
      });
      notify('Email sent', { variant: 'success' });
      setSendDrawer(false);
      load();
    } catch (err) {
      setErrors(err.fieldErrors || {});
      notify('Could not send email', { message: err.message, variant: 'error' });
    } finally {
      setSending(false);
    }
  };

  const submit = () => (sendType === 'sms' ? submitSms() : submitEmail());

  if (loading) return <SkeletonTable columns={5} rows={6} />;
  if (error) return <ErrorState title="Could not load communications" body={error.message} onRetry={load} />;

  const rows = combined.results || combined;

  return (
    <div className="form" style={{ gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
        <div className="muted-banner" style={{ padding: '8px 12px' }}>
          Showing communication history for this customer only.
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <PermissionGate permission={PERMISSIONS.SMS_SEND}>
            <Button variant="secondary" size="sm" onClick={() => openSend('sms')}>Send SMS</Button>
          </PermissionGate>
          <PermissionGate permission={PERMISSIONS.EMAIL_SEND}>
            <Button variant="primary" size="sm" onClick={() => openSend('email')}>Send email</Button>
          </PermissionGate>
        </div>
      </div>

      <Tabs
        tabs={[
          { key: 'combined', label: 'All' },
          { key: 'sms', label: 'SMS' },
          { key: 'email', label: 'Email' },
        ]}
        activeKey={mode}
        onChange={setMode}
      />

      {rows.length === 0 ? (
        <div className="table-wrap">
          <EmptyState title="No communications yet" body="SMS and email history will appear here once messages are sent or received." />
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table data-table--desktop">
            <thead>
              <tr>
                <th>Channel</th>
                <th>Date / time</th>
                <th>Direction</th>
                <th>Subject / preview</th>
                <th>Status</th>
                <th>Reference</th>
              </tr>
            </thead>
            <tbody>
              {rows
                .filter((c) => mode === 'combined' || c.channel === mode)
                .map((c) => (
                  <tr key={`${c.channel}-${c.id}`}>
                    <td><StatusBadge variant={c.channel === 'sms' ? 'info' : c.channel === 'email' ? 'success' : 'neutral'} dot={false}>{c.channel}</StatusBadge></td>
                    <td className="cell-nowrap">{formatDateTime(c.occurred_at)}</td>
                    <td><span className="cell-secondary">{c.summary ? (c.summary.startsWith('To') ? 'Outbound' : c.summary) : '—'}</span></td>
                    <td><span style={{ maxWidth: 320, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{truncate(c.summary, 60)}</span></td>
                    <td>
                      {c.status && <StatusBadge variant={statusVariant(c.status)}>{COMMUNICATION_STATUS[c.status] || c.status}</StatusBadge>}
                    </td>
                    <td className="cell-monospace cell-nowrap">{c.reference || '—'}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      <Drawer
        open={sendDrawer}
        onClose={() => setSendDrawer(false)}
        title={sendType === 'sms' ? 'Send SMS' : 'Send email'}
        footer={
          <>
            <Button variant="secondary" onClick={() => setSendDrawer(false)} disabled={sending}>Cancel</Button>
            <Button variant="primary" onClick={submit} loading={sending}>Send</Button>
          </>
        }
      >
        <form className="form" onSubmit={(e) => { e.preventDefault(); submit(); }} noValidate>
          {sendType === 'sms' ? (
            <div className="form-grid">
              <Field label="Recipient number" required htmlFor="snd-sms-to" error={errors} errorKey="to_number" className="field--span-2">
                <input id="snd-sms-to" className="field__input" value={smsForm.to_number} onChange={(e) => setSmsForm((f) => ({ ...f, to_number: e.target.value }))} />
              </Field>
              <Field label="From number" htmlFor="snd-sms-from" className="field--span-2">
                <input id="snd-sms-from" className="field__input" value={smsForm.from_number} onChange={(e) => setSmsForm((f) => ({ ...f, from_number: e.target.value }))} />
              </Field>
              <Field label="Message" required htmlFor="snd-sms-body" error={errors} errorKey="body" className="field--span-2">
                <textarea id="snd-sms-body" className="field__input" value={smsForm.body} onChange={(e) => setSmsForm((f) => ({ ...f, body: e.target.value }))} />
              </Field>
            </div>
          ) : (
            <div className="form-grid">
              <Field label="Recipient" required htmlFor="snd-email-to" error={errors} errorKey="to_address" className="field--span-2">
                <input id="snd-email-to" type="email" className="field__input" value={emailForm.to_address} onChange={(e) => setEmailForm((f) => ({ ...f, to_address: e.target.value }))} />
              </Field>
              <Field label="Subject" htmlFor="snd-email-subject" className="field--span-2">
                <input id="snd-email-subject" className="field__input" value={emailForm.subject} onChange={(e) => setEmailForm((f) => ({ ...f, subject: e.target.value }))} />
              </Field>
              <Field label="CC" htmlFor="snd-email-cc">
                <input id="snd-email-cc" className="field__input" value={emailForm.cc_address} onChange={(e) => setEmailForm((f) => ({ ...f, cc_address: e.target.value }))} />
              </Field>
              <Field label="BCC" htmlFor="snd-email-bcc">
                <input id="snd-email-bcc" className="field__input" value={emailForm.bcc_address} onChange={(e) => setEmailForm((f) => ({ ...f, bcc_address: e.target.value }))} />
              </Field>
              <Field label="Body" htmlFor="snd-email-body" className="field--span-2">
                <textarea id="snd-email-body" className="field__input" value={emailForm.body} onChange={(e) => setEmailForm((f) => ({ ...f, body: e.target.value }))} />
              </Field>
            </div>
          )}
        </form>
      </Drawer>
    </div>
  );
}

export default CommunicationsTab;