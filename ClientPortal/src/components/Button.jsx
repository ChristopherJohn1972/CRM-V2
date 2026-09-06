import { cn } from '../utils/cn';

export function Button({ children, variant = 'secondary', size, type = 'button', loading = false, disabled, className, ...rest }) {
  return (
    <button type={type} className={cn('btn', `btn--${variant}`, size && `btn--${size}`, className)} disabled={disabled || loading} {...rest}>
      {loading && <span className="spinner" aria-hidden="true" />}
      {children}
    </button>
  );
}

export default Button;
