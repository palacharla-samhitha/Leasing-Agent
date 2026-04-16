// src/services/api.js
// Central API client — all calls to FastAPI backend go through here
// Base URL reads from .env — set REACT_APP_API_URL in your .env file

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function request(method, path, body = null, params = {}) {
  const url = new URL(`${BASE_URL}${path}`);

  // Append query params
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== "") {
      url.searchParams.append(k, v);
    }
  });

  const options = {
    method,
    headers: { "Content-Type": "application/json" },
  };

  if (body) options.body = JSON.stringify(body);

  const res = await fetch(url.toString(), options);

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

const get  = (path, params) => request("GET",   path, null, params);
const post = (path, body)   => request("POST",  path, body);
const patch = (path, body)  => request("PATCH", path, body);
const del  = (path)         => request("DELETE", path);


// ── Health ────────────────────────────────────────────────────────────────────

export const healthApi = {
  check: () => get("/health"),
};


// ── Inquiries ─────────────────────────────────────────────────────────────────

export const inquiriesApi = {
  list: (filters = {}) => get("/inquiries/", filters),
  get:  (id)           => get(`/inquiries/${id}`),
  create: (body)       => post("/inquiries/", body),
  update: (id, body)   => patch(`/inquiries/${id}`, body),
  delete: (id)         => del(`/inquiries/${id}`),
};


// ── Units ─────────────────────────────────────────────────────────────────────

export const unitsApi = {
  list:         (filters = {}) => get("/units/", filters),
  get:          (id)           => get(`/units/${id}`),
  updateStatus: (id, status)   => patch(`/units/${id}/status`, { status }),
};


// ── Properties ────────────────────────────────────────────────────────────────

export const propertiesApi = {
  list: (filters = {}) => get("/properties/", filters),
  get:  (id)           => get(`/properties/${id}`),
};


// ── Workflows ─────────────────────────────────────────────────────────────────

export const workflowsApi = {
  start:   (inquiry_id)            => post("/workflows/start", { inquiry_id }),
  getState:(thread_id)             => get(`/workflows/${thread_id}/state`),
  resume:  (thread_id, body)       => post(`/workflows/${thread_id}/resume`, body),
  history: (thread_id)             => get(`/workflows/${thread_id}/history`),
  active:  ()                      => get("/workflows/active"),
};


// ── Dashboard ─────────────────────────────────────────────────────────────────

export const dashboardApi = {
  summary:  () => get("/dashboard/summary"),
  pipeline: () => get("/dashboard/pipeline"),
  units:    () => get("/dashboard/units"),
};