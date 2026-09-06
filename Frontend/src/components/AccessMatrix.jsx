import { EffectBadge } from './EffectBadge';
import { SourceChips } from './SourceChips';

function ScopeCell({ scope }) {
  if (!scope) return null;
  return (
    <div className="access-matrix__scope">
      <div className="access-matrix__scope-title">{scope.resource || scope.code || scope}</div>
      {scope.meaning && <div className="cell-secondary">{scope.meaning}</div>}
      {scope.policies && scope.policies.length > 0 && (
        <div className="access-matrix__policies">
          {scope.policies.map((p) => (
            <span key={p} className="badge badge--neutral badge--small">{p}</span>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Renders an effective-permission matrix grouped by resource, with each
 * permission's winning effect and its source trace (roles / direct).
 */
export function AccessMatrix({ rightsByResource, scope, dense = false }) {
  if (!rightsByResource || Object.keys(rightsByResource).length === 0) {
    return <p className="cell-secondary">No rights granted.</p>;
  }

  return (
    <div className="access-matrix">
      {Object.entries(rightsByResource).map(([resource, perms]) => (
        <section key={resource} className="access-matrix__group">
          <h3 className="access-matrix__resource">{resource}</h3>
          <table className="access-matrix__table">
            <thead>
              <tr>
                <th>Right</th>
                <th>Effect</th>
                {!dense && <th>Source</th>}
              </tr>
            </thead>
            <tbody>
              {perms.map((p) => (
                <tr key={p.code || p.permission_id}>
                  <td>
                    <div className="access-matrix__name">{p.name || p.code}</div>
                    {p.description && <div className="cell-secondary">{p.description}</div>}
                  </td>
                  <td><EffectBadge effect={p.effective || p.effect} /></td>
                  {!dense && (
                    <td>
                      {p.sources ? <SourceChips sources={p.sources} /> : <span className="cell-secondary">—</span>}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
      {scope && (
        <section className="access-matrix__group">
          <h3 className="access-matrix__resource">Scope</h3>
          <ScopeCell scope={scope} />
        </section>
      )}
    </div>
  );
}

export default AccessMatrix;
