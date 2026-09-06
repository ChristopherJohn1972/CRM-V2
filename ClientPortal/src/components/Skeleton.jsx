export function SkeletonTable({ rows = 5, cols = 4 }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {Array.from({ length: cols }, (_, i) => (
              <th key={i}><div className="skeleton skeleton-line" style={{ width: '60%' }} /></th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }, (_, r) => (
            <tr key={r}>
              {Array.from({ length: cols }, (_, c) => (
                <td key={c}><div className="skeleton skeleton-line" style={{ width: `${50 + Math.random() * 40}%` }} /></td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SkeletonCards({ count = 4 }) {
  return (
    <div className="dashboard-grid">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="dashboard-card">
          <div className="skeleton skeleton-line" style={{ width: '40%' }} />
          <div className="skeleton skeleton-line" style={{ width: '60%', height: 24, marginTop: 8 }} />
        </div>
      ))}
    </div>
  );
}

export default SkeletonTable;
