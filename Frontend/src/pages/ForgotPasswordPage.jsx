import { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { forgotPassword } from '../api/auth';
import Button from '../components/Button';
import Field from '../components/Field';

export function ForgotPasswordPage() {
  const { isAuthenticated } = useAuth();

  const [username, setUsername] = useState('');
  const [error, setError] = useState(null);
  const [globalErrors, setGlobalErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  if (isAuthenticated) return <Navigate to="/clients" replace />;

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setGlobalErrors({});

    const problems = {};
    if (!username.trim()) problems.username = 'Username is required.';
    if (Object.keys(problems).length) {
      setGlobalErrors(problems);
      return;
    }

    setSubmitting(true);
    try {
      await forgotPassword(username.trim());
      setSent(true);
    } catch (err) {
      if (err.fieldErrors && Object.keys(err.fieldErrors).length) {
        setGlobalErrors(err.fieldErrors);
      } else {
        setError(err.message || 'Something went wrong. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (sent) {
    return (
      <div className="login-page">
        <div className="login-card">
          <div className="login-card__brand">
            <img src="/crm-logo.jpg" alt="CRM" className="login-card__brand-logo" />
          </div>
          <div className="login-card__body">
            <h1 className="login-card__title">Check your username</h1>
            <p className="login-card__subtitle">
              If an account exists for <strong>{username}</strong>, reset instructions have been sent.
            </p>
            <Link to="/login" className="btn btn--primary btn--lg btn--block" style={{ marginTop: 'var(--space-3)', textAlign: 'center' }}>
              Back to Sign in
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-card__brand">
          <img src="/crm-logo.jpg" alt="CRM" className="login-card__brand-logo" />
        </div>
        <div className="login-card__body">
          <h1 className="login-card__title">Forgot your password?</h1>
          <p className="login-card__subtitle">
            Enter your username and we'll help you reset your password.
          </p>

          <form className="form" onSubmit={onSubmit} noValidate>
            {error && <div className="form-error-banner" role="alert">{error}</div>}
            <Field label="Username" required error={globalErrors} errorKey="username" htmlFor="fp-username">
              <input
                id="fp-username"
                className="field__input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                autoFocus
              />
            </Field>
            <Button type="submit" variant="primary" size="lg" block loading={submitting}>
              Continue
            </Button>
          </form>

          <p className="login-card__footer">
            <Link to="/login">Back to Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default ForgotPasswordPage;
