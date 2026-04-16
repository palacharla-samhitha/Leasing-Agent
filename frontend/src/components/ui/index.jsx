// src/components/ui/index.jsx
// Reusable UI primitives — used across all pages

import "./ui.css";

// ── Card ─────────────────────────────────────────────────────────────────────

export function Card({ children, className = "", onClick }) {
  return (
    <div
      className={`card ${onClick ? "card--clickable" : ""} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

// ── Stat Card — for dashboard numbers ─────────────────────────────────────────

export function StatCard({ label, value, sub, accent = false, icon: Icon }) {
  return (
    <div className={`stat-card ${accent ? "stat-card--accent" : ""}`}>
      {Icon && (
        <div className="stat-icon">
          <Icon size={18} />
        </div>
      )}
      <p className="stat-label">{label}</p>
      <p className="stat-value">{value}</p>
      {sub && <p className="stat-sub">{sub}</p>}
    </div>
  );
}

// ── Badge ─────────────────────────────────────────────────────────────────────

const STATUS_COLORS = {
  in_progress:       "teal",
  pending_gate_1:    "gold",
  blocked_documents: "red",
  unit_matched:      "purple",
  completed:         "teal",
  cancelled:         "muted",
  paused:            "gold",
  running:           "teal",
  high:              "red",
  medium:            "gold",
  low:               "muted",
  vacant:            "teal",
  expiring_soon:     "gold",
  active:            "teal",
  inactive:          "muted",
};

export function StatusBadge({ status }) {
  const color = STATUS_COLORS[status] || "muted";
  return (
    <span className={`badge badge-${color}`}>
      {status?.replace(/_/g, " ")}
    </span>
  );
}

// ── Button ────────────────────────────────────────────────────────────────────

export function Button({
  children, onClick, variant = "primary",
  size = "md", disabled = false, loading = false
}) {
  return (
    <button
      className={`btn btn--${variant} btn--${size}`}
      onClick={onClick}
      disabled={disabled || loading}
    >
      {loading ? <span className="btn-spinner" /> : children}
    </button>
  );
}

// ── Spinner ───────────────────────────────────────────────────────────────────

export function Spinner({ size = 24 }) {
  return (
    <div
      className="spinner"
      style={{ width: size, height: size, borderWidth: size > 20 ? 3 : 2 }}
    />
  );
}

// ── Page header ───────────────────────────────────────────────────────────────

export function PageHeader({ title, subtitle, action }) {
  return (
    <div className="page-header">
      <div>
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {action && <div className="page-action">{action}</div>}
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

export function Empty({ message = "No data found" }) {
  return (
    <div className="empty">
      <p>{message}</p>
    </div>
  );
}

// ── Error state ───────────────────────────────────────────────────────────────

export function ErrorState({ message }) {
  return (
    <div className="error-state">
      <p>⚠ {message}</p>
    </div>
  );
}

// ── Pagination controls ───────────────────────────────────────────────────────

export function Pagination({ pagination, onNext, onPrev }) {
  if (!pagination) return null;
  const { has_next, has_prev, offset, limit, returned } = pagination;

  return (
    <div className="pagination">
      <span className="pagination-info">
        Showing {offset + 1}–{offset + returned}
      </span>
      <div className="pagination-controls">
        <Button
          variant="ghost"
          size="sm"
          onClick={onPrev}
          disabled={!has_prev}
        >
          ← Prev
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onNext}
          disabled={!has_next}
        >
          Next →
        </Button>
      </div>
    </div>
  );
}
