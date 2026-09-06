import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getLead, updateLead, transitionLead, listLeadFollowUps, createLeadFollowUp, completeLeadFollowUp } from '../../api/leads';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import ErrorState from '../../components/ErrorState';
import { formatEnumLabel } from '../../utils/format';

const STATUS_TRANSITIONS = {
  NEW: ['CONTACTED', 'UNQUALIFIED', 'LOST', 'DISQUALIFIED'],
  CONTACTED: ['QUALIFIED', 'UNQUALIFIED', 'LOST', 'DISQUALIFIED'],
  QUALIFIED: ['CONVERTED', 'LOST', 'DISQUALIFIED'],
  UNQUALIFIED: [],
  CONVERTED: [],
  LOST: [],
  DISQUALIFIED: [],
};

export default function LeadDetailPage() {
  const { leadId } = useParams();
  const navigate = useNavigate();
  const [lead, setLead] = useState(null);
  const [followUps, setFollowUps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [transitioning, setTransitioning] = useState(false);
  const [showFollowUpForm, setShowFollowUpForm] = useState(false);
  const [followUpForm, setFollowUpForm] = useState({ follow_up_type: 'CALL', scheduled_at: '', notes: '' });

  useEffect(() => { loadLead(); }, [leadId]);

  async function loadLead() {
    setLoading(true);
    setError(null);
    try {
      const [l, fuData] = await Promise.all([
        getLead(leadId),
        listLeadFollowUps(leadId).catch(() => ({ results: [] })),
      ]);
      setLead(l);
      setFollowUps(fuData.results || []);
    } catch (err) {
      setError(err.message || 'Failed to load lead');
    } finally {
      setLoading(false);
    }
  }

  async function handleTransition(newStatus) {
    if (!confirm(`Transition lead to ${newStatus}?`)) return;
    setTransitioning(true);
    try {
      await transitionLead(leadId, { status: newStatus });
      await loadLead();
    } catch (err) {
      alert(err.message || 'Failed to transition lead');
    } finally {
      setTransitioning(false);
    }
  }

  async function handleCreateFollowUp(e) {
    e.preventDefault();
    try {
      await createLeadFollowUp(leadId, followUpForm);
      setShowFollowUpForm(false);
      setFollowUpForm({ follow_up_type: 'CALL', scheduled_at: '', notes: '' });
      await loadLead();
    } catch (err) {
      alert(err.message || 'Failed to create follow-up');
    }
  }

  if (loading) return <div className="page"><div className="loading-spinner">Loading...</div></div>;
  if (error) return <div className="page"><ErrorState message={error} onRetry={loadLead} /></div>;
  if (!lead) return <div className="page"><ErrorState message="Lead not found" /></div>;

  const allowedTransitions = STATUS_TRANSITIONS[lead.status] || [];

  return (
    <div className="page">
      <PageHeader
        title={[lead.first_name, lead.last_name].filter(Boolean).join(' ') || 'Unnamed Lead'}
        subtitle={
          <span>
            <StatusBadge status={lead.status}>{formatEnumLabel(lead.status)}</StatusBadge>
            {lead.company && <span style={{ marginLeft: 8 }}>{lead.company}</span>}
          </span>
        }
        actions={
          <div className="page-header__actions">
            <Link to="/leads" className="btn btn--secondary">Back to Leads</Link>
            {allowedTransitions.map(s => (
              <button
                key={s}
                className={`btn ${s === 'QUALIFIED' || s === 'CONVERTED' ? 'btn--primary' : 'btn--secondary'}`}
                disabled={transitioning}
                onClick={() => handleTransition(s)}
              >
                {s}
              </button>
            ))}
          </div>
        }
      />

      <div className="lead-detail">
        <div className="lead-detail__tabs">
          {['overview', 'follow-ups', 'timeline'].map(tab => (
            <button
              key={tab}
              className={`tab ${activeTab === tab ? 'is-active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        <div className="lead-detail__content">
          {activeTab === 'overview' && (
            <div className="lead-overview">
              <div className="detail-section">
                <h4>Contact Information</h4>
                <dl className="detail-list">
                  <dt>Email</dt>
                  <dd>{lead.email || '--'}</dd>
                  <dt>Phone</dt>
                  <dd>{lead.phone || '--'}</dd>
                  <dt>Company</dt>
                  <dd>{lead.company || '--'}</dd>
                  <dt>Source</dt>
                  <dd>{lead.source_channel || '--'}</dd>
                  <dt>Campaign</dt>
                  <dd>{lead.source_campaign_id ? `Campaign #${lead.source_campaign_id}` : '--'}</dd>
                </dl>
              </div>

              <div className="detail-section">
                <h4>Qualification</h4>
                <dl className="detail-list">
                  <dt>Score</dt>
                  <dd>{lead.qualification_score ?? 'Not scored'}</dd>
                  <dt>Consent</dt>
                  <dd>{lead.consent_given ? 'Given' : 'Not given'}</dd>
                  <dt>Created</dt>
                  <dd>{new Date(lead.created_at).toLocaleString()}</dd>
                  <dt>Last Updated</dt>
                  <dd>{new Date(lead.updated_at).toLocaleString()}</dd>
                </dl>
              </div>

              {lead.notes && (
                <div className="detail-section">
                  <h4>Notes</h4>
                  <p>{lead.notes}</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'follow-ups' && (
            <div className="lead-follow-ups">
              <div className="table-wrap__header">
                <h3>Follow-ups</h3>
                <button className="btn btn--primary btn--sm" onClick={() => setShowFollowUpForm(true)}>
                  + New Follow-up
                </button>
              </div>

              {showFollowUpForm && (
                <form onSubmit={handleCreateFollowUp} className="form-inline">
                  <div className="field">
                    <label className="field__label">Type</label>
                    <select className="field__input" value={followUpForm.follow_up_type} onChange={(e) => setFollowUpForm(p => ({ ...p, follow_up_type: e.target.value }))}>
                      <option value="CALL">Call</option>
                      <option value="EMAIL">Email</option>
                      <option value="MEETING">Meeting</option>
                      <option value="SMS">SMS</option>
                    </select>
                  </div>
                  <div className="field">
                    <label className="field__label">Scheduled At</label>
                    <input className="field__input" type="datetime-local" value={followUpForm.scheduled_at} onChange={(e) => setFollowUpForm(p => ({ ...p, scheduled_at: e.target.value }))} />
                  </div>
                  <div className="field">
                    <label className="field__label">Notes</label>
                    <input className="field__input" value={followUpForm.notes} onChange={(e) => setFollowUpForm(p => ({ ...p, notes: e.target.value }))} />
                  </div>
                  <div className="form-actions">
                    <button type="button" className="btn btn--secondary btn--sm" onClick={() => setShowFollowUpForm(false)}>Cancel</button>
                    <button type="submit" className="btn btn--primary btn--sm">Create</button>
                  </div>
                </form>
              )}

              <table className="data-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Scheduled</th>
                    <th>Completed</th>
                    <th>Outcome</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {followUps.length === 0 ? (
                    <tr><td colSpan="5" className="data-table__empty">No follow-ups yet</td></tr>
                  ) : followUps.map(fu => (
                    <tr key={fu.id}>
                      <td>{fu.follow_up_type}</td>
                      <td>{new Date(fu.scheduled_at).toLocaleString()}</td>
                      <td>{fu.completed_at ? new Date(fu.completed_at).toLocaleString() : '--'}</td>
                      <td>{fu.outcome || '--'}</td>
                      <td>{fu.notes || '--'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'timeline' && (
            <div className="lead-timeline">
              <div className="timeline">
                <div className="timeline-item">
                  <div className="timeline-item__dot timeline-item__dot--info" />
                  <div className="timeline-item__content">
                    <div className="timeline-item__title">Lead created</div>
                    <div className="timeline-item__time">{new Date(lead.created_at).toLocaleString()}</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
