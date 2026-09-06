import { cn } from '../utils/cn';

export function SkeletonTable({ columns = 4, rows = 6, className }) {
  return (
    <div className={cn('table-wrap', className)}>
      <table className="data-table data-table--desktop">
        <thead>
          <tr>
            {Array.from({ length: columns }).map((_, i) => (
              <th key={i}><span className="skeleton skeleton-line" style={{ width: 90, display: 'block' }} /></th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, r) => (
            <tr key={r} className="skeleton-table">
              {Array.from({ length: columns }).map((_, c) => (
                <td key={c}><span className="skeleton skeleton-line" style={{ width: `${60 + (c * 9) % 30}%` }} /></td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default SkeletonTable;