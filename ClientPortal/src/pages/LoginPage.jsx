import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { forgotPassword } from '../api/auth';
import Button from '../components/Button';
import Field from '../components/Field';

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/';

  const [accountNumber, setAccountNumber] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [forgotMode, setForgotMode] = useState(false);
  const [forgotSent, setForgotSent] = useState(false);
  const [forgotSubmitting, setForgotSubmitting] = useState(false);

  if (isAuthenticated) return <Navigate to="/" replace />;

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setErrors({});

    const problems = {};
    if (!accountNumber.trim()) problems.accountNumber = 'Account number is required.';
    if (!email.trim()) problems.email = 'Email is required.';
    if (!password) problems.password = 'Password is required.';
    if (Object.keys(problems).length) { setErrors(problems); return; }

    setSubmitting(true);
    try {
      const user = await login(accountNumber.trim(), email.trim().toLowerCase(), password);
      if (user.password_setup_required) {
        navigate('/setup-password', { replace: true });
      } else {
        navigate(from, { replace: true });
      }
    } catch (err) {
      if (err.fieldErrors && Object.keys(err.fieldErrors).length) {
        setErrors(err.fieldErrors);
      } else {
        setError(err.message || 'Sign in failed. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const onForgot = async (e) => {
    e.preventDefault();
    setForgotSubmitting(true);
    try {
      await forgotPassword(accountNumber.trim());
      setForgotSent(true);
    } catch {
      setForgotSent(true);
    } finally {
      setForgotSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-card__brand">
          <span className="login-card__brand-mark" aria-hidden="true" />
          <span className="login-card__brand-name">Client Portal</span>
        </div>

        {!forgotMode ? (
          <>
            <h1 className="login-card__title">Sign in</h1>
            <p className="login-card__subtitle">Enter your account details to access your portal.</p>

            <form className="form" onSubmit={onSubmit} noValidate>
              {error && <div className="form-error-banner" role="alert">{error}</div>}
              <Field label="Account Number" required error={errors} errorKey="accountNumber" htmlFor="login-account">
                <input
                  id="login-account"
                  className="field__input"
                  value={accountNumber}
                  onChange={(e) => setAccountNumber(e.target.value)}
                  autoComplete="username"
                  autoFocus
                  placeholder="e.g. 000124"
                />
              </Field>
              <Field label="Email" required error={errors} errorKey="email" htmlFor="login-email">
                <input
                  id="login-email"
                  type="email"
                  className="field__input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  placeholder="your@email.com"
                />
              </Field>
              <Field label="Password" required error={errors} errorKey="password" htmlFor="login-password">
                <div className="password-field">
                  <input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    className="field__input"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    className="password-field__toggle"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
              </Field>
              <Button type="submit" variant="primary" size="lg" block loading={submitting}>
                Sign in
              </Button>
            </form>

            <div className="login-card__links">
              <button type="button" className="btn btn--ghost btn--sm" onClick={() => setForgotMode(true)}>
                Forgot password?
              </button>
            </div>

            <div className="login-card__footer">
              Use your authorized account credentials. Never share your password.
            </div>
          </>
        ) : (
          <>
            <h1 className="login-card__title">Reset password</h1>
            <p className="login-card__subtitle">
              {forgotSent
                ? 'If an account exists with this number, a reset link has been sent.'
                : 'Enter your account number and we will send you a password reset link.'}
            </p>

            {!forgotSent ? (
              <form className="form" onSubmit={onForgot} noValidate>
                <Field label="Account Number" required htmlFor="forgot-account">
                  <input
                    id="forgot-account"
                    className="field__input"
                    value={accountNumber}
                    onChange={(e) => setAccountNumber(e.target.value)}
                    autoFocus
                  />
                </Field>
                <Button type="submit" variant="primary" size="lg" block loading={forgotSubmitting}>
                  Send reset link
                </Button>
              </form>
            ) : null}

            <div className="login-card__links" style={{ marginTop: 24 }}>
              <button type="button" className="btn btn--ghost btn--sm" onClick={() => { setForgotMode(false); setForgotSent(false); }}>
                Back to sign in
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default LoginPage;
