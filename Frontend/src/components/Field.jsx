import { cn } from '../utils/cn';

export function Field({
  label,
  required,
  error,
  hint,
  errorKey,
  children,
  className,
  id,
  htmlFor,
}) {
  // Support both `error="Message"` and object form `errors={{ field: "Msg" }}`
  const resolvedError = typeof error === 'object' && error ? error[errorKey] : error;
  return (
    <div className={cn('field', resolvedError && 'field--invalid', className)}>
      {label && (
        <label className="field__label" htmlFor={htmlFor || id}>
          {label}
          {required && <span className="field__required" aria-hidden="true"> *</span>}
        </label>
      )}
      {children}
      {errorKey && typeof error !== 'string' && !resolvedError && null}
      {hint && !resolvedError && <span className="field__hint">{hint}</span>}
      {resolvedError && <span className="field__error" role="alert">{resolvedError}</span>}
    </div>
  );
}

export default Field;