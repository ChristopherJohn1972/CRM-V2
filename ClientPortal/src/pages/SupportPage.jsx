import { useState, useEffect } from 'react';
import { fetchFaqs, submitSupportRequest } from '../api/portal';
import PageHeader from '../components/PageHeader';
import Button from '../components/Button';
import Field from '../components/Field';
import { SkeletonCards } from '../components/Skeleton';
import { ErrorState, EmptyState } from '../components/States';
import { useToast } from '../components/Toast';

export function SupportPage() {
  const [faqs, setFaqs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedFaq, setExpandedFaq] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const toast = useToast();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchFaqs();
      setFaqs(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!subject.trim() || !message.trim()) return;
    setSubmitting(true);
    try {
      await submitSupportRequest({ subject: subject.trim(), message: message.trim() });
      toast.success('Support request submitted. We will get back to you shortly.');
      setShowForm(false);
      setSubject('');
      setMessage('');
    } catch (err) {
      toast.error(err.message || 'Failed to submit request.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <PageHeader title="Support" subtitle="Help and contact information" />

      <div className="grid-2">
        {/* FAQs */}
        <div className="card">
          <div className="card__header"><h2 className="card__title">Frequently Asked Questions</h2></div>
          <div className="card__body" style={{ padding: 0 }}>
            {loading && <div style={{ padding: 'var(--space-5)' }}><SkeletonCards count={3} /></div>}
            {error && <div style={{ padding: 'var(--space-5)' }}><ErrorState detail={error} /></div>}
            {!loading && !error && faqs.length === 0 && (
              <EmptyState title="No FAQs available" body="FAQs will appear here once configured." />
            )}
            {!loading && !error && faqs.map((faq) => (
              <div key={faq.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                <button
                  onClick={() => setExpandedFaq(expandedFaq === faq.id ? null : faq.id)}
                  style={{
                    width: '100%', padding: 'var(--space-4) var(--space-5)', border: 0, background: 'none',
                    textAlign: 'left', cursor: 'pointer', fontWeight: 500, fontSize: 'var(--text-sm)',
                    color: 'var(--color-text)', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  }}
                >
                  {faq.question}
                  <span style={{ color: 'var(--color-text-muted)', transform: expandedFaq === faq.id ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M3 5l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
                  </span>
                </button>
                {expandedFaq === faq.id && (
                  <div style={{ padding: '0 var(--space-5) var(--space-4)', fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
                    {faq.answer}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Contact & Service Request */}
        <div>
          {/* Contact Info */}
          <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
            <div className="card__header"><h2 className="card__title">Contact Us</h2></div>
            <div className="card__body">
              <dl className="def-list">
                <dt>Email</dt><dd>support@portal.com</dd>
                <dt>Phone</dt><dd>+254 800 123 456</dd>
                <dt>Hours</dt><dd>Mon - Fri, 8:00 AM - 5:00 PM</dd>
              </dl>
              <div style={{ marginTop: 'var(--space-4)', padding: 'var(--space-3)', background: 'var(--color-danger-subtle)', borderRadius: 'var(--radius-md)', fontSize: 'var(--text-xs)', color: 'var(--color-danger)' }}>
                <strong>Emergency?</strong> Call our 24/7 hotline at +254 800 999 000
              </div>
            </div>
          </div>

          {/* Service Request */}
          <div className="card">
            <div className="card__header">
              <h2 className="card__title">Service Request</h2>
              {!showForm && <Button variant="primary" size="sm" onClick={() => setShowForm(true)}>New Request</Button>}
            </div>
            <div className="card__body">
              {showForm ? (
                <form className="form" onSubmit={handleSubmit} noValidate>
                  <Field label="Subject" required htmlFor="sup-subject">
                    <input id="sup-subject" className="field__input" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Brief description" />
                  </Field>
                  <Field label="Message" required htmlFor="sup-message">
                    <textarea id="sup-message" className="field__input" rows={4} value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Describe your request..." />
                  </Field>
                  <div className="form-actions">
                    <Button type="button" variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
                    <Button type="submit" variant="primary" loading={submitting} disabled={!subject.trim() || !message.trim()}>Submit</Button>
                  </div>
                </form>
              ) : (
                <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)' }}>
                  Need help? Submit a service request and our team will respond within 24 hours.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SupportPage;
