import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import Button from '../components/Button';
import Field from '../components/Field';

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/clients';
  const signupMessage = location.state?.message;

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [globalErrors, setGlobalErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) return <Navigate to="/clients" replace />;

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setGlobalErrors({});

    const problems = {};
    if (!username.trim()) problems.username = 'Username is required.';
    if (!password) problems.password = 'Password is required.';
    if (Object.keys(problems).length) {
      setGlobalErrors(problems);
      return;
    }

    setSubmitting(true);
    try {
      await login(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      if (err.fieldErrors && Object.keys(err.fieldErrors).length) {
        setGlobalErrors(err.fieldErrors);
      } else {
        setError(err.message || 'Sign in failed. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-card__brand">
          <img
            src="/crm-logo.jpg"
            alt="CRM"
            className="login-card__brand-logo"
          />
        </div>
        <div className="login-card__body">
          <h1 className="login-card__title">Welcome back</h1>
          <p className="login-card__subtitle">Sign in to your CRM account</p>

          <form className="form" onSubmit={onSubmit} noValidate>
            {signupMessage && <div className="form-success-banner" role="status">{signupMessage}</div>}
            {error && <div className="form-error-banner" role="alert">{error}</div>}
            <Field label="Username" required error={globalErrors} errorKey="username" htmlFor="login-username">
              <input
                id="login-username"
                className="field__input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                autoFocus
              />
            </Field>
            <Field label="Password" required error={globalErrors} errorKey="password" htmlFor="login-password">
              <input
                id="login-password"
                type="password"
                className="field__input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </Field>
            <div className="login-card__forgot">
              <Link to="/forgot-password">Forgot password?</Link>
            </div>
            <Button type="submit" variant="primary" size="lg" block loading={submitting}>
              Sign in
            </Button>
          </form>

          <p className="login-card__footer">
            Don't have an account? <Link to="/signup">Sign up</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
