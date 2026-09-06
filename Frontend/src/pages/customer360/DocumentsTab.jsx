import { useCallback, useEffect, useState } from 'react';
import { getDocuments, uploadDocument, getDocumentDownloadUrl, getDocumentVersions } from '../../api/customers';
import Button from '../../components/Button';
import Drawer from '../../components/Drawer';
import Modal from '../../components/Modal';
import Field from '../../components/Field';
import StatusBadge from '../../components/StatusBadge';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import SkeletonTable from '../../components/SkeletonTable';
import { titleCase } from '../../utils/format';
import { PermissionGate } from '../../components/PermissionGate';
import { useToast } from '../../components/Toast';
import { formatDateTime, formatBytes } from '../../utils/format';
import { ACCESS_CLASSIFICATIONS, PERMISSIONS } from '../../utils/constants';

const EMPTY = { document_type: 'OTHER', access_classification: 'INTERNAL', expires_at: '', file: null };

function classificationVariant(cls) {
  if (cls === 'PUBLIC') return 'success';
  if (cls === 'CONFIDENTIAL') return 'danger';
  if (cls === 'RESTRICTED') return 'warning';
  return 'muted';
}

export function DocumentsTab({ customerId }) {
  const { notify } = useToast();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [uploadDrawer, setUploadDrawer] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [uploading, setUploading] = useState(false);

  const [versionsFor, setVersionsFor] = useState(null);
  const [versions, setVersions] = useState([]);
  const [versionsLoading, setVersionsLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getDocuments(customerId));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    load();
  }, [load]);

  const submitUpload = async () => {
    const problems = {};
    if (!form.document_type.trim()) problems.document_type = 'Document type is required.';
    if (!form.file) problems.file = 'Select a file to upload.';
    setErrors(problems);
    if (Object.keys(problems).length) return;

    const fd = new FormData();
    fd.append('file', form.file);
    fd.append('document_type', form.document_type.trim());
    fd.append('access_classification', form.access_classification);
    if (form.expires_at) fd.append('expires_at', new Date(form.expires_at).toISOString());

    setUploading(true);
    setErrors({});
    try {
      await uploadDocument(customerId, fd);
      notify('Document uploaded', { variant: 'success' });
      setUploadDrawer(false);
      load();
    } catch (err) {
      setErrors(err.fieldErrors || {});
      notify('Could not upload document', { message: err.message, variant: 'error' });
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (doc) => {
    try {
      const res = await getDocumentDownloadUrl(customerId, doc.document_id);
      const url = typeof res === 'string' ? res : res?.url;
      if (!url) throw new Error('No download link returned.');
      window.open(url, '_blank', 'noopener');
    } catch (err) {
      notify('Could not prepare download', { message: err.message, variant: 'error' });
    }
  };

  const openVersions = async (doc) => {
    setVersionsFor(doc);
    setVersions([]);
    setVersionsLoading(true);
    try {
      setVersions(await getDocumentVersions(customerId, doc.document_id));
    } catch (err) {
      notify('Could not load version history', { message: err.message, variant: 'error' });
    } finally {
      setVersionsLoading(false);
    }
  };

  if (loading) return <SkeletonTable columns={6} rows={5} />;
  if (error) return <ErrorState title="Could not load documents" body={error.message} onRetry={load} />;

  return (
    <div className="form" style={{ gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <PermissionGate permission={PERMISSIONS.DOCUMENT_UPLOAD}>
          <Button variant="primary" size="sm" onClick={() => { setForm(EMPTY); setErrors({}); setUploadDrawer(true); }}>Upload document</Button>
        </PermissionGate>
      </div>

      {data.length === 0 ? (
        <div className="table-wrap">
          <EmptyState title="No documents yet" body="Uploaded documents such as contracts and onboarding files will appear here." />
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table data-table--desktop">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Version</th>
                <th>Size</th>
                <th>Classification</th>
                <th>Uploaded</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.document_id}>
                  <td>
                    <div style={{ fontWeight: 500 }}>{d.current_file_name || `Document #${d.document_id}`}</div>
                    <div className="cell-secondary" style={{ fontSize: 12 }}>{d.current_mime_type || '—'}</div>
                  </td>
                  <td><span className="cell-secondary">{titleCase(d.document_type)}</span></td>
                  <td><span className="cell-monospace">v{d.current_version}</span></td>
                  <td className="cell-nowrap">{formatBytes(d.current_size_bytes)}</td>
                  <td><StatusBadge variant={classificationVariant(d.access_classification)} dot={false}>{ACCESS_CLASSIFICATIONS[d.access_classification] || d.access_classification}</StatusBadge></td>
                  <td className="cell-nowrap">{formatDateTime(d.created_at)}</td>
                  <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                    <PermissionGate permission={PERMISSIONS.DOCUMENT_DOWNLOAD}>
                      <Button variant="ghost" size="sm" onClick={() => handleDownload(d)}>Download</Button>
                    </PermissionGate>
                    <Button variant="ghost" size="sm" onClick={() => openVersions(d)}>Versions</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Drawer
        open={uploadDrawer}
        onClose={() => setUploadDrawer(false)}
        title="Upload document"
        footer={
          <>
            <Button variant="secondary" onClick={() => setUploadDrawer(false)} disabled={uploading}>Cancel</Button>
            <Button variant="primary" onClick={submitUpload} loading={uploading}>Upload</Button>
          </>
        }
      >
        <div className="form" style={{ gap: 16 }}>
          <Field label="File" required htmlFor="doc-file" error={errors} errorKey="file">
            <input
              id="doc-file"
              type="file"
              className="field__input"
              onChange={(e) => setForm((f) => ({ ...f, file: e.target.files?.[0] || null }))}
            />
          </Field>
          <Field label="Document type" required htmlFor="doc-type" error={errors} errorKey="document_type">
            <select id="doc-type" className="field__input" value={form.document_type} onChange={(e) => setForm((f) => ({ ...f, document_type: e.target.value }))}>
              <option value="CONTRACT">Contract</option>
              <option value="IDENTIFICATION">Identification</option>
              <option value="INVOICE">Invoice</option>
              <option value="STATEMENT">Statement</option>
              <option value="OTHER">Other</option>
            </select>
          </Field>
          <Field label="Classification" htmlFor="doc-class" hint="Additional permission checks apply to sensitive classifications.">
            <select id="doc-class" className="field__input" value={form.access_classification} onChange={(e) => setForm((f) => ({ ...f, access_classification: e.target.value }))}>
              {Object.entries(ACCESS_CLASSIFICATIONS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select>
          </Field>
          <Field label="Expiry (optional)" htmlFor="doc-exp">
            <input id="doc-exp" type="datetime-local" className="field__input" value={form.expires_at} onChange={(e) => setForm((f) => ({ ...f, expires_at: e.target.value }))} />
          </Field>
        </div>
      </Drawer>

      <Modal
        open={Boolean(versionsFor)}
        onClose={() => setVersionsFor(null)}
        title={`Version history — ${versionsFor?.current_file_name || ''}`}
        footer={
          <Button variant="secondary" onClick={() => setVersionsFor(null)}>Close</Button>
        }
      >
        <div className="form" style={{ gap: 12 }}>
          {versionsLoading ? (
            <div className="field__hint">Loading versions…</div>
          ) : versions.length === 0 ? (
            <p className="field__hint">No versions recorded.</p>
          ) : (
            <div className="list-strip">
              {versions.map((v) => (
                <div className="list-strip__item" key={v.document_version_id}>
                  <div>
                    <div style={{ fontWeight: 500 }}>v{v.version_num} {v.is_current ? '(current)' : ''}</div>
                    <div className="cell-secondary" style={{ fontSize: 12 }}>
                      {v.file_name} · {formatBytes(v.size_bytes)} · uploaded {formatDateTime(v.created_at)}
                    </div>
                  </div>
                  {v.scan_status && <StatusBadge variant={v.scan_status === 'PENDING' ? 'warning' : 'muted'} dot={false}>scan: {v.scan_status}</StatusBadge>}
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}

export default DocumentsTab;