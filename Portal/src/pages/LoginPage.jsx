import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { usePortalAuth } from '../auth/PortalAuth';

export function LoginPage() {
  const { login, isAuthenticated } = usePortalAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) return <Navigate to="/quotes" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!email.trim() || !password) {
      setError('Please enter your email and password.');
      return;
    }
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate('/quotes', { replace: true });
    } catch (err) {
      setError(err.message || 'Login failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="portal-login">
      <div className="portal-login__card">
        <div className="portal-login__brand">
          <div className="portal-login__logo" />
          <h1>Client Portal</h1>
        </div>
        <p className="portal-login__subtitle">Sign in to view your quotes and account.</p>

        <form className="portal-form" onSubmit={handleSubmit}>
          {error && <div className="portal-form-error" role="alert">{error}</div>}

          <div className="portal-field">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              type="email"
              className="portal-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              autoFocus
              required
            />
          </div>

          <div className="portal-field">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              className="portal-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          <button type="submit" className="portal-btn portal-btn--primary portal-btn--block" disabled={submitting}>
            {submitting ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;
