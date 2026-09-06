import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listLeads } from '../../api/leads';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';

function cleanEnum(value) {
  if (!value || typeof value !== 'string') return value;
  const dotIndex = value.lastIndexOf('.');
  return dotIndex >= 0 ? value.slice(dotIndex + 1) : value;
}

const LEAD_STATUS_LABELS = {
  NEW: 'Received',
  QUALIFIED: 'Being reviewed',
  CONTACTED: 'Our team is in touch',
  CONVERTED: 'Purchase completed',
  LOST: 'Closed',
  SUPPRESSED: 'Communication unavailable',
};

function leadStatusLabel(status) {
  const key = cleanEnum(status);
  return LEAD_STATUS_LABELS[key] || key;
}

const LEAD_STATUS_VARIANT = {
  NEW: 'info',
  QUALIFIED: 'warning',
  CONTACTED: 'info',
  CONVERTED: 'success',
  LOST: 'muted',
  SUPPRESSED: 'muted',
};

function leadStatusVariant(status) {
  const key = cleanEnum(status);
  return LEAD_STATUS_VARIANT[key] || 'neutral';
}

export default function MyInterestsPage() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await listLeads({ page_size: 50 });
        setLeads(data.results || []);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="portal-page">
        <div className="loading-spinner">Loading...</div>
      </div>
    );
  }

  return (
    <div className="portal-page">
      <PageHeader title="My Interests" subtitle="Your submitted interest registrations" />

      {leads.length === 0 ? (
        <EmptyState
          title="No interests yet"
          body="You haven't registered interest in any campaigns yet."
          action={
            <Link to="/portal/leads/new" className="btn btn--primary btn--sm">
              Register Interest
            </Link>
          }
        />
      ) : (
        <div className="portal-interests">
          {/* Table view for larger screens */}
          <table className="data-table portal-interests__table">
            <thead>
              <tr>
                <th>Campaign</th>
                <th>Product Interests</th>
                <th>Status</th>
                <th>Submitted</th>
              </tr>
            </thead>
            <tbody>
              {leads.map(lead => (
                <tr key={lead.id}>
                  <td>
                    <Link to={`/portal/interests/${lead.id}`}>
                      {lead.campaign_name || lead.source_campaign_name || 'General Interest'}
                    </Link>
                  </td>
                  <td>
                    {lead.product_interests?.length > 0
                      ? lead.product_interests.join(', ')
                      : <span className="text-muted">--</span>}
                  </td>
                  <td>
                    <span className={`badge badge--${leadStatusVariant(cleanEnum(lead.status))}`}>
                      {leadStatusLabel(lead.status)}
                    </span>
                  </td>
                  <td>{new Date(lead.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Card view for mobile */}
          <div className="portal-interests__cards">
            {leads.map(lead => (
              <Link
                key={lead.id}
                to={`/portal/interests/${lead.id}`}
                className="portal-interest-card"
              >
                <div className="portal-interest-card__header">
                  <span className="portal-interest-card__name">
                    {lead.campaign_name || lead.source_campaign_name || 'General Interest'}
                  </span>
                  <span className={`badge badge--${leadStatusVariant(cleanEnum(lead.status))}`}>
                    {leadStatusLabel(lead.status)}
                  </span>
                </div>
                <div className="portal-interest-card__body">
                  {lead.product_interests?.length > 0 && (
                    <div className="portal-interest-card__field">
                      <span className="text-muted">Products:</span>{' '}
                      {lead.product_interests.join(', ')}
                    </div>
                  )}
                  <div className="portal-interest-card__field">
                    <span className="text-muted">Submitted:</span>{' '}
                    {new Date(lead.created_at).toLocaleDateString()}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
