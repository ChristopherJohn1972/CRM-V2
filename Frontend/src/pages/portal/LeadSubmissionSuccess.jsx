import { Link, useSearchParams } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';

export default function LeadSubmissionSuccess() {
  const [searchParams] = useSearchParams();
  const campaignId = searchParams.get('campaign');
  const campaignName = searchParams.get('campaign_name') || '';

  return (
    <div className="portal-page">
      <PageHeader title="Interest Submitted" />

      <div className="portal-success">
        <div className="portal-success__icon">
          <svg
            width="64"
            height="64"
            viewBox="0 0 64 64"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <circle cx="32" cy="32" r="32" fill="#22c55e" />
            <path
              d="M20 32l8 8 16-16"
              stroke="#fff"
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        <h2 className="portal-success__headline">You're all set</h2>

        <div className="portal-success__summary">
          <p>
            Your interest{campaignName ? <> in <strong>{campaignName}</strong></> : ''} has been
            submitted successfully. Our team will review your details and get back to
            you shortly.
          </p>
        </div>

        <div className="portal-success__next-steps">
          <h3>What happens next?</h3>
          <ol>
            <li>Our team receives your submission</li>
            <li>We review your requirements</li>
            <li>A specialist will reach out to discuss your needs</li>
          </ol>
        </div>

        <div className="portal-success__actions">
          <Link
            to={campaignId ? `/portal/campaigns/${campaignId}` : '/portal/campaigns'}
            className="btn btn--secondary"
          >
            {campaignName ? `Back to ${campaignName}` : 'Back to Campaigns'}
          </Link>
          <Link to="/portal/referrals" className="btn btn--primary">
            Refer a Friend
          </Link>
        </div>
      </div>
    </div>
  );
}
