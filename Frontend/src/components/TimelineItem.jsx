import { formatDateTime } from '../utils/format';
import StatusBadge from './StatusBadge';

export function TimelineItem({ summary, occurredAt, actorLabel, sourceModule, meta, variant = 'info' }) {
  return (
    <div className="timeline-item">
      <span className={`timeline-item__dot timeline-item__dot--${variant}`} aria-hidden="true" />
      <div className="timeline-item__content">
        <div className="timeline-item__summary">{summary}</div>
        <div className="timeline-item__meta">
          {occurredAt && <span>{formatDateTime(occurredAt)}</span>}
          {actorLabel && <span>{actorLabel}</span>}
          {sourceModule && <StatusBadge variant="muted" dot={false}>{sourceModule}</StatusBadge>}
          {meta}
        </div>
      </div>
    </div>
  );
}

export default TimelineItem;