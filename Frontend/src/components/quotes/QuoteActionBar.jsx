import Button from '../../components/Button';
import { canSubmitForApproval, canApprove, canSend, canCancel } from '../../utils/quotes';

function QuoteActionBar({ status, onAction, canEdit }) {
  return (
    <div className="quote-action-bar">
      {canEdit && (
        <Button variant="ghost" size="sm" onClick={() => onAction('save')}>Save Draft</Button>
      )}

      {canEdit && (
        <Button variant="secondary" size="sm" onClick={() => onAction('submit-approval')}>
          Submit for Approval
        </Button>
      )}

      {canApprove(status) && (
        <>
          <Button variant="primary" size="sm" onClick={() => onAction('approve')}>Approve</Button>
          <Button variant="danger" size="sm" onClick={() => onAction('reject')}>Reject</Button>
        </>
      )}

      {canSend(status) && (
        <Button variant="primary" size="sm" onClick={() => onAction('send')}>Send Quote</Button>
      )}

      {canCancel(status) && (
        <Button variant="ghost" size="sm" onClick={() => onAction('cancel')}>Cancel</Button>
      )}

      <div className="quote-action-bar__more">
        <Button variant="ghost" size="sm" onClick={() => onAction('duplicate')}>Duplicate</Button>
      </div>
    </div>
  );
}

export default QuoteActionBar;
