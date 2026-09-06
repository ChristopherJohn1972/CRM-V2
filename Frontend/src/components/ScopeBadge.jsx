import { SCOPE_MEANINGS } from '../utils/constants';

export function ScopeBadge({ scope, className, showMeaning = false }) {
  if (!scope) return <span className="badge badge--neutral">NONE</span>;
  const meaning = SCOPE_MEANINGS[scope] || '';
  return (
    <span className={className} title={meaning || undefined}>
      {scope}
      {showMeaning && meaning && <span style={{ marginLeft: 6, color: 'inherit', opacity: 0.75 }}>{meaning}</span>}
    </span>
  );
}

export default ScopeBadge;
