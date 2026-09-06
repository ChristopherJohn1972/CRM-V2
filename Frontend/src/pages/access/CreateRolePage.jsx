import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createRole } from '../../api/iam';
import PageHeader from '../../components/PageHeader';
import RoleForm from './RoleForm';
import UnsavedChangesBlocker from '../../components/UnsavedChangesBlocker';

export function CreateRolePage() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [banner, setBanner] = useState(null);

  const submit = async (payload) => {
    setBanner(null);
    setSubmitting(true);
    try {
      const role = await createRole(payload);
      setDirty(false);
      navigate(`/roles/${role.role_id}`, { state: { message: `Role "${role.name}" created.` } });
    } catch (err) {
      setBanner(err.message || 'Could not create the role.');
      setSubmitting(false);
    }
  };

  return (
    <div className="page">
      <PageHeader
        title="Create Role"
        subtitle="Define a reusable bundle of permissions and scope, then assign it to operators."
        breadcrumbs={[{ label: 'Roles', to: '/roles' }, { label: 'Create Role' }]}
      />
      {banner && <div className="form-error-banner" role="alert">{banner}</div>}
      <RoleForm
        submitLabel="Create Role"
        submitting={submitting}
        onSubmit={submit}
        onCancel={() => navigate('/roles')}
        onDirtyChange={setDirty}
      />
      <UnsavedChangesBlocker when={dirty} />
    </div>
  );
}

export default CreateRolePage;