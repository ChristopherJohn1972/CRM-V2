import { cn } from '../utils/cn';
import Button from './Button';

export function Pagination({ page, pageSize, count, onPageChange, pageSizeOptions, onPageSizeChange }) {
  if (count === 0) return null;
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(count, page * pageSize);

  return (
    <div className="pagination">
      <div className="pagination__info" role="status">
        {from}–{to} of {count}
      </div>
      <div className="pagination__controls">
        {pageSizeOptions && onPageSizeChange && (
          <>
            <label className="sr-only" htmlFor="page-size">Rows per page</label>
            <select
              id="page-size"
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              aria-label="Rows per page"
            >
              {pageSizeOptions.map((n) => <option key={n} value={n}>{n} per page</option>)}
            </select>
          </>
        )}
        <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Previous</Button>
        <span className={cn('cell-monospace')} aria-label={`Page ${page} of ${totalPages}`}>{page} / {totalPages}</span>
        <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>Next</Button>
      </div>
    </div>
  );
}

export default Pagination;