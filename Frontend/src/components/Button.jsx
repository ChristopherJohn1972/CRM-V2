import { cn } from '../utils/cn';

export function Button({
  children,
  variant = 'secondary',
  size,
  block,
  type = 'button',
  loading = false,
  disabled,
  className,
  ...rest
}) {
  return (
    <button
      type={type}
      className={cn('btn', `btn--${variant}`, size && `btn--${size}`, block && 'btn--block', className)}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <span className="spinner" aria-hidden="true" />}
      {children}
    </button>
  );
}

export default Button;