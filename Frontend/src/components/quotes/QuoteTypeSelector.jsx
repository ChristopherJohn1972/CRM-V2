import { QUOTE_TYPE, QUOTE_TYPE_LABELS } from '../../utils/constants';
import { QUOTE_TYPE_DESCRIPTIONS } from '../../utils/quotes';

const TYPE_ICONS = {
  PRODUCT: (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <rect x="4" y="8" width="24" height="18" rx="2" stroke="currentColor" strokeWidth="2" />
      <path d="M4 14h24" stroke="currentColor" strokeWidth="2" />
      <path d="M12 8V4h8v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  SERVICE: (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <circle cx="16" cy="16" r="11" stroke="currentColor" strokeWidth="2" />
      <path d="M16 10v6l4 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  PROJECT: (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <path d="M4 10a2 2 0 012-2h8l2 2h10a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V10z" stroke="currentColor" strokeWidth="2" />
      <path d="M10 18h12M10 22h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
};

function QuoteTypeCard({ type, selected, onSelect }) {
  return (
    <button
      type="button"
      className={`quote-type-card${selected ? ' quote-type-card--selected' : ''}`}
      onClick={() => onSelect(type)}
    >
      <div className="quote-type-card__icon">
        {TYPE_ICONS[type]}
      </div>
      <div className="quote-type-card__content">
        <div className="quote-type-card__title">{QUOTE_TYPE_LABELS[type]}</div>
        <div className="quote-type-card__description">{QUOTE_TYPE_DESCRIPTIONS[type]}</div>
      </div>
      {selected && (
        <div className="quote-type-card__check">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <circle cx="10" cy="10" r="10" fill="var(--color-primary)" />
            <path d="M6 10l3 3 5-6" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      )}
    </button>
  );
}

export function QuoteTypeSelector({ selected, onSelect }) {
  return (
    <div className="quote-type-selector">
      <div className="quote-type-selector__title">What are you quoting?</div>
      <div className="quote-type-selector__subtitle">Select the type of quotation you want to create.</div>
      <div className="quote-type-selector__grid">
        {Object.values(QUOTE_TYPE).map((type) => (
          <QuoteTypeCard
            key={type}
            type={type}
            selected={selected === type}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  );
}

export default QuoteTypeSelector;
