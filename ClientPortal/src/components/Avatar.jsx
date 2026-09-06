export function Avatar({ name, size = 32 }) {
  const initials = (name || '?')
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
  return (
    <span className="avatar" style={{ width: size, height: size, fontSize: size * 0.375 }}>
      {initials}
    </span>
  );
}

export default Avatar;
