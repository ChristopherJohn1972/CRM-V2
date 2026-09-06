import { useCallback, useEffect, useState } from 'react';
import { listTemplates, createTemplate, activateTemplate, deactivateTemplate } from '../../api/quotes';
import PageHeader from '../../components/PageHeader';
import Button from '../../components/Button';
import DataTable from '../../components/DataTable';
import StatusBadge from '../../components/StatusBadge';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import Modal from '../../components/Modal';
import Field from '../../components/Field';
import FormSection from '../../components/FormSection';
import { useToast } from '../../components/Toast';
import { formatDate } from '../../utils/format';
import { TEMPLATE_TYPE_LABELS } from '../../utils/constants';

function TemplatesPage() {
  const { notify } = useToast();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', template_type: 'DEFAULT' });
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listTemplates();
      setTemplates(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    setSubmitting(true);
    try {
      await createTemplate({
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        template_type: form.template_type,
      });
      notify('Template created', { variant: 'success' });
      setCreateOpen(false);
      setForm({ name: '', description: '', template_type: 'DEFAULT' });
      load();
    } catch (err) {
      notify('Failed to create template', { message: err.message, variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleStatus = async (template) => {
    try {
      if (template.status?.split('.').pop() === 'ACTIVE') {
        await deactivateTemplate(template.template_id);
        notify('Template deactivated', { variant: 'success' });
      } else {
        await activateTemplate(template.template_id);
        notify('Template activated', { variant: 'success' });
      }
      load();
    } catch (err) {
      notify('Action failed', { message: err.message, variant: 'error' });
    }
  };

  const columns = [
    { key: 'name', header: 'Name', render: (r) => <span style={{ fontWeight: 500 }}>{r.name}</span> },
    { key: 'template_type', header: 'Type', render: (r) => <span className="badge badge--neutral">{TEMPLATE_TYPE_LABELS[r.template_type] || r.template_type}</span> },
    { key: 'status', header: 'Status', render: (r) => {
      const isActive = r.status?.split('.').pop() === 'ACTIVE';
      return (
        <StatusBadge
          label={isActive ? 'Active' : 'Inactive'}
          variant={isActive ? 'success' : 'muted'}
        />
      );
    } },
    { key: 'current_version', header: 'Version', render: (r) => <span className="cell-secondary">v{r.current_version}</span> },
    { key: 'is_default', header: 'Default', render: (r) => r.is_default ? <span className="badge badge--info">Default</span> : '—' },
    { key: 'updated_at', header: 'Updated', render: (r) => <span className="cell-secondary cell-nowrap">{formatDate(r.updated_at)}</span> },
    { key: 'actions', header: '', render: (r) => (
      <Button variant="ghost" size="sm" onClick={() => handleToggleStatus(r)}>
        {r.status?.split('.').pop() === 'ACTIVE' ? 'Deactivate' : 'Activate'}
      </Button>
    ) },
  ];

  return (
    <div>
      <PageHeader
        title="Templates"
        subtitle="Manage reusable quote templates."
        actions={<Button variant="primary" onClick={() => setCreateOpen(true)}>Create Template</Button>}
      />

      {error ? (
        <ErrorState title="Could not load templates" body={error.message} onRetry={load} />
      ) : loading ? (
        <DataTable columns={columns} rows={[]} loading />
      ) : templates.length === 0 ? (
        <EmptyState
          title="No templates yet"
          body="Create your first quote template to standardize quotation formatting."
          action={<Button variant="primary" onClick={() => setCreateOpen(true)}>Create Template</Button>}
        />
      ) : (
        <DataTable columns={columns} rows={templates} keyField="template_id" />
      )}

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Create Template">
        <form className="form" onSubmit={handleCreate}>
          <Field label="Template Name" required htmlFor="tpl-name">
            <input id="tpl-name" className="field__input" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="e.g. Standard Service Quote" />
          </Field>
          <Field label="Description" htmlFor="tpl-desc">
            <textarea id="tpl-desc" className="field__input field__input--textarea" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} rows={2} placeholder="Optional description" />
          </Field>
          <Field label="Template Type" htmlFor="tpl-type">
            <select id="tpl-type" className="field__input" value={form.template_type} onChange={(e) => setForm((f) => ({ ...f, template_type: e.target.value }))}>
              <option value="DEFAULT">Default</option>
              <option value="PRODUCT">Product</option>
              <option value="SERVICE">Service</option>
              <option value="PROJECT">Project</option>
            </select>
          </Field>
          <div className="drawer__footer">
            <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button type="submit" variant="primary" loading={submitting}>Create</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

export default TemplatesPage;
