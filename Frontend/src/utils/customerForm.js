/**
 * Pure create-form model for the Client module.
 * Deliberately excludes fields the backend contract no longer accepts:
 * display name, address_line_1/2, state/province, and the Assignment
 * section (assigned user / team / branch). The account number is never part
 * of this model — it is generated and returned by the backend.
 */
export const EMPTY_CUSTOMER_FORM = {
  customer_type: 'BUSINESS',
  first_name: '',
  middle_name: '',
  last_name: '',
  legal_name: '',
  email: '',
  phone: '',
  customer_category: '',
  segment: '',
  industry: '',
  registration_number: '',
  tax_identifier: '',
  address_type: 'OFFICE',
  address: '',
  city: '',
  postal_code: '',
  country: '',
  is_primary: true,
};

export function buildCustomerCreatePayload(form) {
  const payload = {
    customer_type: form.customer_type,
    first_name: form.first_name.trim() || null,
    middle_name: form.middle_name.trim() || null,
    last_name: form.last_name.trim() || null,
    legal_name: form.legal_name.trim() || null,
    email: form.email.trim() || null,
    phone: form.phone.trim() || null,
    customer_category: form.customer_category.trim() || null,
    segment: form.segment.trim() || null,
    industry: form.industry.trim() || null,
    registration_number: form.registration_number.trim() || null,
    tax_identifier: form.tax_identifier.trim() || null,
    addresses: [],
  };

  if (form.address.trim()) {
    payload.addresses.push({
      address_type: form.address_type,
      address: form.address.trim(),
      city: form.city.trim() || null,
      postal_code: form.postal_code.trim() || null,
      country: form.country.trim() || null,
      is_primary: form.is_primary,
    });
  }

  return payload;
}

export function validateCustomerForm(form) {
  const problems = {};
  if (form.customer_type === 'INDIVIDUAL') {
    if (!form.first_name.trim() && !form.legal_name.trim()) {
      problems.first_name = 'Individual customers require a first name or legal name.';
    }
  } else if (!form.legal_name.trim()) {
    problems.legal_name = 'Legal name is required.';
  }
  return problems;
}

export function buildAddressForm(address = {}) {
  return {
    address_type: address.address_type || 'OFFICE',
    address: address.address || '',
    city: address.city || '',
    postal_code: address.postal_code || '',
    country: address.country || '',
    is_primary: Boolean(address.is_primary),
  };
}

export function buildAddressPayload(form) {
  return {
    address_type: form.address_type,
    address: form.address.trim(),
    city: form.city.trim() || null,
    postal_code: form.postal_code.trim() || null,
    country: form.country.trim() || null,
    is_primary: form.is_primary,
  };
}