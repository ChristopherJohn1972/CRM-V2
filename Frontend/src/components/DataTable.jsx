import { cn } from '../utils/cn';
import EmptyState from './EmptyState';
import ErrorState from './ErrorState';
import SkeletonTable from './SkeletonTable';

/**
 * Desktop data table. Pass a `columns` array of { key, header, render, className }
 * and a `rows` array. `keyField` identifies rows for React keys.
 * Responsive behaviour is handled by the parent page (mobile card list).
 */
export function DataTable({ columns, rows = [], keyField = 'id', loading = false, error, onRetry, emptyTitle, emptyBody, emptyAction }) {
  if (loading) return <SkeletonTable columns={columns.length} rows={6} />;

  if (error) {
    return <ErrorState title={error.title || 'Unable to load this data'} body={error.message} onRetry={onRetry} />;
  }

  if (rows.length === 0) {
    return <EmptyState title={emptyTitle || 'No records yet'} body={emptyBody} action={emptyAction} />;
  }

  return (
    <div className="table-wrap">
      <table className="data-table data-table--desktop">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} scope="col">{col.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={row[keyField] ?? rowIndex}>
              {columns.map((col) => (
                <td key={col.key} className={cn(col.className)}>
                  {col.render ? col.render(row) : String(row[col.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default DataTable;