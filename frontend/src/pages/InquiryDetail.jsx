// src/pages/InquiryDetail.jsx
import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { inquiriesApi, workflowsApi } from "../services/api";
import {
  PageHeader, Card, StatusBadge,
  Button, Spinner, ErrorState
} from "../components/ui";
import "./InquiryDetail.css";

const GATE_LABELS = {
  gate_1: "Gate 1 — Leasing Executive Approval",
  gate_2: "Gate 2 — LCM Document Review",
  gate_3: "Gate 3 — Senior Manager Final Approval",
};

const GATE_DESC = {
  gate_1: "Review matched units and Heads of Terms. Select a unit, edit terms if needed, then approve or reject.",
  gate_2: "Review KYC/KYB document status. If issues exist, reject to request updated documents.",
  gate_3: "Final review of lease draft and consistency checks. Approve to file EJARI.",
};

// HoT fields the leasing exec can edit at Gate 1
const HOT_EDITABLE_FIELDS = [
  { key: "base_rent_aed_sqm",       label: "Base Rent (AED/sqm)",      type: "number" },
  { key: "lease_duration_years",    label: "Lease Duration (years)",   type: "number" },
  { key: "fit_out_months",          label: "Fit-Out Months",           type: "number" },
  { key: "rent_free_months",        label: "Rent-Free Months",         type: "number" },
  { key: "security_deposit_months", label: "Security Deposit (months)", type: "number" },
  { key: "annual_escalation_pct",   label: "Annual Escalation (%)",    type: "number" },
];

