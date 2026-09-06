export function RestrictedBanner({ children }) {
  return <div className="restricted-banner">{children || 'This information is restricted.'}</div>;
}

export default RestrictedBanner;