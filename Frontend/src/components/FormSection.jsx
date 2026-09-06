export function FormSection({ title, description, children }) {
  return (
    <section className="form-section">
      <div className="form-section__header">
        <h3 className="form-section__title">{title}</h3>
        {description && <p className="form-section__desc">{description}</p>}
      </div>
      <div className="form-grid">{children}</div>
    </section>
  );
}

export default FormSection;