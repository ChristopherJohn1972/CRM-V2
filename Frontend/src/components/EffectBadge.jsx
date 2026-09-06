import { cn } from '../utils/cn';

const VARIANTS = ['success', 'danger', 'muted'];

export function EffectBadge({ effect, className }) {
  const value = effect === 'ALLOW' || effect === 'DENY' ? effect : 'NONE';
  const variant = value === 'ALLOW' ? 'success' : value === 'DENY' ? 'danger' : 'muted';
  return (
    <span className={cn('badge', `badge--${variant}`, !VARIANTS.includes(variant) && 'badge--neutral', className)}>
      {value}
    </span>
  );
}

export default EffectBadge;
