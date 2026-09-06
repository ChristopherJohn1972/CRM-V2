import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchPaymentDetail } from '../api/portal';
import { formatCurrency, formatDateTime } from '../utils/format';
import PageHeader from '../components/PageHeader';
import { SkeletonTable } from '../components/Skeleton';
import { ErrorState } from '../components/States';

export function PaymentDetailPage() {
  const { paymentId } = useParams();
  const [payment, setPayment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPaymentDetail(paymentId);
      setPayment(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [paymentId]);

  if (loading) return <div><PageHeader title="Payment Details" /><SkeletonTable rows={3} cols={2} /></div>;
  if (error) return <div><PageHeader title="Payment Details" /><ErrorState detail={error} onRetry={load} /></div>;
  if (!payment) return null;

  return (
    <div>
      <PageHeader title="Payment Details" subtitle={payment.reference}>
        <Link to="/payments" className="btn btn--ghost">Back to Payments</Link>
      </PageHeader>

      <div className="grid-2">
        <div className="card">
          <div className="card__header"><h2 className="card__title">Payment Information</h2></div>
          <div className="card__body">
            <dl className="def-list">
              <dt>Reference</dt><dd className="cell-monospace">{payment.reference}</dd>
              <dt>Date</dt><dd>{formatDateTime(payment.date)}</dd>
              <dt>Amount</dt><dd style={{ fontWeight: 600 }}>KES {formatCurrency(payment.amount)}</dd>
              <dt>Status</dt><dd><span className={`badge badge--${payment.status === 'Confirmed' ? 'success' : 'warning'}`}>{payment.status}</span></dd>
              <dt>Description</dt><dd>{payment.description}</dd>
              <dt>Payment Method</dt><dd>{payment.payment_method}</dd>
              <dt>Bank Reference</dt><dd className="cell-monospace">{payment.bank_reference}</dd>
              <dt>Confirmed</dt><dd>{formatDateTime(payment.confirmed_at)}</dd>
            </dl>
          </div>
        </div>

        <div className="card">
          <div className="card__header"><h2 className="card__title">Timeline</h2></div>
          <div className="card__body">
            <div className="timeline">
              {payment.timeline.map((t, i) => (
                <div key={i} className="timeline-item">
                  <div className={`timeline-item__dot${i === payment.timeline.length - 1 ? '' : ''}`} />
                  <div className="timeline-item__content">
                    <div className="timeline-item__summary">{t.status}</div>
                    <div className="timeline-item__meta">
                      <span>{formatDateTime(t.date)}</span>
                    </div>
                    {t.note && <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: 'var(--space-1)' }}>{t.note}</div>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {payment.has_receipt && (
        <div style={{ marginTop: 'var(--space-6)' }}>
          <button className="btn btn--primary" onClick={() => alert('Receipt download will be available when backend is connected.')}>
            Download Receipt
          </button>
        </div>
      )}
    </div>
  );
}

export default PaymentDetailPage;
