import { cn } from '../utils/cn';
import { STATUS_COLORS, CAMPAIGN_STATUS_COLORS } from '../utils/constants';

const VARIANTS = ['success', 'warning', 'danger', 'info', 'muted', 'neutral'];

export function StatusBadge({ label, variant = 'neutral', status, dot = true, className, children }) {
  const text = label ?? children;
  const colors = status ? (STATUS_COLORS[status] || CAMPAIGN_STATUS_COLORS[status]) : null;

  if (colors) {
    return (
      <span
        className={cn('badge', 'badge--status', !dot && 'badge--plain', className)}
        style={{
          background: colors.bg,
          color: colors.text,
        }}
      >
        {dot && (
          <span
            className="badge__dot"
            style={{ background: colors.dot }}
          />
        )}
        {text}
      </span>
    );
  }

  const cls = cn('badge', VARIANTS.includes(variant) && `badge--${variant}`, !dot && 'badge--plain', className);
  return <span className={cls}>{text}</span>;
}

export default StatusBadge;