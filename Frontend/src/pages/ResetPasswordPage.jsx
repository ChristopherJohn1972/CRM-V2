import { useState } from 'react';
import { Link, Navigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { resetPassword } from '../api/auth';
import Button from '../components/Button';
import Field from '../components/Field';

export function ResetPasswordPage() {
  const { isAuthenticated } = useAuth();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState(null);
  const [globalErrors, setGlobalErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [resetDone, setResetDone] = useState(false);

  if (isAuthenticated) return <Navigate to="/clients" replace />;

  if (!token) {
    return (
      <div className="login-page">
        <div className="login-card">
          <div className="login-card__brand">
            <img src="/crm-logo.jpg" alt="CRM" className="login-card__brand-logo" />
          </div>
          <div className="login-card__body">
            <h1 className="login-card__title">Invalid link</h1>
            <p className="login-card__subtitle">
              This password reset link is invalid or missing a token.
            </p>
            <Link to="/forgot-password" className="btn btn--primary btn--lg btn--block" style={{ marginTop: 'var(--space-3)', textAlign: 'center' }}>
              Try again
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setGlobalErrors({});

    const problems = {};
    if (!newPassword) problems.newPassword = 'New password is required.';
    if (newPassword.length < 8) problems.newPassword = 'Password must be at least 8 characters.';
    if (newPassword !== confirmPassword) problems.confirmPassword = 'Passwords do not match.';
    if (Object.keys(problems).length) {
      setGlobalErrors(problems);
      return;
    }

    setSubmitting(true);
    try {
      await resetPassword(token, newPassword, confirmPassword);
      setResetDone(true);
    } catch (err) {
      if (err.fieldErrors && Object.keys(err.fieldErrors).length) {
        setGlobalErrors(err.fieldErrors);
      } else {
        setError(err.message || 'Password reset failed. The link may have expired.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (resetDone) {
    return (
      <div className="login-page">
        <div className="login-card">
          <div className="login-card__brand">
            <img src="/crm-logo.jpg" alt="CRM" className="login-card__brand-logo" />
          </div>
          <div className="login-card__body">
            <h1 className="login-card__title">Password reset successful</h1>
            <p className="login-card__subtitle">
              Your password has been updated successfully.
            </p>
            <Link to="/login" className="btn btn--primary btn--lg btn--block" style={{ marginTop: 'var(--space-3)', textAlign: 'center' }}>
              Sign in
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
          <h1 className="login-card__title">Reset your password</h1>
          <p className="login-card__subtitle">
            Enter your new password below.
          </p>

          <form className="form" onSubmit={onSubmit} noValidate>
            {error && <div className="form-error-banner" role="alert">{error}</div>}
            <Field label="New password" required error={globalErrors} errorKey="newPassword" htmlFor="rp-new-password">
              <input
                id="rp-new-password"
                type="password"
                className="field__input"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
                autoFocus
              />
            </Field>
            <Field label="Confirm password" required error={globalErrors} errorKey="confirmPassword" htmlFor="rp-confirm-password">
              <input
                id="rp-confirm-password"
                type="password"
                className="field__input"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
              />
            </Field>
            <Button type="submit" variant="primary" size="lg" block loading={submitting}>
              Reset password
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

export default ResetPasswordPage;
