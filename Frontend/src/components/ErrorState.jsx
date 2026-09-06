import Button from './Button';

export function ErrorState({ title = 'Something went wrong', body, detail, onRetry }) {
  return (
    <div className="error-state">
      <div className="empty-state__title">{title}</div>
      <div className="error-state__body">{body || 'An unexpected error occurred while loading this data.'}</div>
      {detail && <div className="error-state__detail">{detail}</div>}
      {onRetry && (
        <div style={{ display: 'inline-flex' }}>
          <Button variant="secondary" onClick={onRetry}>Try again</Button>
        </div>
      )}
    </div>
  );
}

export default ErrorState;