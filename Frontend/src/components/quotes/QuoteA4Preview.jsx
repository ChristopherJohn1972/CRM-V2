import { formatCurrency, formatDate, formatDateTime } from '../../utils/format';

const COMPANY = {
  name: 'Curl Stack',
  tagline: 'Decoded Simplicity, Scalable Solutions.',
  address: 'Msa 97356D',
};

function Header() {
  return (
    <div className="a4-header">
      <div className="a4-logo">
        <img src="/curl-stack-logo.jpg" alt="Curl Stack" className="a4-logo__image" />
      </div>
    </div>
  );
}

function QuoteMeta({ quote }) {
  return (
    <div className="a4-meta">
      <div className="a4-meta__item">
        <span className="a4-meta__label">Date</span>
        <span className="a4-meta__value">{formatDate(quote.quote_date || quote.created_at)}</span>
      </div>
      <div className="a4-meta__item">
        <span className="a4-meta__label">Valid Until</span>
        <span className="a4-meta__value">{formatDate(quote.valid_until)}</span>
      </div>
    </div>
  );
}

function CustomerBlock({ customer }) {
  if (!customer) return null;
  const name = customer.legal_name || [customer.first_name, customer.middle_name, customer.last_name].filter(Boolean).join(' ');
  return (
    <div className="a4-customer">
      <div className="a4-customer__label">Prepared For</div>
      <div className="a4-customer__name">{name}</div>
      {customer.email && <div className="a4-customer__detail">{customer.email}</div>}
      {customer.phone && <div className="a4-customer__detail">{customer.phone}</div>}
      {customer.physical_address && <div className="a4-customer__detail">{customer.physical_address}</div>}
    </div>
  );
}

function ItemsTable({ items = [], currency }) {
  if (items.length === 0) return null;
  return (
    <table className="a4-table">
      <thead>
        <tr>
          <th className="a4-table__th-num">#</th>
          <th className="a4-table__th-desc">Description</th>
          <th className="a4-table__th-qty">Qty</th>
          <th className="a4-table__th-price">Unit Price</th>
          <th className="a4-table__th-total">Total</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item, idx) => (
          <tr key={item.item_id || idx}>
            <td className="a4-table__td-num">{idx + 1}</td>
            <td className="a4-table__td-desc">
              <div className="a4-table__desc">{item.description}</div>
              {item.sku && <div className="a4-table__sub">{item.sku}</div>}
              {item.notes && <div className="a4-table__sub">{item.notes}</div>}
            </td>
            <td className="a4-table__td-qty">{item.quantity}</td>
            <td className="a4-table__td-price">{formatCurrency(item.unit_price, currency)}</td>
            <td className="a4-table__td-total">{formatCurrency(item.line_total || (item.quantity * item.unit_price), currency)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Totals({ quote, currency }) {
  const subtotal = quote.subtotal || 0;
  const discount = quote.discount_amount || 0;
  const tax = quote.tax_amount || 0;
  const installation = quote.installation_charge || 0;
  const delivery = quote.delivery_charge || 0;
  const total = quote.grand_total || (subtotal - discount + tax + installation + delivery);

  return (
    <div className="a4-totals">
      <div className="a4-totals__rows">
        <div className="a4-totals__row">
          <span>Subtotal</span>
          <span>{formatCurrency(subtotal, currency)}</span>
        </div>
        {discount > 0 && (
          <div className="a4-totals__row">
            <span>Discount</span>
            <span>-{formatCurrency(discount, currency)}</span>
          </div>
        )}
        {tax > 0 && (
          <div className="a4-totals__row">
            <span>Tax</span>
            <span>{formatCurrency(tax, currency)}</span>
          </div>
        )}
        {installation > 0 && (
          <div className="a4-totals__row">
            <span>Installation</span>
            <span>{formatCurrency(installation, currency)}</span>
          </div>
        )}
        {delivery > 0 && (
          <div className="a4-totals__row">
            <span>Delivery</span>
            <span>{formatCurrency(delivery, currency)}</span>
          </div>
        )}
        <div className="a4-totals__row a4-totals__row--grand">
          <span>TOTAL</span>
          <span>{formatCurrency(total, currency)}</span>
        </div>
      </div>
    </div>
  );
}

function Footer({ quote }) {
  const now = new Date();
  return (
    <div className="a4-footer">
      <div className="a4-footer__full">
        <div className="a4-terms">
          <div className="a4-terms__label">Payment Terms</div>
          <div className="a4-terms__text">To be shared</div>
        </div>
      </div>
      <div className="a4-footer__tracking">
        {quote.quote_number && (
          <div className="a4-quote-num">{quote.quote_number}</div>
        )}
        <div className="a4-generated">Generated {formatDateTime(now)}</div>
      </div>
    </div>
  );
}

export function QuoteA4Preview({ quote, customer, staff, currency = 'KES' }) {
  const items = quote.items || [];

  return (
    <div className="a4-page">
      <div className="a4-page__inner">
        <Header />

        <h1 className="a4-heading">QUOTATION</h1>

        <QuoteMeta quote={quote} />

        <CustomerBlock customer={customer} />

        {quote.title && (
          <div className="a4-title">{quote.title}</div>
        )}

        <ItemsTable items={items} currency={currency} />

        <div className="a4-totals-section">
          <Totals quote={quote} currency={currency} />
        </div>

        <Footer quote={quote} />
      </div>
    </div>
  );
}

export default QuoteA4Preview;
