import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { register } from '../api/auth';
import Button from '../components/Button';
import Field from '../components/Field';

export function SignUpPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
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
    if (!email.trim()) problems.email = 'Email is required.';
    if (!firstName.trim()) problems.firstName = 'First name is required.';
    if (!lastName.trim()) problems.lastName = 'Last name is required.';
    if (!password) problems.password = 'Password is required.';
    if (password.length < 8) problems.password = 'Password must be at least 8 characters.';
    if (password !== confirmPassword) problems.confirmPassword = 'Passwords do not match.';
    if (Object.keys(problems).length) {
      setGlobalErrors(problems);
      return;
    }

    setSubmitting(true);
    try {
      await register({ username, email, firstName, lastName, password, confirmPassword });
      navigate('/login', {
        replace: true,
        state: { message: 'Account created successfully. Please sign in.' },
      });
    } catch (err) {
      if (err.fieldErrors && Object.keys(err.fieldErrors).length) {
        setGlobalErrors(err.fieldErrors);
      } else {
        setError(err.message || 'Registration failed. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page signup-page">
      <div className="login-card signup-card">
        <div className="login-card__brand">
          <img
            src="/crm-logo.jpg"
            alt="CRM"
            className="login-card__brand-logo"
          />
        </div>
        <div className="login-card__body">
          <h1 className="login-card__title">Create account</h1>
          <p className="login-card__subtitle">Fill in the details below to get started.</p>

          <form className="form" onSubmit={onSubmit} noValidate>
            {error && <div className="form-error-banner" role="alert">{error}</div>}
            <div className="signup-name-row">
              <Field label="First name" required error={globalErrors} errorKey="firstName" htmlFor="signup-first-name">
                <input
                  id="signup-first-name"
                  className="field__input"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  autoComplete="given-name"
                  autoFocus
                />
              </Field>
              <Field label="Last name" required error={globalErrors} errorKey="lastName" htmlFor="signup-last-name">
                <input
                  id="signup-last-name"
                  className="field__input"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  autoComplete="family-name"
                />
              </Field>
            </div>
            <Field label="Username" required error={globalErrors} errorKey="username" htmlFor="signup-username">
              <input
                id="signup-username"
                className="field__input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
              />
            </Field>
            <Field label="Email" required error={globalErrors} errorKey="email" htmlFor="signup-email">
              <input
                id="signup-email"
                type="email"
                className="field__input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </Field>
            <Field label="Password" required error={globalErrors} errorKey="password" htmlFor="signup-password">
              <input
                id="signup-password"
                type="password"
                className="field__input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
              />
            </Field>
            <Field label="Confirm password" required error={globalErrors} errorKey="confirmPassword" htmlFor="signup-confirm-password">
              <input
                id="signup-confirm-password"
                type="password"
                className="field__input"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
              />
            </Field>
            <Button type="submit" variant="primary" size="lg" block loading={submitting}>
              Create account
            </Button>
          </form>

          <p className="login-card__footer">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default SignUpPage;
