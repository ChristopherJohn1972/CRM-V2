import Button from '../Button';
import { formatCurrency } from '../../utils/format';

export function SalesOrderItemsTable({ items = [], currency = 'KES', canEdit = false, onEdit, onRemove }) {
  if (items.length === 0) {
    return (
      <div className="quote-items-empty">
        <p>No items added yet.</p>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th style={{ width: 40 }}>#</th>
            <th>Description</th>
            <th style={{ textAlign: 'right' }}>Qty</th>
            <th style={{ textAlign: 'right' }}>Unit Price</th>
            <th style={{ textAlign: 'right' }}>Discount</th>
            <th style={{ textAlign: 'right' }}>Tax</th>
            <th style={{ textAlign: 'right' }}>Total</th>
            {canEdit && <th style={{ width: 100 }}></th>}
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={item.item_id}>
              <td className="cell-secondary">{idx + 1}</td>
              <td>
                <span style={{ fontWeight: 500 }}>{item.description}</span>
                {item.sku && <span className="cell-secondary" style={{ marginLeft: 8 }}>{item.sku}</span>}
              </td>
              <td style={{ textAlign: 'right' }}>{item.quantity}</td>
              <td style={{ textAlign: 'right' }}>{formatCurrency(item.unit_price, currency)}</td>
              <td style={{ textAlign: 'right' }}>
                {item.discount_amount > 0 ? `-${formatCurrency(item.discount_amount, currency)}` : '—'}
              </td>
              <td style={{ textAlign: 'right' }}>
                {item.tax_amount > 0 ? formatCurrency(item.tax_amount, currency) : '—'}
              </td>
              <td style={{ textAlign: 'right', fontWeight: 600 }}>{formatCurrency(item.line_total, currency)}</td>
              {canEdit && (
                <td>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <Button variant="ghost" size="sm" onClick={() => onEdit(item)}>Edit</Button>
                    <Button variant="ghost" size="sm" onClick={() => onRemove(item.item_id)}>Remove</Button>
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default SalesOrderItemsTable;
