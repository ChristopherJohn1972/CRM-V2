import { CUSTOMER_STATUS, STATUS_COLORS } from '../utils/constants';

export function StatusSelect({ value, onChange, id, className, placeholder = 'All statuses' }) {
  return (
    <select
      id={id}
      className={`field__input status-select${className ? ` ${className}` : ''}`}
      value={value}
      onChange={onChange}
    >
      <option value="">{placeholder}</option>
      {Object.entries(CUSTOMER_STATUS).map(([key, label]) => {
        const colors = STATUS_COLORS[key];
        return (
          <option key={key} value={key}>
            {colors ? '● ' : ''}{label}
          </option>
        );
      })}
    </select>
  );
}

export default StatusSelect;