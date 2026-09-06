import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePortalAuth } from '../../auth/PortalAuthContext';

export function PortalLoginPage() {
  const navigate = useNavigate();
  const { login } = usePortalAuth();
  const [email, setEmail] = useState('');
  const [accountNumber, setAccountNumber] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, accountNumber, password);
      navigate('/portal');
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="portal-login">
      <div className="portal-login__card">
        <div className="portal-login__header">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true">
            <rect x="4" y="4" width="32" height="32" rx="6" stroke="currentColor" strokeWidth="2.5" />
            <path d="M14 20h12M20 14v12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
          <h1 className="portal-login__title">Client Portal</h1>
          <p className="portal-login__subtitle">Sign in to view your quotes and account</p>
        </div>

        {error && (
          <div className="form-error-banner" role="alert">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="portal-login__form">
          <div className="field">
            <label className="field__label" htmlFor="portal-email">Email</label>
            <input
              id="portal-email"
              type="email"
              className="field__input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="your@email.com"
            />
          </div>

          <div className="field">
            <label className="field__label" htmlFor="portal-account">Account Number</label>
            <input
              id="portal-account"
              type="text"
              className="field__input"
              value={accountNumber}
              onChange={(e) => setAccountNumber(e.target.value)}
              required
              autoComplete="off"
              placeholder="e.g. 0001"
            />
          </div>

          <div className="field">
            <label className="field__label" htmlFor="portal-password">Password</label>
            <input
              id="portal-password"
              type="password"
              className="field__input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              placeholder="Enter your password"
            />
          </div>

          <button type="submit" className="btn btn--primary btn--block" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="portal-login__footer">
          <a href="/portal/forgot-password" className="portal-login__link">Forgot password?</a>
          <span className="portal-login__divider">|</span>
          <a href="/login" className="portal-login__link">Staff login</a>
        </div>
      </div>
    </div>
  );
}

export default PortalLoginPage;
