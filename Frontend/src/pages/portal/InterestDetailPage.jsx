import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getLead } from '../../api/leads';
import PageHeader from '../../components/PageHeader';
import ErrorState from '../../components/ErrorState';

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

const TIMELINE_STEPS = [
  { key: 'SUBMITTED', label: 'Interest submitted', icon: '📋' },
  { key: 'RECEIVED', label: 'Information received', icon: '✅' },
  { key: 'REVIEWED', label: 'Team reviewed', icon: '🔍' },
  { key: 'FOLLOW_UP', label: 'Follow-up started', icon: '📞' },
  { key: 'COMPLETED', label: 'Purchase completed', icon: '🎉' },
];

function getTimelineStep(status) {
  const key = cleanEnum(status);
  switch (key) {
    case 'NEW':
      return 0;
    case 'QUALIFIED':
      return 2;
    case 'CONTACTED':
      return 3;
    case 'CONVERTED':
      return 4;
    case 'LOST':
    case 'SUPPRESSED':
      return 2;
    default:
      return 0;
  }
}

export default function InterestDetailPage() {
  const { leadId } = useParams();
  const [lead, setLead] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getLead(leadId);
        setLead(data);
      } catch (err) {
        setError(err.message || 'Interest not found');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [leadId]);

  if (loading) {
    return (
      <div className="portal-page">
        <div className="loading-spinner">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="portal-page">
        <ErrorState message={error} />
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="portal-page">
        <ErrorState message="Interest not found" />
      </div>
    );
  }

  const currentStep = getTimelineStep(lead.status);

  return (
    <div className="portal-page">
      <PageHeader
        title={lead.campaign_name || lead.source_campaign_name || 'Interest Detail'}
        breadcrumbs={[
          { to: '/portal/interests', label: 'My Interests' },
          { label: lead.campaign_name || 'Detail' },
        ]}
        actions={
          <Link to="/portal/interests" className="btn btn--secondary">
            Back to My Interests
          </Link>
        }
      />

      <div className="portal-interest-detail">
        {/* Detail Fields */}
        <div className="detail-section">
          <h4>Details</h4>
          <dl className="detail-list">
            <dt>Campaign</dt>
            <dd>{lead.campaign_name || lead.source_campaign_name || 'General Interest'}</dd>

            <dt>Status</dt>
            <dd>
              <span className={`badge badge--${leadStatusVariant(cleanEnum(lead.status))}`}>
                {leadStatusLabel(lead.status)}
              </span>
            </dd>

            <dt>Product Interests</dt>
            <dd>
              {lead.product_interests?.length > 0
                ? lead.product_interests.join(', ')
                : '--'}
            </dd>

            <dt>Use Case</dt>
            <dd>{lead.use_case || '--'}</dd>

            <dt>Submitted</dt>
            <dd>{new Date(lead.created_at).toLocaleDateString()}</dd>
          </dl>
        </div>

        {/* Timeline */}
        <div className="detail-section">
          <h4>Progress</h4>
          <div className="portal-timeline">
            {TIMELINE_STEPS.map((step, index) => {
              const isCompleted = index <= currentStep;
              const isCurrent = index === currentStep;
              return (
                <div
                  key={step.key}
                  className={`portal-timeline__step ${isCompleted ? 'portal-timeline__step--completed' : ''} ${isCurrent ? 'portal-timeline__step--current' : ''}`}
                >
                  <div className="portal-timeline__marker">
                    <span className="portal-timeline__icon">{step.icon}</span>
                    {index < TIMELINE_STEPS.length - 1 && (
                      <div className="portal-timeline__connector" />
                    )}
                  </div>
                  <div className="portal-timeline__content">
                    <div className="portal-timeline__label">{step.label}</div>
                    {isCurrent && (
                      <div className="portal-timeline__badge">
                        <span className="badge badge--info">Current</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
