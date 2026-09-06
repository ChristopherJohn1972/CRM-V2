import { cn } from '../utils/cn';

export function Field({ label, required, error, errorKey, htmlFor, children, className }) {
  const errorMsg = errorKey && error ? error[errorKey] : null;
  return (
    <div className={cn('field', errorMsg && 'field--invalid', className)}>
      {label && (
        <label className="field__label" htmlFor={htmlFor}>
          {label}
          {required && <span className="field__required"> *</span>}
        </label>
      )}
      {children}
      {errorMsg && <div className="field__error">{errorMsg}</div>}
    </div>
  );
}

export default Field;
