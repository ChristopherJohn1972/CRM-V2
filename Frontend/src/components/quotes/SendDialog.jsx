import { useState } from 'react';
import Modal from '../../components/Modal';
import Button from '../../components/Button';
import Field from '../../components/Field';
import { formatCurrency, formatDate } from '../../utils/format';

function SendDialog({ open, onClose, onConfirm, quote }) {
  const [customerId, setCustomerId] = useState('');
  const [sending, setSending] = useState(false);

  if (!quote) return null;

  const handleConfirm = async () => {
    setSending(true);
    try {
      await onConfirm(customerId ? parseInt(customerId, 10) : undefined);
    } finally {
      setSending(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Send Quote">
      <div className="send-dialog">
        <div className="send-dialog__summary">
          <div className="send-dialog__row">
            <span className="send-dialog__label">Quote</span>
            <span className="send-dialog__value">{quote.quote_number}</span>
          </div>
          {quote.title && (
            <div className="send-dialog__row">
              <span className="send-dialog__label">Title</span>
              <span className="send-dialog__value">{quote.title}</span>
            </div>
          )}
          <div className="send-dialog__row">
            <span className="send-dialog__label">Total</span>
            <span className="send-dialog__value send-dialog__value--strong">
              {formatCurrency(quote.grand_total, quote.currency)}
            </span>
          </div>
          {quote.valid_until && (
            <div className="send-dialog__row">
              <span className="send-dialog__label">Valid Until</span>
              <span className="send-dialog__value">{formatDate(quote.valid_until)}</span>
            </div>
          )}
        </div>

        <Field label="Customer Account ID" htmlFor="send-customer-id" hint="The portal account this quote will be published to.">
          <input
            id="send-customer-id"
            type="number"
            className="field__input"
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            placeholder="Enter customer account ID"
          />
        </Field>

        <div className="send-dialog__notice">
          This will publish the quotation to the client's portal. The client will be able to view, accept, or decline the quote.
        </div>

        <div className="drawer__footer">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={sending} onClick={handleConfirm}>
            Send {quote.quote_number}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default SendDialog;
