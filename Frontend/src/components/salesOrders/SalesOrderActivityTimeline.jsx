import { formatDate } from '../../utils/format';

const EVENT_TYPE_LABELS = {
  CREATED: 'Order created',
  EDITED: 'Order edited',
  CONVERTED_FROM_QUOTE: 'Converted from quote',
  ITEM_ADDED: 'Item added',
  ITEM_REMOVED: 'Item removed',
  ITEM_UPDATED: 'Item updated',
  SUBMITTED_FOR_APPROVAL: 'Submitted for approval',
  APPROVED: 'Approved',
  CONFIRMED: 'Confirmed',
  PROCESSING: 'Processing started',
  FULFILLED: 'Fulfilled',
  CANCELLED: 'Cancelled',
  PAYMENT_RECORDED: 'Payment recorded',
  PAYMENT_CONFIRMED: 'Payment confirmed',
  PAYMENT_REVERSED: 'Payment reversed',
  RECEIPT_ISSUED: 'Receipt issued',
  RECEIPT_VOIDED: 'Receipt voided',
  PORTAL_PUBLISHED: 'Published to portal',
  STATUS_CHANGED: 'Status changed',
};

export function SalesOrderActivityTimeline({ events = [] }) {
  if (events.length === 0) {
    return <div style={{ padding: 'var(--space-4)', color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }}>No activity yet.</div>;
  }

  return (
    <div className="quote-timeline">
      {events.map((event) => (
        <div key={event.event_id} className="quote-timeline__item">
          <div className="quote-timeline__dot" />
          <div className="quote-timeline__content">
            <div className="quote-timeline__header">
              <span className="quote-timeline__label">
                {EVENT_TYPE_LABELS[event.event_type] || event.event_type}
              </span>
              <span className="quote-timeline__date">{formatDate(event.occurred_at)}</span>
            </div>
            {event.description && (
              <div className="quote-timeline__description">{event.description}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default SalesOrderActivityTimeline;
