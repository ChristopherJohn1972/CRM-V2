import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { AddClientModal } from '../components/AddClientModal';

export function AddClientPage() {
  const navigate = useNavigate();
  const handleClose = useCallback(() => navigate('/clients'), [navigate]);
  return <AddClientModal open onClose={handleClose} />;
}

export default AddClientPage;