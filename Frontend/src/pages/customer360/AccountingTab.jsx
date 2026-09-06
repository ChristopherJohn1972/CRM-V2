import { useCallback, useEffect, useState } from 'react';
import { getAccountingSummary, getAccountingTransactions } from '../../api/customers';
import StatusBadge from '../../components/StatusBadge';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import SkeletonTable from '../../components/SkeletonTable';
import RestrictedBanner from '../../components/RestrictedBanner';
import Pagination from '../../components/Pagination';
import { formatDateTime } from '../../utils/format';

function currency(value) {
  if (value === null || value === undefined || value === '') return '—';
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString(undefined, { style: 'currency', currency: 'KES', maximumFractionDigits: 2 });
}

export function AccountingTab({ customerId }) {
  const [summary, setSummary] = useState(null);
  const [summaryState, setSummaryState] = useState('loading');

  const [tx, setTx] = useState([]);
  const [txState, setTxState] = useState('idle');
  const [txTotal, setTxTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const loadSummary = useCallback(async () => {
    setSummaryState('loading');
    try {
      const res = await getAccountingSummary(customerId);
      setSummary(res);
      setSummaryState(res.available ? 'ready' : 'unavailable');
    } catch (err) {
      setSummaryState('error');
    }
  }, [customerId]);

  const loadTransactions = useCallback(async () => {
    setTxState('loading');
    try {
      const res = await getAccountingTransactions(customerId, { page, page_size: pageSize });
      if (res.available) {
        const payload = res.data || {};
        const results = Array.isArray(payload.results) ? payload.results : Array.isArray(payload.items) ? payload.items : payload.list || [];
        setTx(results);
        setTxTotal(payload.count ?? results.length);
        setTxState('ready');
      } else {
        setTx([]);
        setTxTotal(0);
        setTxState('unavailable');
      }
    } catch (err) {
      setTxState('error');
    }
  }, [customerId, page]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  useEffect(() => {
    if (summaryState !== 'ready') return;
    loadTransactions();
  }, [loadTransactions, summaryState]);

  const summaryData = summary?.data || {};

  return (
    <div className="form" style={{ gap: 20 }}>
      <RestrictedBanner>
        Accounting is a separate source-of-truth module. This view is read-only inside the CRM;
        posting, reversing and reconciling happen in the Accounting module.
      </RestrictedBanner>

      {summaryState === 'loading' && <SkeletonTable columns={3} rows={4} />}
      {summaryState === 'error' && <ErrorState title="Accounting data is unavailable" body="The accounting module could not be reached. Please retry shortly." />}
      {summaryState === 'unavailable' && (
        <div className="muted-banner">
          {summary?.reason === 'accounting_error' ? 'Financial data could not be loaded from the accounting module.' : (summary?.message || 'Financial data could not be loaded from the accounting module.')}
        </div>
      )}
      {summaryState === 'ready' && (
        <>
          <div className="grid-2">
            <section className="card">
              <div className="card__header"><h2 className="card__title">Financial summary</h2></div>
              <div className="card__body">
                <dl className="def-list">
                  <dt>Current balance</dt>
                  <dd><b>{currency(summaryData.current_balance ?? summaryData.balance)}</b></dd>
                  <dt>Total paid</dt>
                  <dd>{currency(summaryData.total_paid ?? summaryData.total_received)}</dd>
                  <dt>Outstanding</dt>
                  <dd>{currency(summaryData.outstanding ?? summaryData.amount_due)}</dd>
                  <dt>Last transaction</dt>
                  <dd>{summaryData.last_transaction_at ? formatDateTime(summaryData.last_transaction_at) : '—'}</dd>
                </dl>
              </div>
            </section>
            <section className="card">
              <div className="card__header"><h2 className="card__title">Notes</h2></div>
              <div className="card__body">
                <p className="field__hint">
                  Transaction detail here is read-only for most CRM users. Refer to the
                  Accounting module for posting, reconciliation and approval workflows.
                </p>
              </div>
            </section>
          </div>

          <section className="card">
            <div className="card__header">
              <h2 className="card__title">Recent transactions</h2>
            </div>
            <div className="card__body">
              {txState === 'loading' && <p className="field__hint">Loading transactions…</p>}
              {txState === 'error' && <ErrorState title="Could not load transactions" />}
              {txState === 'ready' && tx.length === 0 && (
                <EmptyState title="No transactions" body="Recent transactions for this customer will appear here." />
              )}
              {txState === 'ready' && tx.length > 0 && (
                <div className="table-wrap">
                  <table className="data-table data-table--desktop">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Type</th>
                        <th>Method</th>
                        <th>Reference</th>
                        <th>Amount</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tx.map((t, i) => (
                        <tr key={t.transaction_id ?? t.reference ?? i}>
                          <td className="cell-nowrap">{formatDateTime(t.transaction_date ?? t.date ?? t.created_at)}</td>
                          <td><span className="cell-secondary">{t.type ?? t.transaction_type ?? '—'}</span></td>
                          <td><span className="cell-secondary">{t.method ?? t.payment_method ?? '—'}</span></td>
                          <td className="cell-monospace cell-nowrap">{t.reference ?? t.transaction_code ?? '—'}</td>
                          <td className="cell-nowrap" style={{ fontWeight: 500 }}>{currency(t.amount)}</td>
                          <td>{t.status ? <StatusBadge variant={t.status === 'COMPLETED' || t.status === 'SUCCESS' ? 'success' : t.status === 'FAILED' || t.status === 'REVERSED' ? 'danger' : 'neutral'} dot={false}>{t.status}</StatusBadge> : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
            {txState === 'ready' && txTotal > pageSize && (
              <div className="table-wrap" style={{ borderLeft: 0, borderRight: 0, borderBottom: 0, borderTop: `1px solid var(--color-border)`, borderRadius: 0 }}>
                <Pagination page={page} pageSize={pageSize} count={txTotal} onPageChange={setPage} />
              </div>
            )}
          </section>
        </>
      )}

      <p className="field__hint" style={{ fontSize: 12 }}>
        M-Pesa transaction codes, bank transfer references and receipt numbers come directly from the accounting module.
      </p>
    </div>
  );
}

export default AccountingTab;