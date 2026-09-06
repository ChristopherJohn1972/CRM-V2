import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getAccessReview, getOperator } from '../../api/iam';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import ErrorState from '../../components/ErrorState';
import AccessMatrix from '../../components/AccessMatrix';
import { operatorDisplayName } from '../../utils/iam';
import { OPERATOR_STATUS, OPERATOR_STATUS_VARIANT } from '../../utils/constants';

export function AccessReviewPage() {
  const { operatorId } = useParams();
  const [review, setReview] = useState(null);
  const [operator, setOperator] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [reviewRes, operatorRes] = await Promise.all([
        getAccessReview(operatorId),
        getOperator(operatorId).catch(() => null),
      ]);
      setReview(reviewRes);
      setOperator(operatorRes);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [operatorId]);

  useEffect(() => {
    load();
  }, [load]);

  const stats = useMemo(() => {
    const permissions = review?.permissions || [];
    return {
      allowed: permissions.filter((p) => p.effective === 'ALLOW').length,
      denied: permissions.filter((p) => p.effective === 'DENY').length,
      none: permissions.filter((p) => p.effective === 'NONE').length,
    };
  }, [review]);

  if (error) {
    return <ErrorState title="Could not load access review" body={error.message} onRetry={load} />;
  }
  if (loading || !review) {
    return <p className="cell-secondary">Loading access review…</p>;
  }

  const name = operatorDisplayName(operator || review);

  return (
    <div className="page">
      <PageHeader
        title="Access Review"
        subtitle={`Effective permissions for ${name} (@${review.username}).`}
        breadcrumbs={[
          { label: 'Operators', to: '/operators' },
          { label: name, to: `/operators/${review.user_id}` },
          { label: 'Access Review' },
        ]}
        actions={<Link className="btn btn--secondary" to={`/operators/${review.user_id}`}>Back to profile</Link>}
      />

      <div className="review-grid">
        <section className="card">
          <div className="card__header"><h3 className="card__title">Identity</h3></div>
          <div className="card__body">
            <div className="def-list">
              <dt>Name</dt><dd>{name}</dd>
              <dt>Username</dt><dd>@{review.username}</dd>
              <dt>Email</dt><dd>{review.email || '—'}</dd>
              <dt>Status</dt>
              <dd>
                <StatusBadge variant={OPERATOR_STATUS_VARIANT[review.status] || 'neutral'}>
                  {OPERATOR_STATUS[review.status] || review.status}
                </StatusBadge>
              </dd>
            </div>
          </div>
        </section>

        <section className="card">
          <div className="card__header"><h3 className="card__title">Roles</h3></div>
          <div className="card__body">
            {review.roles.length === 0 ? (
              <p className="cell-secondary">No roles assigned.</p>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {review.roles.map((r) => (
                  <span key={r.role_id} className="badge badge--neutral">
                    {r.name}
                    {r.is_system_role && <span style={{ marginLeft: 6, opacity: 0.7 }}>system</span>}
                  </span>
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="card">
          <div className="card__header"><h3 className="card__title">Scope</h3></div>
          <div className="card__body">
            <div className="def-list">
              <dt>Effective scope</dt>
              <dd><strong>{review.scope.effective}</strong></dd>
              <dt>Meaning</dt><dd>{review.scope.meaning}</dd>
              <dt>Policies</dt>
              <dd>
                {review.scope.policies.length === 0 ? (
                  <span className="cell-secondary">None</span>
                ) : (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                    {review.scope.policies.map((p) => <span key={p} className="badge badge--neutral badge--small">{p}</span>)}
                  </div>
                )}
              </dd>
            </div>
          </div>
        </section>

        <section className="card">
          <div className="card__header"><h3 className="card__title">Summary</h3></div>
          <div className="card__body">
            <div className="def-list">
              <dt>Granted (ALLOW)</dt><dd><strong>{stats.allowed}</strong></dd>
              <dt>Denied (DENY)</dt><dd><strong>{stats.denied}</strong></dd>
              <dt>Not granted</dt><dd><strong>{stats.none}</strong></dd>
            </div>
          </div>
        </section>
      </div>

      <section className="card" style={{ marginTop: 20 }}>
        <div className="card__header">
          <h3 className="card__title">Effective rights</h3>
          <p className="field__hint">Each right shows the winning effect and the role or direct exception that produced it. DENY wins.</p>
        </div>
        <div className="card__body">
          <AccessMatrix rightsByResource={review.rights_by_resource} scope={review.scope} />
        </div>
      </section>
    </div>
  );
}

export default AccessReviewPage;
