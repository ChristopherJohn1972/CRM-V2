import { EffectBadge } from './EffectBadge';

/**
 * Traces how an effective permission was derived: role grants and/or direct
 * user-level ALLOW/DENY exceptions (DENY wins).
 */
export function SourceChips({ sources }) {
  if (!sources || sources.length === 0) {
    return <span className="cell-secondary">No source</span>;
  }

  return (
    <div className="source-chips" style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
      {sources.map((source, i) => {
        if (source.source === 'role') {
          return (
            <span key={i} className="source-chip source-chip--role" title={`Granted by role ${source.role_code}`}>
              <span className="source-chip__name">{source.role_name || source.role_code}</span>
              <EffectBadge effect={source.effect} className="badge--small" />
            </span>
          );
        }
        return (
          <span key={i} className="source-chip source-chip--direct" title={source.reason || 'Direct permission exception'}>
            <span className="source-chip__name">Direct exception</span>
            <EffectBadge effect={source.effect} className="badge--small" />
          </span>
        );
      })}
    </div>
  );
}

export default SourceChips;
