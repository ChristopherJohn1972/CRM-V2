import { initials } from '../utils/format';

export function Avatar({ name, size = 32 }) {
  return (
    <span
      className="avatar"
      style={{ width: size, height: size, fontSize: size < 32 ? 11 : undefined }}
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  );
}

export default Avatar;