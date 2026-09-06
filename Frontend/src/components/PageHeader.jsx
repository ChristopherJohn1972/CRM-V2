import { cn } from '../utils/cn';

export function PageHeader({ title, subtitle, breadcrumbs, actions, className }) {
  return (
    <header className={cn('page-header', className)}>
      <div>
        {breadcrumbs && (
          <nav className="breadcrumbs" aria-label="Breadcrumb">
            {breadcrumbs.map((crumb, i) => {
              const isLast = i === breadcrumbs.length - 1;
              return (
                <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                  {i > 0 && <span className="breadcrumbs__sep">/</span>}
                  {crumb.to && !isLast ? <a href={crumb.to}>{crumb.label}</a> : <span>{crumb.label}</span>}
                </span>
              );
            })}
          </nav>
        )}
        <h1 className="page-header__title">{title}</h1>
        {subtitle && <p className="page-header__subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </header>
  );
}

export default PageHeader;