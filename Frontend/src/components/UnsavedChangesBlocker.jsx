import { useEffect } from 'react';
import { useBlocker } from 'react-router-dom';
import Modal from './Modal';
import Button from './Button';

/**
 * Warns before leaving a page (in-app navigation or close/reload) while there
 * are unsaved edits. Confirmation keeps the user on the page; "Discard" leaves.
 */
export function UnsavedChangesBlocker({ when, onDiscard }) {
  const blocker = useBlocker(when);

  useEffect(() => {
    if (!when) return;
    const handler = (e) => {
      e.preventDefault();
      e.returnValue = true;
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [when]);

  const discard = () => {
    onDiscard?.();
    blocker.proceed?.();
  };

  const stay = () => blocker.reset?.();

  return (
    <Modal
      open={blocker.state === 'blocked'}
      onClose={stay}
      title="Unsaved changes"
      footer={(
        <>
          <Button variant="secondary" onClick={stay}>Keep editing</Button>
          <Button variant="danger" onClick={discard}>Discard changes</Button>
        </>
      )}
    >
      <p>You have unsaved changes. Leaving now will discard them.</p>
    </Modal>
  );
}

export default UnsavedChangesBlocker;