export default function InquiryDetail() {
  const { id }   = useParams();
  const navigate = useNavigate();

  const [inquiry,        setInquiry]        = useState(null);
  const [workflow,       setWorkflow]       = useState(null);
  const [threadId,       setThreadId]       = useState(null);
  const [loading,        setLoading]        = useState(true);
  const [wfLoading,      setWfLoading]      = useState(false);
  const [resuming,       setResuming]       = useState(false);
  const [error,          setError]          = useState(null);
  const [polling,        setPolling]        = useState(false);

  // Gate controls
  const [note,           setNote]           = useState("");
  const [rejecting,      setRejecting]      = useState(false);   // show rejection reason box
  const [rejectReason,   setRejectReason]   = useState("");
  const [selectedUnit,   setSelectedUnit]   = useState("");      // Gate 1 unit picker
  const [hotEdits,       setHotEdits]       = useState({});      // Gate 1 HoT edits
  const [showHotEdit,    setShowHotEdit]    = useState(false);   // toggle HoT edit form
  const [rejectCount,    setRejectCount]    = useState(0);       // track rejections

  // ── Load inquiry ──────────────────────────────────────────────────────────
  useEffect(() => {
    inquiriesApi.get(id)
      .then(d => setInquiry(d))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  // ── Poll workflow state ───────────────────────────────────────────────────
  const pollWorkflow = useCallback(async (tid) => {
    if (!tid) return;
    try {
      const state = await workflowsApi.getState(tid);
      setWorkflow(state);
      if (state.status === "running") {
        setTimeout(() => pollWorkflow(tid), 2500);
      } else {
        setPolling(false);
        inquiriesApi.get(id).then(d => setInquiry(d));
        // Pre-fill HoT edits from agent draft when paused at gate_1
        if (state.status === "paused" && state.paused_at === "gate_1") {
          const draft = state.state?.hot_draft || {};
          const prefill = {};
          HOT_EDITABLE_FIELDS.forEach(f => {
            if (draft[f.key] !== undefined) prefill[f.key] = draft[f.key];
          });
          setHotEdits(prefill);
          // Auto-select top matched unit
          const units = state.state?.matched_units || [];
          if (units.length > 0 && !selectedUnit) {
            setSelectedUnit(units[0].unit_id || "");
          }
        }
      }
    } catch {
      setPolling(false);
    }
  }, [id, selectedUnit]);

  // ── Start workflow ────────────────────────────────────────────────────────
  async function handleStart() {
    setWfLoading(true);
    setPolling(true);
    setRejecting(false);
    setRejectReason("");
    setNote("");
    setHotEdits({});
    setSelectedUnit("");
    try {
      const res = await workflowsApi.start(id);
      setThreadId(res.thread_id);
      await pollWorkflow(res.thread_id);
    } catch (e) {
      setError(e.message);
      setPolling(false);
    } finally {
      setWfLoading(false);
    }
  }

  // ── Approve ───────────────────────────────────────────────────────────────
  async function handleApprove() {
    if (!threadId || !workflow?.paused_at) return;
    setResuming(true);
    setPolling(true);
    setRejecting(false);

    const body = {
      decision:   "approve",
      gate:       workflow.paused_at,
      agent_note: note || undefined,
    };

    // Gate 1 — pass edited HoT + selected unit
    if (workflow.paused_at === "gate_1") {
      if (Object.keys(hotEdits).length > 0) body.hot_edits = hotEdits;
      if (selectedUnit) body.selected_unit_id = selectedUnit;
    }

    try {
      await workflowsApi.resume(threadId, body);
      setNote("");
      setHotEdits({});
      setShowHotEdit(false);
      await pollWorkflow(threadId);
    } catch (e) {
      setError(e.message);
      setPolling(false);
    } finally {
      setResuming(false);
    }
  }

  // ── Reject ────────────────────────────────────────────────────────────────
  async function handleReject() {
    if (!rejectReason.trim()) return; // reason is required
    if (!threadId || !workflow?.paused_at) return;
    setResuming(true);
    setPolling(true);

    try {
      await workflowsApi.resume(threadId, {
        decision:   "reject",
        gate:       workflow.paused_at,
        agent_note: rejectReason,
      });
      setRejectCount(c => c + 1);
      setRejecting(false);
      setRejectReason("");
      setNote("");
      setHotEdits({});
      setShowHotEdit(false);
      setSelectedUnit("");
      await pollWorkflow(threadId);
    } catch (e) {
      setError(e.message);
      setPolling(false);
    } finally {
      setResuming(false);
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  function fmt(val) {
    if (val === null || val === undefined || val === "") return "—";
    if (typeof val === "boolean") return val ? "Yes" : "No";
    return val;
  }

  function fmtAed(val) {
    if (!val) return "—";
    return `AED ${Number(val).toLocaleString()}`;
  }

  if (loading) return <div className="page-center"><Spinner size={36} /></div>;
  if (error)   return <ErrorState message={error} />;
  if (!inquiry) return null;

  const { inquiry: inq, lead_score, documents } = inquiry;
  const state   = workflow?.state || {};
  const units   = state.matched_units || [];
  const hotDraft = state.hot_draft || {};

  return (
    <div className="inquiry-detail">
      <PageHeader
        title={inq.brand_name}
        subtitle={`${inq.inquiry_id} · ${inq.legal_entity_name}`}
        action={
          <Button variant="ghost" onClick={() => navigate("/inquiries")}>
            ← Back
          </Button>
        }
      />

      {/* Meta row */}
      <div className="detail-meta">
        <StatusBadge status={inq.status} />
        <StatusBadge status={inq.priority} />
        <span className="meta-channel">{inq.channel?.replace(/_/g, " ")}</span>
        {inq.risk_flag && (
          <span className="risk-flag">⚠ {inq.risk_flag.replace(/_/g, " ")}</span>
        )}
        {inq.first_uae_store && (
          <span className="badge badge-purple">First UAE Store</span>
        )}
      </div>

      <div className="detail-grid">

        {/* ── LEFT COLUMN ─────────────────────────────────────────────── */}
        <div className="detail-left">

          <Card>
            <h2 className="card-title">Inquiry Details</h2>
            <div className="info-grid">
              {[
                ["Category",       inq.category],
                ["Preferred Mall", inq.preferred_mall_name || inq.preferred_mall],
                ["Preferred Zone", inq.preferred_zone],
                ["Size Required",  inq.size_min_sqm && inq.size_max_sqm
                  ? `${inq.size_min_sqm} – ${inq.size_max_sqm} sqm` : null],
                ["Target Opening", inq.target_opening],
                ["Received",       new Date(inq.received_at).toLocaleDateString("en-GB",
                  { day: "numeric", month: "short", year: "numeric" })],
              ].map(([label, val]) => (
                <div key={label} className="info-row">
                  <span className="info-label">{label}</span>
                  <span className="info-value">{fmt(val)}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <h2 className="card-title">Contact</h2>
            <div className="info-grid">
              {[
                ["Name",  inq.contact_name],
                ["Role",  inq.contact_role],
                ["Email", inq.contact_email],
                ["Phone", inq.contact_phone],
              ].map(([label, val]) => (
                <div key={label} className="info-row">
                  <span className="info-label">{label}</span>
                  <span className="info-value">{fmt(val)}</span>
                </div>
              ))}
            </div>
          </Card>

          {lead_score && (
            <Card>
              <h2 className="card-title">Lead Score</h2>
              <div className="lead-score-row">
                <div className={`lead-grade-big grade-${lead_score.lead_grade?.toLowerCase()}`}>
                  {lead_score.lead_grade}
                </div>
                <div className="lead-score-detail">
                  <div className="lead-score-num">{lead_score.lead_score}</div>
                  <div className="lead-score-bar-wrap">
                    <div className="lead-score-bar" style={{ width: `${lead_score.lead_score * 100}%` }} />
                  </div>
                </div>
              </div>
              {lead_score.reasoning && <p className="lead-reasoning">{lead_score.reasoning}</p>}
              <div className="signals">
                {lead_score.signals_positive?.map((s, i) => (
                  <span key={i} className="signal signal--pos">✓ {s}</span>
                ))}
                {lead_score.signals_negative?.map((s, i) => (
                  <span key={i} className="signal signal--neg">✗ {s}</span>
                ))}
              </div>
            </Card>
          )}

          {documents?.length > 0 && (
            <Card>
              <h2 className="card-title">Documents</h2>
              <div className="doc-list">
                {documents.map(doc => (
                  <div key={doc.document_id} className="doc-row">
                    <div className="doc-info">
                      <span className="doc-type">{doc.doc_type?.replace(/_/g, " ")}</span>
                      {doc.expiry_date && (
                        <span className="doc-expiry">
                          Expires {new Date(doc.expiry_date).toLocaleDateString("en-GB",
                            { day: "numeric", month: "short", year: "numeric" })}
                        </span>
                      )}
                      {doc.flag && <span className="doc-flag">⚠ {doc.flag}</span>}
                    </div>
                    <StatusBadge status={doc.status} />
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* ── RIGHT COLUMN — Workflow ──────────────────────────────────── */}
        <div className="detail-right">
          <Card className="workflow-card">
            <h2 className="card-title">AI Workflow</h2>

            {/* Not started */}
            {!threadId && !workflow && (
              <div className="workflow-start">
                <p className="workflow-start-desc">
                  Start the AI leasing agent. It will classify the inquiry,
                  match units, draft Heads of Terms — then pause for your
                  approval at Gate 1.
                </p>
                <Button variant="primary" loading={wfLoading} onClick={handleStart}>
                  ▶ Start Workflow
                </Button>
              </div>
            )}

            {/* Running */}
            {polling && (workflow?.status === "running" || !workflow) && (
              <div className="workflow-running">
                <Spinner size={24} />
                <p>Agent running — processing inquiry...</p>
              </div>
            )}

            {/* Paused at gate */}
            {!polling && workflow?.status === "paused" && workflow?.paused_at && (
              <div className="gate-section">

                {/* Gate header */}
                <div className="gate-header">
                  <span className="gate-indicator">⏸</span>
                  <div>
                    <p className="gate-title">{GATE_LABELS[workflow.paused_at]}</p>
                    <p className="gate-desc">{GATE_DESC[workflow.paused_at]}</p>
                  </div>
                </div>

                {/* Rejection count notice */}
                {rejectCount > 0 && (
                  <div className="reject-notice">
                    ↺ Agent re-ran after {rejectCount} rejection{rejectCount > 1 ? "s" : ""} — review updated output below
                  </div>
                )}

                {/* ── Gate 1 — Unit selector + HoT ── */}
                {workflow.paused_at === "gate_1" && (
                  <>
                    {units.length > 0 && (
                      <div className="agent-output">
                        <h3 className="output-title">
                          Matched Units — Select One to Proceed
                        </h3>
                        {units.map((u, i) => (
                          <div
                            key={i}
                            className={`unit-card unit-card--selectable ${selectedUnit === u.unit_id ? "unit-card--selected" : ""}`}
                            onClick={() => setSelectedUnit(u.unit_id)}
                          >
                            <div className="unit-header">
                              <div className="unit-select-indicator">
                                {selectedUnit === u.unit_id ? "●" : "○"}
                              </div>
                              <span className="unit-id">{u.unit_id}</span>
                              <span className="unit-score">
                                Score: {u._scoring?.match_score ?? "—"}
                              </span>
                            </div>
                            <div className="unit-meta">
                              <span>{u.mall_name || u.zone || "—"}</span>
                              <span>{u.sqm} sqm</span>
                              {u.base_rent_sqm && (
                                <span>AED {Number(u.base_rent_sqm).toLocaleString()}/sqm</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* HoT — read view + toggle to edit */}
                    {Object.keys(hotDraft).length > 0 && (
                      <div className="agent-output">
                        <div className="hot-header">
                          <h3 className="output-title">Heads of Terms Draft</h3>
                          <button
                            className="hot-edit-toggle"
                            onClick={() => setShowHotEdit(v => !v)}
                          >
                            {showHotEdit ? "← View" : "✎ Edit Terms"}
                          </button>
                        </div>

                        {!showHotEdit ? (
                          // Read view
                          <div className="hot-grid">
                            {Object.entries(hotDraft).map(([k, v]) => (
                              <div key={k} className="hot-row">
                                <span className="hot-key">{k.replace(/_/g, " ")}</span>
                                <span className="hot-val">
                                  {typeof v === "number" && k.includes("aed")
                                    ? fmtAed(v) : String(v ?? "—")}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          // Edit view — only editable fields
                          <div className="hot-edit-form">
                            <p className="hot-edit-hint">
                              Edit terms below. These values will override the agent's draft and feed into lease generation.
                            </p>
                            {HOT_EDITABLE_FIELDS.map(f => (
                              <div key={f.key} className="hot-edit-row">
                                <label className="hot-edit-label">{f.label}</label>
                                <input
                                  type={f.type}
                                  className="hot-edit-input"
                                  value={hotEdits[f.key] ?? hotDraft[f.key] ?? ""}
                                  onChange={e => setHotEdits(prev => ({
                                    ...prev,
                                    [f.key]: f.type === "number"
                                      ? Number(e.target.value)
                                      : e.target.value
                                  }))}
                                  placeholder={String(hotDraft[f.key] ?? "")}
                                />
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}

                {/* ── Gate 2 — Doc issues ── */}
                {workflow.paused_at === "gate_2" && (
                  <div className="agent-output">
                    <h3 className="output-title">Document Verification</h3>
                    {state.document_issues?.length > 0 ? (
                      state.document_issues.map((issue, i) => (
                        <div key={i} className="doc-issue">⚠ {issue}</div>
                      ))
                    ) : (
                      <div className="doc-ok">✓ All documents verified — no issues found</div>
                    )}
                  </div>
                )}

                {/* ── Gate 3 — Consistency check ── */}
                {workflow.paused_at === "gate_3" && state.consistency_check && (
                  <div className="agent-output">
                    <h3 className="output-title">Lease Consistency Check</h3>
                    <div className={`cc-status cc-status--${state.consistency_check.status}`}>
                      <span>{state.consistency_check.status === "pass" ? "✓ All checks passed" : "✗ Issues found"}</span>
                      <span>{state.consistency_check.checks_run} checks · {state.consistency_check.issues_found} issues</span>
                    </div>
                    {state.consistency_check.checks_detail?.filter(c => !c.passed).map((c, i) => (
                      <div key={i} className="cc-issue">
                        <span className="cc-issue-id">{c.check_id}</span>
                        <span className="cc-issue-detail">{c.detail}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* ── Approve / Reject controls ── */}
                {!rejecting ? (
                  <div className="gate-controls">
                    {/* Optional approve note */}
                    <div className="gate-note">
                      <label className="form-label">Note (optional)</label>
                      <textarea
                        className="gate-textarea"
                        value={note}
                        onChange={e => setNote(e.target.value)}
                        placeholder="Add a note for the audit trail..."
                        rows={2}
                      />
                    </div>
                    <div className="gate-actions">
                      <Button
                        variant="primary"
                        loading={resuming}
                        onClick={handleApprove}
                        disabled={workflow.paused_at === "gate_1" && !selectedUnit}
                      >
                        ✓ Approve
                      </Button>
                      <Button
                        variant="danger"
                        onClick={() => setRejecting(true)}
                      >
                        ✗ Reject
                      </Button>
                    </div>
                    {workflow.paused_at === "gate_1" && !selectedUnit && (
                      <p className="gate-hint">Select a unit above to approve</p>
                    )}
                  </div>
                ) : (
                  // Rejection reason panel
                  <div className="reject-panel">
                    <div className="reject-panel-title">
                      Rejection Reason <span className="required">*</span>
                    </div>
                    <p className="reject-panel-desc">
                      Explain why you are rejecting. The agent will use this context when re-running.
                    </p>
                    <textarea
                      className="gate-textarea"
                      value={rejectReason}
                      onChange={e => setRejectReason(e.target.value)}
                      placeholder={
                        workflow.paused_at === "gate_1"
                          ? "e.g. Units matched don't fit the zone strategy. Try units on Level 2."
                          : workflow.paused_at === "gate_2"
                          ? "e.g. Trade license has expired — request renewed documents from tenant."
                          : "e.g. Lease dates are incorrect — rent commencement should start after fit-out."
                      }
                      rows={3}
                      autoFocus
                    />
                    {!rejectReason.trim() && (
                      <p className="form-error">Rejection reason is required</p>
                    )}
                    <div className="gate-actions">
                      <Button
                        variant="danger"
                        loading={resuming}
                        onClick={handleReject}
                        disabled={!rejectReason.trim()}
                      >
                        Confirm Rejection
                      </Button>
                      <Button variant="ghost" onClick={() => { setRejecting(false); setRejectReason(""); }}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Completed */}
            {workflow?.status === "completed" && (
              <div className="workflow-complete">
                <div className="complete-icon">✓</div>
                <h3>Workflow Complete</h3>
                <p>EJARI filed · Deal closed · Handed to M360</p>
                {state.ejari_certificate && (
                  <div className="ejari-cert">
                    <p className="cert-label">EJARI Registration</p>
                    <p className="cert-number">{state.ejari_certificate.registration_number}</p>
                    <p className="cert-status">{state.ejari_certificate.status}</p>
                  </div>
                )}
              </div>
            )}

            {/* Agent steps log */}
            {state.reasoning_log?.length > 0 && (
              <div className="reasoning-log">
                <h3 className="output-title">Agent Steps</h3>
                {state.reasoning_log.map((log, i) => (
                  <div key={i} className="log-entry">
                    <span className="log-step">{log.step?.replace(/_/g, " ")}</span>
                    <span className="log-time">
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ""}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {inq.agent_note && (
            <Card>
              <h2 className="card-title">Agent Note</h2>
              <p className="agent-note-text">{inq.agent_note}</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}