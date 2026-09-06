import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div style={{ textAlign: 'center', padding: 'var(--space-10) var(--space-5)' }}>
      <h1 style={{ fontSize: 'var(--text-3xl)', fontWeight: 600, marginBottom: 'var(--space-3)' }}>404</h1>
      <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-6)' }}>The page you are looking for does not exist.</p>
      <Link to="/" className="btn btn--primary">Go to Dashboard</Link>
    </div>
  );
}

export default NotFoundPage;
