import Button from '../Button';
import {
  canEditOrder, canSubmitForApproval, canApproveOrder,
  canConfirmOrder, canCancelOrder, canProcessOrder, canFulfillOrder, canOnHoldOrder,
} from '../../utils/salesOrders';

export function SalesOrderActionBar({ status, onAction, canEdit }) {
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      {canSubmitForApproval(status) && (
        <Button variant="primary" size="sm" onClick={() => onAction('submit_approval')}>
          Submit for Approval
        </Button>
      )}
      {canApproveOrder(status) && (
        <Button variant="primary" size="sm" onClick={() => onAction('approve')}>
          Approve
        </Button>
      )}
      {canConfirmOrder(status) && (
        <Button variant="primary" size="sm" onClick={() => onAction('confirm')}>
          Confirm Order
        </Button>
      )}
      {canProcessOrder(status) && (
        <Button variant="primary" size="sm" onClick={() => onAction('processing')}>
          Mark Processing
        </Button>
      )}
      {canOnHoldOrder(status) && (
        <Button variant="ghost" size="sm" onClick={() => onAction('on_hold')}>
          On Hold
        </Button>
      )}
      {canFulfillOrder(status) && (
        <Button variant="success" size="sm" onClick={() => onAction('fulfilled')}>
          Mark Fulfilled
        </Button>
      )}
      {canCancelOrder(status) && (
        <Button variant="danger" size="sm" onClick={() => onAction('cancel')}>
          Cancel
        </Button>
      )}
    </div>
  );
}

export default SalesOrderActionBar;
