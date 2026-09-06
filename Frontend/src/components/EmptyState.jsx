export function EmptyState({ title = 'No records yet', body, action }) {
  return (
    <div className="empty-state">
      <div className="empty-state__title">{title}</div>
      {body && <div className="empty-state__body">{body}</div>}
      {action && <div style={{ display: 'inline-flex' }}>{action}</div>}
    </div>
  );
}

export default EmptyState;