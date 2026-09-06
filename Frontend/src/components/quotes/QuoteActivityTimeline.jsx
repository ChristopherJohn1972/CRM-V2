import { formatDateTime } from '../../utils/format';

const EVENT_LABELS = {
  CREATED: 'Quote created',
  UPDATED: 'Quote updated',
  ITEM_ADDED: 'Item added',
  ITEM_REMOVED: 'Item removed',
  ITEM_UPDATED: 'Item updated',
  PRICE_OVERRIDDEN: 'Price overridden',
  DISCOUNT_APPLIED: 'Discount applied',
  TEMPLATE_SELECTED: 'Template selected',
  SUBMITTED_FOR_APPROVAL: 'Submitted for approval',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
  SENT: 'Sent to customer',
  VIEWED: 'Viewed by customer',
  ACCEPTED: 'Accepted by customer',
  DECLINED: 'Declined by customer',
  CHANGE_REQUESTED: 'Change requested by customer',
  EXPIRED: 'Quote expired',
  CANCELLED: 'Quote cancelled',
  DUPLICATED: 'Quote duplicated',
  DOCUMENT_GENERATED: 'PDF generated',
  PORTAL_PUBLISHED: 'Published to client portal',
  CONVERTED_TO_ORDER: 'Converted to sales order',
};

const EVENT_ICONS = {
  CREATED: 'plus',
  UPDATED: 'edit',
  ITEM_ADDED: 'plus',
  ITEM_REMOVED: 'minus',
  ITEM_UPDATED: 'edit',
  SUBMITTED_FOR_APPROVAL: 'clock',
  APPROVED: 'check',
  REJECTED: 'x',
  SENT: 'send',
  VIEWED: 'eye',
  ACCEPTED: 'check-circle',
  DECLINED: 'x-circle',
  CHANGE_REQUESTED: 'message',
  EXPIRED: 'clock',
  CANCELLED: 'x',
};

function QuoteActivityTimeline({ events = [] }) {
  if (events.length === 0) {
    return (
      <div className="quote-timeline-empty">
        <p className="text-muted">No activity recorded yet.</p>
      </div>
    );
  }

  return (
    <div className="quote-timeline">
      {events.map((event) => (
        <div key={event.event_id} className="quote-timeline__item">
          <div className="quote-timeline__dot" />
          <div className="quote-timeline__content">
            <div className="quote-timeline__label">
              {EVENT_LABELS[event.event_type] || event.event_type}
            </div>
            {event.description && (
              <div className="quote-timeline__desc">{event.description}</div>
            )}
            <div className="quote-timeline__time">{formatDateTime(event.occurred_at)}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default QuoteActivityTimeline;
