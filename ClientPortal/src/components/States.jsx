export function EmptyState({ title = 'Nothing here yet', body, action }) {
  return (
    <div className="empty-state">
      <div className="empty-state__title">{title}</div>
      {body && <div className="empty-state__body">{body}</div>}
      {action}
    </div>
  );
}

export function ErrorState({ title = 'Something went wrong', detail, onRetry }) {
  return (
    <div className="error-state">
      <div className="empty-state__title">{title}</div>
      {detail && <div className="error-state__detail">{detail}</div>}
      {onRetry && (
        <button className="btn btn--secondary" onClick={onRetry} style={{ marginTop: 16 }}>
          Try again
        </button>
      )}
    </div>
  );
}
