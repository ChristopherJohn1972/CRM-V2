import { cn } from '../utils/cn';

function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function SearchBar({ value, onChange, placeholder = 'Search…', label = 'Search', autoFocus, className }) {
  return (
    <div className={cn('search-bar', className)}>
      <span className="search-bar__icon"><SearchIcon /></span>
      <label className="sr-only" htmlFor={`search-${label}`}>{label}</label>
      <input
        id={`search-${label}`}
        type="search"
        className="search-bar__input"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoFocus={autoFocus}
        autoComplete="off"
        spellCheck="false"
      />
    </div>
  );
}

export default SearchBar;