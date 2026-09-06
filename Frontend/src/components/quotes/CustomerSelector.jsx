import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { listCustomers } from '../../api/customers';
import { useDebouncedValue } from '../../utils/useDebouncedValue';

export function CustomerSelector({ value, onChange, disabled = false, onClear }) {
  const [search, setSearch] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const debouncedSearch = useDebouncedValue(search, 300);
  const abortRef = useRef(null);
  const wrapperRef = useRef(null);

  useEffect(() => {
    if (!debouncedSearch || debouncedSearch.length < 2) {
      setResults([]);
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    listCustomers({ search: debouncedSearch, page_size: 8 })
      .then((res) => {
        if (!controller.signal.aborted) {
          setResults(res.results || []);
          setOpen(true);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [debouncedSearch]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleKeyDown = (e) => {
    if (!open || results.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && highlightedIndex >= 0) {
      e.preventDefault();
      selectCustomer(results[highlightedIndex]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  const selectCustomer = (customer) => {
    onChange(customer);
    setSearch('');
    setResults([]);
    setOpen(false);
    setHighlightedIndex(-1);
  };

  const displayName = value
    ? value.legal_name || [value.first_name, value.middle_name, value.last_name].filter(Boolean).join(' ')
    : '';

  return (
    <div className="customer-selector" ref={wrapperRef}>
      {value ? (
        <div className="customer-selector__selected">
          <div className="customer-selector__selected-info">
            <div className="customer-selector__selected-name">{displayName}</div>
            <div className="customer-selector__selected-meta">
              {value.customer_number && <span className="badge badge--neutral">{value.customer_number}</span>}
              {value.email && <span className="cell-secondary">{value.email}</span>}
              {value.phone && <span className="cell-secondary">{value.phone}</span>}
            </div>
          </div>
          <div className="customer-selector__selected-actions">
            <Link to={`/customers/${value.customer_id}`} className="btn btn--ghost btn--sm">View Profile</Link>
            {!disabled && (
              <button type="button" className="btn btn--ghost btn--sm" onClick={() => { onClear?.(); onChange(null); }}>Change</button>
            )}
          </div>
        </div>
      ) : (
        <div className="customer-selector__search-wrap">
          <input
            type="text"
            className="field__input"
            placeholder="Search by name, account number, email or phone..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setHighlightedIndex(-1); }}
            onFocus={() => results.length > 0 && setOpen(true)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
          />
          {loading && <span className="customer-selector__spinner" />}
          {open && results.length > 0 && (
            <div className="customer-selector__dropdown">
              {results.map((c, idx) => {
                const name = c.legal_name || [c.first_name, c.middle_name, c.last_name].filter(Boolean).join(' ');
                return (
                  <button
                    key={c.customer_id}
                    type="button"
                    className={`customer-selector__option${idx === highlightedIndex ? ' is-highlighted' : ''}`}
                    onClick={() => selectCustomer(c)}
                    onMouseEnter={() => setHighlightedIndex(idx)}
                  >
                    <span className="customer-selector__option-name">{name}</span>
                    <span className="customer-selector__option-meta">
                      {c.customer_number && <span className="badge badge--neutral">{c.customer_number}</span>}
                      {c.email && <span>{c.email}</span>}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default CustomerSelector;
