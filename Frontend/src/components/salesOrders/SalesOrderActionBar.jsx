import Button from '../Button';
import { PermissionGate } from '../PermissionGate';
import { useAuth } from '../../auth/AuthContext';
import { PERMISSIONS } from '../../utils/constants';
import {
  canEditOrder, canSubmitForApproval, canApproveOrder,
  canConfirmOrder, canCancelOrder, canProcessOrder, canFulfillOrder, canOnHoldOrder,
} from '../../utils/salesOrders';

export function SalesOrderActionBar({ status, onAction, canEdit }) {
  const { hasPermission } = useAuth();
  const canUpdate = hasPermission(PERMISSIONS.SALES_ORDER_UPDATE);
  const canWorkflow = hasPermission(PERMISSIONS.SALES_ORDER_WORKFLOW);

  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      {canUpdate && canSubmitForApproval(status) && (
        <Button variant="primary" size="sm" onClick={() => onAction('submit_approval')}>
          Submit for Approval
        </Button>
      )}
      {canWorkflow && canApproveOrder(status) && (
        <Button variant="primary" size="sm" onClick={() => onAction('approve')}>
          Approve
        </Button>
      )}
      {canUpdate && canConfirmOrder(status) && (
        <Button variant="primary" size="sm" onClick={() => onAction('confirm')}>
          Confirm Order
        </Button>
      )}
      {canWorkflow && canProcessOrder(status) && (
        <Button variant="primary" size="sm" onClick={() => onAction('processing')}>
          Mark Processing
        </Button>
      )}
      {canWorkflow && canOnHoldOrder(status) && (
        <Button variant="ghost" size="sm" onClick={() => onAction('on_hold')}>
          On Hold
        </Button>
      )}
      {canWorkflow && canFulfillOrder(status) && (
        <Button variant="success" size="sm" onClick={() => onAction('fulfilled')}>
          Mark Fulfilled
        </Button>
      )}
      {canUpdate && canCancelOrder(status) && (
        <Button variant="danger" size="sm" onClick={() => onAction('cancel')}>
          Cancel
        </Button>
      )}
    </div>
  );
}

export default SalesOrderActionBar;
