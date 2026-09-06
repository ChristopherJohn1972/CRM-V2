import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="page" style={{ paddingTop: '12vh', textAlign: 'center' }}>
      <h1 style={{ fontSize: 'var(--text-2xl)', marginBottom: 8 }}>Page not found</h1>
      <p style={{ color: 'var(--color-text-secondary)', marginBottom: 20 }}>
        The page you are looking for does not exist or you may not have access to it.
      </p>
      <Link to="/clients" className="btn btn--primary">Back to Clients</Link>
    </div>
  );
}

export default NotFoundPage;