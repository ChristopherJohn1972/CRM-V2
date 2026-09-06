import Button from './Button';
import { PermissionGate } from './PermissionGate';

export function ActionButton({ permission, ...rest }) {
  return (
    <PermissionGate permission={permission}>
      <Button {...rest} />
    </PermissionGate>
  );
}

export default ActionButton;