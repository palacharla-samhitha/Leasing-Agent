// src/pages/NewInquiry.jsx
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { inquiriesApi, propertiesApi } from "../services/api";
import { PageHeader, Button } from "../components/ui";
import "./NewInquiry.css";

const CHANNELS   = ["partner_connect", "broker_portal", "whatsapp", "walk_in", "email"];
const PRIORITIES = ["high", "medium", "low"];
const CATEGORIES = [
  "premium outdoor & adventure gear",
  "specialty coffee & wellness cafe",
  "premium skincare & beauty retail",
  "childrens toys, apparel & play",
  "fashion & premium retail",
  "sports & outdoor",
  "f&b & dining",
  "lifestyle & family",
  "electronics & technology",
  "home & furniture",
  "other",
];
const TARGET_OPENINGS = ["Q1 2026", "Q2 2026", "Q3 2026", "Q4 2026", "Q1 2027", "Q2 2027"];

const INITIAL = {
  brand_name:        "",
  legal_entity_name: "",
  channel:           "partner_connect",
  category:          "",
  contact_name:      "",
  contact_email:     "",
  contact_phone:     "",
  contact_role:      "",
  preferred_mall:    "",
  preferred_zone:    "",
  size_min_sqm:      "",
  size_max_sqm:      "",
  target_opening:    "Q4 2026",
  first_uae_store:   false,
  priority:          "medium",
};

