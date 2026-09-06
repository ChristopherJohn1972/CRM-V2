import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { setupPassword } from '../api/auth';
import Button from '../components/Button';
import Field from '../components/Field';

function getPasswordStrength(pw) {
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[a-z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 2) return { level: 'Weak', bars: 1, class: '' };
  if (score <= 3) return { level: 'Fair', bars: 2, class: 'fair' };
  if (score <= 4) return { level: 'Strong', bars: 3, class: 'strong' };
  return { level: 'Very Strong', bars: 4, class: 'strong' };
}

export function SetupPasswordPage() {
  const navigate = useNavigate();
  const { updateUser } = useAuth();
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const strength = useMemo(() => getPasswordStrength(newPassword), [newPassword]);

  const rules = [
    { label: 'At least 12 characters', met: newPassword.length >= 12 },
    { label: 'Contains uppercase letter', met: /[A-Z]/.test(newPassword) },
    { label: 'Contains lowercase letter', met: /[a-z]/.test(newPassword) },
    { label: 'Contains a number', met: /[0-9]/.test(newPassword) },
    { label: 'Contains a special character', met: /[^A-Za-z0-9]/.test(newPassword) },
  ];

  const allRulesMet = rules.every((r) => r.met);
  const passwordsMatch = newPassword.length > 0 && confirmPassword.length > 0 && newPassword === confirmPassword;
  const canSubmit = allRulesMet && passwordsMatch && !submitting;

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!allRulesMet) { setError('Please meet all password requirements.'); return; }
    if (!passwordsMatch) { setError('Passwords do not match.'); return; }

    setSubmitting(true);
    try {
      await setupPassword(newPassword);
      updateUser({ password_setup_required: false });
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.message || 'Failed to set password. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="password-setup-page">
      <div className="password-setup-card">
        <div className="login-card__brand">
          <span className="login-card__brand-mark" aria-hidden="true" />
          <span className="login-card__brand-name">Client Portal</span>
        </div>

        <h1 className="login-card__title">Create your password</h1>
        <p className="login-card__subtitle">
          For security, you must create a strong password before accessing the portal.
        </p>

        <form className="form" onSubmit={onSubmit} noValidate>
          {error && <div className="form-error-banner" role="alert">{error}</div>}

          <Field label="New Password" required htmlFor="new-password">
            <div className="password-field">
              <input
                id="new-password"
                type={showPassword ? 'text' : 'password'}
                className="field__input"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoFocus
              />
              <button
                type="button"
                className="password-field__toggle"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
            {newPassword && (
              <>
                <div className="strength-meter">
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className={`strength-meter__bar${i <= strength.bars ? ` strength-meter__bar--filled strength-meter__bar--${strength.class}` : ''}`}
                    />
                  ))}
                </div>
                <div className="strength-meter__label">{strength.level}</div>
              </>
            )}
            <ul className="password-rules">
              {rules.map((r) => (
                <li key={r.label} className={r.met ? 'is-met' : ''}>{r.label}</li>
              ))}
            </ul>
          </Field>

          <Field label="Confirm Password" required htmlFor="confirm-password">
            <input
              id="confirm-password"
              type={showPassword ? 'text' : 'password'}
              className="field__input"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
            {confirmPassword && !passwordsMatch && (
              <div className="field__error">Passwords do not match</div>
            )}
          </Field>

          <Button type="submit" variant="primary" size="lg" block loading={submitting}>
            {submitting ? 'Setting password...' : 'Set password and continue'}
          </Button>
        </form>

        <div className="login-card__footer" style={{ marginTop: 24 }}>
          Never use your account number, company name, or easily guessed information.
        </div>
      </div>
    </div>
  );
}

export default SetupPasswordPage;
