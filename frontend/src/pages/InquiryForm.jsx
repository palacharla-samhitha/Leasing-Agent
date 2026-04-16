import { useEffect, useState } from 'react'
import client from '../api/clients'

function Field({ label, required, children }) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: '#374151', marginBottom: '6px' }}>
        {label} {required && <span style={{ color: '#E24B4A' }}>*</span>}
      </label>
      {children}
    </div>
  )
}

const inputStyle = {
  width: '100%', padding: '9px 12px', fontSize: '13px',
  border: '0.5px solid #E5E7EB', borderRadius: '6px',
  outline: 'none', background: 'white', color: '#374151',
  boxSizing: 'border-box',
}

const CATEGORIES = [
  'Fashion & Premium Retail',
  'Sports & Outdoor',
  'Beauty & Skincare',
  'F&B & Specialty Dining',
  'Electronics & Tech',
  'Kids & Family',
  'Lifestyle & Leisure',
  'General Retail',
]

const QUARTERS = ['Q1', 'Q2', 'Q3', 'Q4']
const YEARS    = ['2026', '2027', '2028']

export default function InquiryForm() {
  const [properties, setProperties] = useState([])
  const [submitted, setSubmitted]   = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError]           = useState(null)
  const [inquiryId, setInquiryId]   = useState(null)

  const [form, setForm] = useState({
    brand_name:         '',
    legal_entity_name:  '',
    contact_name:       '',
    contact_email:      '',
    contact_phone:      '',
    contact_role:       '',
    category:           '',
    preferred_mall:     '',
    preferred_zone:     '',
    size_min_sqm:       '',
    size_max_sqm:       '',
    target_quarter:     'Q4',
    target_year:        '2026',
    first_uae_store:    false,
    channel:            'walk_in',
  })

  useEffect(() => {
    client.get('/properties/', { params: { status: 'active' } })
      .then(res => setProperties(res.data.properties || []))
      .catch(() => {})
  }, [])

  function set(field, value) {
    setForm(f => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)

    if (!form.brand_name || !form.legal_entity_name || !form.category) {
      setError('Please fill in all required fields.')
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        brand_name:        form.brand_name,
        legal_entity_name: form.legal_entity_name,
        contact_name:      form.contact_name || null,
        contact_email:     form.contact_email || null,
        contact_phone:     form.contact_phone || null,
        contact_role:      form.contact_role || null,
        category:          form.category,
        preferred_mall:    form.preferred_mall || null,
        preferred_zone:    form.preferred_zone || null,
        size_min_sqm:      form.size_min_sqm ? parseInt(form.size_min_sqm) : null,
        size_max_sqm:      form.size_max_sqm ? parseInt(form.size_max_sqm) : null,
        target_opening:    `${form.target_quarter} ${form.target_year}`,
        first_uae_store:   form.first_uae_store,
        channel:           'walk_in',
        priority:          'medium',
      }
      const res = await client.post('/inquiries/', payload)
      setInquiryId(res.data.inquiry_id)
      setSubmitted(true)
    } catch (err) {
      setError('Failed to submit inquiry. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  // Success screen
  if (submitted) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', maxWidth: '400px' }}>
          <div style={{ width: '56px', height: '56px', borderRadius: '50%', background: '#E1F5EE', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', fontSize: '24px' }}>
            ✓
          </div>
          <h2 style={{ fontSize: '18px', fontWeight: '500', color: '#0A2342', marginBottom: '8px' }}>
            Inquiry submitted
          </h2>
          <p style={{ fontSize: '13px', color: '#6B7280', marginBottom: '16px', lineHeight: '1.6' }}>
            Thank you for your interest. Our leasing team will review your inquiry and be in touch shortly.
          </p>
          {inquiryId && (
            <div style={{ background: '#F9FAFB', border: '0.5px solid #E5E7EB', borderRadius: '6px', padding: '10px 16px', marginBottom: '20px' }}>
              <span style={{ fontSize: '12px', color: '#9CA3AF' }}>Your reference: </span>
              <span style={{ fontSize: '12px', fontFamily: 'monospace', fontWeight: '500', color: '#0A2342' }}>{inquiryId}</span>
            </div>
          )}
          <button
            onClick={() => { setSubmitted(false); setForm({ brand_name: '', legal_entity_name: '', contact_name: '', contact_email: '', contact_phone: '', contact_role: '', category: '', preferred_mall: '', preferred_zone: '', size_min_sqm: '', size_max_sqm: '', target_quarter: 'Q4', target_year: '2026', first_uae_store: false, channel: 'walk_in' }) }}
            style={{ padding: '9px 20px', fontSize: '13px', background: '#0A2342', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
          >
            Submit another inquiry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: '680px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '18px', fontWeight: '500', color: '#0A2342', marginBottom: '2px' }}>Submit an Inquiry</h1>
        <p style={{ fontSize: '13px', color: '#6B7280' }}>Tell us about your brand and space requirements. Our team will be in touch.</p>
      </div>

      <form onSubmit={handleSubmit}>

        {/* Brand information */}
        <div style={{ background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px', padding: '20px', marginBottom: '16px' }}>
          <div style={{ fontSize: '13px', fontWeight: '500', color: '#0A2342', marginBottom: '16px', paddingBottom: '10px', borderBottom: '0.5px solid #F3F4F6' }}>
            Brand information
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
            <Field label="Brand name" required>
              <input style={inputStyle} value={form.brand_name} onChange={e => set('brand_name', e.target.value)} placeholder="e.g. Summit Gear Co." />
            </Field>
            <Field label="Legal entity name" required>
              <input style={inputStyle} value={form.legal_entity_name} onChange={e => set('legal_entity_name', e.target.value)} placeholder="e.g. Summit Gear Trading LLC" />
            </Field>
          </div>
          <Field label="Retail category" required>
            <select style={inputStyle} value={form.category} onChange={e => set('category', e.target.value)}>
              <option value="">Select a category</option>
              {CATEGORIES.map(c => <option key={c} value={c.toLowerCase()}>{c}</option>)}
            </select>
          </Field>
          <Field label="First UAE store?">
            <div style={{ display: 'flex', gap: '16px', alignItems: 'center', paddingTop: '4px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#374151', cursor: 'pointer' }}>
                <input type="radio" checked={form.first_uae_store === true} onChange={() => set('first_uae_store', true)} /> Yes
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#374151', cursor: 'pointer' }}>
                <input type="radio" checked={form.first_uae_store === false} onChange={() => set('first_uae_store', false)} /> No — we have existing UAE locations
              </label>
            </div>
          </Field>
        </div>

        {/* Contact details */}
        <div style={{ background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px', padding: '20px', marginBottom: '16px' }}>
          <div style={{ fontSize: '13px', fontWeight: '500', color: '#0A2342', marginBottom: '16px', paddingBottom: '10px', borderBottom: '0.5px solid #F3F4F6' }}>
            Contact details
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
            <Field label="Contact name">
              <input style={inputStyle} value={form.contact_name} onChange={e => set('contact_name', e.target.value)} placeholder="Full name" />
            </Field>
            <Field label="Role / title">
              <input style={inputStyle} value={form.contact_role} onChange={e => set('contact_role', e.target.value)} placeholder="e.g. Regional Director" />
            </Field>
            <Field label="Email">
              <input style={inputStyle} type="email" value={form.contact_email} onChange={e => set('contact_email', e.target.value)} placeholder="email@company.com" />
            </Field>
            <Field label="Phone">
              <input style={inputStyle} value={form.contact_phone} onChange={e => set('contact_phone', e.target.value)} placeholder="+971 50 000 0000" />
            </Field>
          </div>
        </div>

        {/* Space requirements */}
        <div style={{ background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px', padding: '20px', marginBottom: '16px' }}>
          <div style={{ fontSize: '13px', fontWeight: '500', color: '#0A2342', marginBottom: '16px', paddingBottom: '10px', borderBottom: '0.5px solid #F3F4F6' }}>
            Space requirements
          </div>
          <Field label="Preferred mall">
            <select style={inputStyle} value={form.preferred_mall} onChange={e => set('preferred_mall', e.target.value)}>
              <option value="">No preference</option>
              {properties.map(p => <option key={p.property_id} value={p.property_id}>{p.name}</option>)}
            </select>
          </Field>
          <Field label="Preferred zone">
            <input style={inputStyle} value={form.preferred_zone} onChange={e => set('preferred_zone', e.target.value)} placeholder="e.g. Sports & Outdoor, Fashion District" />
          </Field>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
            <Field label="Size — minimum (sqm)">
              <input style={inputStyle} type="number" value={form.size_min_sqm} onChange={e => set('size_min_sqm', e.target.value)} placeholder="e.g. 100" />
            </Field>
            <Field label="Size — maximum (sqm)">
              <input style={inputStyle} type="number" value={form.size_max_sqm} onChange={e => set('size_max_sqm', e.target.value)} placeholder="e.g. 300" />
            </Field>
          </div>
          <Field label="Target opening">
            <div style={{ display: 'flex', gap: '8px' }}>
              <select style={{ ...inputStyle, width: 'auto' }} value={form.target_quarter} onChange={e => set('target_quarter', e.target.value)}>
                {QUARTERS.map(q => <option key={q} value={q}>{q}</option>)}
              </select>
              <select style={{ ...inputStyle, width: 'auto' }} value={form.target_year} onChange={e => set('target_year', e.target.value)}>
                {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
          </Field>
        </div>

        {error && (
          <div style={{ background: '#FCEBEB', border: '0.5px solid #F7C1C1', borderRadius: '8px', padding: '12px 16px', color: '#A32D2D', fontSize: '13px', marginBottom: '16px' }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            type="submit"
            disabled={submitting}
            style={{
              padding: '10px 28px', fontSize: '14px', fontWeight: '500',
              background: submitting ? '#9CA3AF' : '#0A2342',
              color: 'white', border: 'none', borderRadius: '6px',
              cursor: submitting ? 'default' : 'pointer',
            }}
          >
            {submitting ? 'Submitting...' : 'Submit inquiry'}
          </button>
        </div>
      </form>
    </div>
  )
}