export default function NewInquiry() {
  const navigate = useNavigate();
  const [form,       setForm]       = useState(INITIAL);
  const [properties, setProperties] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [errors,     setErrors]     = useState({});

  // Load properties for mall dropdown
  useEffect(() => {
    propertiesApi.list({ status: "active" })
      .then(d => setProperties(d.properties || []))
      .catch(() => {});
  }, []);

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm(f => ({ ...f, [name]: type === "checkbox" ? checked : value }));
    if (errors[name]) setErrors(e => ({ ...e, [name]: null }));
  }

  function validate() {
    const e = {};
    if (!form.brand_name.trim())        e.brand_name        = "Brand name is required";
    if (!form.legal_entity_name.trim()) e.legal_entity_name = "Legal entity name is required";
    if (!form.category)                 e.category          = "Category is required";
    if (form.size_min_sqm && form.size_max_sqm &&
        Number(form.size_min_sqm) > Number(form.size_max_sqm)) {
      e.size_max_sqm = "Max size must be greater than min size";
    }
    if (form.contact_email && !/\S+@\S+\.\S+/.test(form.contact_email)) {
      e.contact_email = "Enter a valid email address";
    }
    return e;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }

    setSubmitting(true);
    try {
      const payload = {
        ...form,
        size_min_sqm: form.size_min_sqm ? Number(form.size_min_sqm) : null,
        size_max_sqm: form.size_max_sqm ? Number(form.size_max_sqm) : null,
        preferred_mall: form.preferred_mall || null,
      };
      const res = await inquiriesApi.create(payload);
      navigate(`/inquiries`);
    } catch (err) {
      setErrors({ submit: err.message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="new-inquiry">
      <PageHeader
        title="New Inquiry"
        subtitle="Create a new tenant leasing inquiry"
        action={
          <Button variant="ghost" onClick={() => navigate("/inquiries")}>
            ← Back
          </Button>
        }
      />

      <form onSubmit={handleSubmit} className="inquiry-form">

        {/* ── Section 1 — Brand & Entity ─────────────────────────────────── */}
        <div className="form-section">
          <h2 className="form-section-title">Brand & Legal Entity</h2>

          <div className="form-row">
            <div className="form-field">
              <label className="form-label">Brand Name <span className="required">*</span></label>
              <input
                className={`form-input ${errors.brand_name ? "form-input--error" : ""}`}
                name="brand_name"
                value={form.brand_name}
                onChange={handleChange}
                placeholder="e.g. Summit Gear Co."
              />
              {errors.brand_name && <p className="form-error">{errors.brand_name}</p>}
            </div>

            <div className="form-field">
              <label className="form-label">Legal Entity Name <span className="required">*</span></label>
              <input
                className={`form-input ${errors.legal_entity_name ? "form-input--error" : ""}`}
                name="legal_entity_name"
                value={form.legal_entity_name}
                onChange={handleChange}
                placeholder="e.g. Summit Gear Trading LLC"
              />
              {errors.legal_entity_name && <p className="form-error">{errors.legal_entity_name}</p>}
            </div>
          </div>

          <div className="form-row">
            <div className="form-field">
              <label className="form-label">Category <span className="required">*</span></label>
              <select
                className={`form-select ${errors.category ? "form-input--error" : ""}`}
                name="category"
                value={form.category}
                onChange={handleChange}
              >
                <option value="">Select category</option>
                {CATEGORIES.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
              {errors.category && <p className="form-error">{errors.category}</p>}
            </div>

            <div className="form-field">
              <label className="form-label">Channel</label>
              <select
                className="form-select"
                name="channel"
                value={form.channel}
                onChange={handleChange}
              >
                {CHANNELS.map(c => (
                  <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-row form-row--3">
            <div className="form-field">
              <label className="form-label">Priority</label>
              <select
                className="form-select"
                name="priority"
                value={form.priority}
                onChange={handleChange}
              >
                {PRIORITIES.map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>

            <div className="form-field">
              <label className="form-label">Target Opening</label>
              <select
                className="form-select"
                name="target_opening"
                value={form.target_opening}
                onChange={handleChange}
              >
                {TARGET_OPENINGS.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div className="form-field form-field--checkbox">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  name="first_uae_store"
                  checked={form.first_uae_store}
                  onChange={handleChange}
                  className="checkbox-input"
                />
                <span>First UAE Store</span>
              </label>
              <p className="form-hint">Check if this brand has no existing UAE presence</p>
            </div>
          </div>
        </div>

        {/* ── Section 2 — Contact ───────────────────────────────────────── */}
        <div className="form-section">
          <h2 className="form-section-title">Contact Details</h2>

          <div className="form-row">
            <div className="form-field">
              <label className="form-label">Contact Name</label>
              <input
                className="form-input"
                name="contact_name"
                value={form.contact_name}
                onChange={handleChange}
                placeholder="e.g. James Whitfield"
              />
            </div>

            <div className="form-field">
              <label className="form-label">Contact Role</label>
              <input
                className="form-input"
                name="contact_role"
                value={form.contact_role}
                onChange={handleChange}
                placeholder="e.g. Regional Director — MENA"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-field">
              <label className="form-label">Email</label>
              <input
                className={`form-input ${errors.contact_email ? "form-input--error" : ""}`}
                name="contact_email"
                type="email"
                value={form.contact_email}
                onChange={handleChange}
                placeholder="e.g. james@brand.com"
              />
              {errors.contact_email && <p className="form-error">{errors.contact_email}</p>}
            </div>

            <div className="form-field">
              <label className="form-label">Phone</label>
              <input
                className="form-input"
                name="contact_phone"
                value={form.contact_phone}
                onChange={handleChange}
                placeholder="e.g. +971501234567"
              />
            </div>
          </div>
        </div>

        {/* ── Section 3 — Space Requirements ───────────────────────────── */}
        <div className="form-section">
          <h2 className="form-section-title">Space Requirements</h2>

          <div className="form-row">
            <div className="form-field">
              <label className="form-label">Preferred Mall</label>
              <select
                className="form-select"
                name="preferred_mall"
                value={form.preferred_mall}
                onChange={handleChange}
              >
                <option value="">No preference</option>
                {properties.map(p => (
                  <option key={p.property_id} value={p.property_id}>
                    {p.name} ({p.address_city})
                  </option>
                ))}
              </select>
            </div>

            <div className="form-field">
              <label className="form-label">Preferred Zone</label>
              <input
                className="form-input"
                name="preferred_zone"
                value={form.preferred_zone}
                onChange={handleChange}
                placeholder="e.g. Sports & Outdoor"
              />
            </div>
          </div>

          <div className="form-row form-row--3">
            <div className="form-field">
              <label className="form-label">Min Size (sqm)</label>
              <input
                className="form-input"
                name="size_min_sqm"
                type="number"
                min="0"
                value={form.size_min_sqm}
                onChange={handleChange}
                placeholder="e.g. 150"
              />
            </div>

            <div className="form-field">
              <label className="form-label">Max Size (sqm)</label>
              <input
                className={`form-input ${errors.size_max_sqm ? "form-input--error" : ""}`}
                name="size_max_sqm"
                type="number"
                min="0"
                value={form.size_max_sqm}
                onChange={handleChange}
                placeholder="e.g. 300"
              />
              {errors.size_max_sqm && <p className="form-error">{errors.size_max_sqm}</p>}
            </div>
          </div>
        </div>

        {/* ── Submit ────────────────────────────────────────────────────── */}
        {errors.submit && (
          <div className="form-submit-error">⚠ {errors.submit}</div>
        )}

        <div className="form-actions">
          <Button variant="ghost" onClick={() => navigate("/inquiries")}>
            Cancel
          </Button>
          <Button variant="primary" loading={submitting}>
            Create Inquiry
          </Button>
        </div>

      </form>
    </div>
  );
}
