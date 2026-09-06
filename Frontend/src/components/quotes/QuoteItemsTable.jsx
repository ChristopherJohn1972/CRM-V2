import { formatCurrency } from '../../utils/format';

const ITEM_TYPE_LABELS = {
  PRODUCT: 'Product',
  SERVICE: 'Service',
  PROJECT: 'Project',
  CUSTOM: 'Custom',
};

function QuoteItemsTable({ items = [], currency = 'KES', canEdit = false, onEdit, onRemove, onDuplicate }) {
  if (items.length === 0) {
    return (
      <div className="quote-items-empty">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="quote-items-empty__icon">
          <rect x="8" y="8" width="32" height="32" rx="4" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" />
          <path d="M24 18v12M18 24h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <p className="quote-items-empty__title">No items added yet</p>
        {canEdit && <p className="quote-items-empty__hint">Click "Add Item" to add your first line item.</p>}
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table className="data-table data-table--desktop quote-items-table">
        <thead>
          <tr>
            <th style={{ width: 40 }}>#</th>
            <th>Item</th>
            <th style={{ width: 100 }}>SKU/Code</th>
            <th style={{ width: 70 }}>Qty</th>
            <th style={{ width: 70 }}>Unit</th>
            <th style={{ width: 110 }}>Unit Price</th>
            <th style={{ width: 100 }}>Discount</th>
            <th style={{ width: 100 }}>Tax</th>
            <th style={{ width: 110, textAlign: 'right' }}>Line Total</th>
            {canEdit && <th style={{ width: 100 }}>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={item.item_id} className="quote-items-table__row">
              <td className="cell-secondary">{idx + 1}</td>
              <td>
                <div className="quote-items-table__item">
                  <span className="quote-items-table__desc">{item.description}</span>
                  {item.item_type && item.item_type !== 'CUSTOM' && (
                    <span className="badge badge--neutral quote-items-table__type">{ITEM_TYPE_LABELS[item.item_type] || item.item_type}</span>
                  )}
                </div>
                {item.notes && (
                  <div className="quote-items-table__notes cell-secondary">{item.notes}</div>
                )}
              </td>
              <td className="cell-secondary">{item.sku || '—'}</td>
              <td>{item.quantity}</td>
              <td className="cell-secondary">{item.unit_of_measure || '—'}</td>
              <td>{formatCurrency(item.unit_price, currency)}</td>
              <td>
                {item.discount_amount > 0 ? (
                  <span className="quote-items-table__discount">
                    {item.discount_type === 'PERCENTAGE' ? `${item.discount_value}%` : `−${formatCurrency(item.discount_amount, currency)}`}
                  </span>
                ) : '—'}
              </td>
              <td>
                {item.tax_amount > 0 ? (
                  <span className="quote-items-table__tax">
                    {item.tax_code && <span className="quote-items-table__tax-code">{item.tax_code}</span>}
                    {formatCurrency(item.tax_amount, currency)}
                  </span>
                ) : '—'}
              </td>
              <td style={{ textAlign: 'right', fontWeight: 600 }}>{formatCurrency(item.line_total, currency)}</td>
              {canEdit && (
                <td>
                  <div className="quote-items-table__actions">
                    <button type="button" className="icon-btn icon-btn--edit" onClick={() => onEdit(item)} title="Edit">
                      <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M11.5 1.5l3 3-9 9H2.5v-3l9-9z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    </button>
                    <button type="button" className="icon-btn" onClick={() => onDuplicate?.(item)} title="Duplicate">
                      <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="5" y="5" width="9" height="9" rx="1" stroke="currentColor" strokeWidth="1.5" /><path d="M11 5V3.5A1.5 1.5 0 009.5 2h-6A1.5 1.5 0 002 3.5v6A1.5 1.5 0 003.5 11H5" stroke="currentColor" strokeWidth="1.5" /></svg>
                    </button>
                    <button type="button" className="icon-btn icon-btn--delete" onClick={() => onRemove(item.item_id)} title="Remove">
                      <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M5.333 4V2.667a1.333 1.333 0 011.334-1.334h2.666a1.333 1.333 0 011.334 1.334V4m2 0v9.333a1.333 1.333 0 01-1.334 1.334H4.667a1.333 1.333 0 01-1.334-1.334V4h9.334z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    </button>
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Mobile items */}
      <div className="quote-items-mobile">
        {items.map((item, idx) => (
          <div key={item.item_id} className="quote-item-card">
            <div className="quote-item-card__header">
              <span className="quote-item-card__num">{idx + 1}</span>
              <div className="quote-item-card__info">
                <span className="quote-item-card__desc">{item.description}</span>
                {item.item_type && item.item_type !== 'CUSTOM' && (
                  <span className="badge badge--neutral">{ITEM_TYPE_LABELS[item.item_type] || item.item_type}</span>
                )}
              </div>
            </div>
            {item.sku && <div className="quote-item-card__meta">SKU: {item.sku}</div>}
            <div className="quote-item-card__details">
              <span>Qty: {item.quantity}{item.unit_of_measure ? ` ${item.unit_of_measure}` : ''}</span>
              <span>Price: {formatCurrency(item.unit_price, currency)}</span>
              {item.discount_amount > 0 && (
                <span className="quote-item-card__discount">
                  Discount: −{formatCurrency(item.discount_amount, currency)}
                </span>
              )}
            </div>
            <div className="quote-item-card__total">
              <span>Total</span>
              <span style={{ fontWeight: 600 }}>{formatCurrency(item.line_total, currency)}</span>
            </div>
            {canEdit && (
              <div className="quote-item-card__actions">
                <button type="button" className="icon-btn icon-btn--edit" onClick={() => onEdit(item)} title="Edit">
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M11.5 1.5l3 3-9 9H2.5v-3l9-9z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </button>
                <button type="button" className="icon-btn" onClick={() => onDuplicate?.(item)} title="Duplicate">
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="5" y="5" width="9" height="9" rx="1" stroke="currentColor" strokeWidth="1.5" /><path d="M11 5V3.5A1.5 1.5 0 009.5 2h-6A1.5 1.5 0 002 3.5v6A1.5 1.5 0 003.5 11H5" stroke="currentColor" strokeWidth="1.5" /></svg>
                </button>
                <button type="button" className="icon-btn icon-btn--delete" onClick={() => onRemove(item.item_id)} title="Remove">
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M5.333 4V2.667a1.333 1.333 0 011.334-1.334h2.666a1.333 1.333 0 011.334 1.334V4m2 0v9.333a1.333 1.333 0 01-1.334 1.334H4.667a1.333 1.333 0 01-1.334-1.334V4h9.334z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default QuoteItemsTable;
