import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import client from '../api/clients'

// ── Constants ─────────────────────────────────────────────────────────────────

const STEPS = [
  { key: 'node_intake',      label: '1. Intake & Lead Scoring' },
  { key: 'node_unit_match',  label: '2. Unit Match & Scoring' },
  { key: 'node_hot_draft',   label: '3. Heads of Terms Draft' },
  { key: 'gate_1',           label: '⚑ Gate 1 — Exec Review',    isGate: true },
  { key: 'node_doc_request', label: '4. Document Request' },
  { key: 'node_doc_verify',  label: '4b. Document Verification' },
  { key: 'gate_2',           label: '⚑ Gate 2 — LCM Review',     isGate: true },
  { key: 'node_lease_gen',   label: '5. Lease Generation' },
  { key: 'gate_3',           label: '⚑ Gate 3 — Final Approval', isGate: true },
  { key: 'node_ejari',       label: '6. EJARI Filing' },
  { key: 'complete',         label: '✓ Deal Closed' },
]

const GRADE_COLORS = {
  A: { bg: '#E1F5EE', color: '#0F6E56' },
  B: { bg: '#FAEEDA', color: '#854F0B' },
  C: { bg: '#FCEBEB', color: '#A32D2D' },
}

// ── Small helpers ─────────────────────────────────────────────────────────────

function StepItem({ step, currentStep, pausedAt }) {
  const isDone = STEPS.findIndex(s => s.key === step.key) <
                 STEPS.findIndex(s => s.key === (pausedAt || currentStep))
  const isActive = step.key === (pausedAt || currentStep)
  const isGate   = step.isGate

  let bg = 'transparent'
  let color = 'rgba(255,255,255,0.35)'
  let border = 'transparent'

  if (isDone)   { bg = 'rgba(0,196,180,0.1)';  color = '#00C4B4'; border = '#00C4B4' }
  if (isActive && isGate) { bg = 'rgba(239,159,39,0.15)'; color = '#EF9F27'; border = '#EF9F27' }
  if (isActive && !isGate) { bg = 'rgba(255,255,255,0.1)'; color = 'white'; border = 'white' }

  return (
    <div style={{
      padding: '7px 10px', borderRadius: '6px', fontSize: '12px',
      background: bg, color, borderLeft: `3px solid ${border}`,
      marginBottom: '4px', fontWeight: isActive ? '500' : '400',
    }}>
      {step.label}
    </div>
  )
}

function GradeBadge({ grade }) {
  if (!grade) return null
  const cfg = GRADE_COLORS[grade] || { bg: '#F3F4F6', color: '#6B7280' }
  return <span style={{ fontSize: '12px', padding: '2px 8px', borderRadius: '20px', background: cfg.bg, color: cfg.color, fontWeight: '600' }}>{grade}</span>
}

function Card({ title, children, style = {} }) {
  return (
    <div style={{ background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px', padding: '16px', marginBottom: '16px', ...style }}>
      {title && <div style={{ fontSize: '13px', fontWeight: '500', color: '#0A2342', marginBottom: '12px', paddingBottom: '10px', borderBottom: '0.5px solid #F3F4F6' }}>{title}</div>}
      {children}
    </div>
  )
}

function MetricRow({ label, value, mono }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '0.5px solid #F9FAFB' }}>
      <span style={{ fontSize: '12px', color: '#6B7280' }}>{label}</span>
      <span style={{ fontSize: '12px', color: '#0A2342', fontWeight: '500', fontFamily: mono ? 'monospace' : 'inherit' }}>{value}</span>
    </div>
  )
}

// ── Gate panels ───────────────────────────────────────────────────────────────

function Gate1Panel({ state, onDecision, loading }) {
  const lead    = state.lead_score_result || {}
  const matched = state.matched_units || []
  const hot     = state.hot_draft || {}

  const [selectedUnit, setSelectedUnit]   = useState(matched[0]?.unit_id || '')
  const [rent, setRent]                   = useState(hot.base_rent_aed_sqm || 0)
  const [fitOut, setFitOut]               = useState(hot.fit_out_months || 3)
  const [duration, setDuration]           = useState(hot.lease_duration_years || 3)
  const [escalation, setEscalation]       = useState(hot.annual_escalation_pct || 5)
  const [deposit, setDeposit]             = useState(hot.security_deposit_months || 3)
  const [rentFree, setRentFree]           = useState(hot.rent_free_months || 0)
  const [notes, setNotes]                 = useState('')
  const [rejectReason, setRejectReason]   = useState('')

  function handleApprove() {
    onDecision('approve', 'gate_1', {
      hot_edits: {
        ...hot,
        base_rent_aed_sqm:    parseFloat(rent),
        fit_out_months:       parseInt(fitOut),
        lease_duration_years: parseInt(duration),
        annual_escalation_pct: parseFloat(escalation),
        security_deposit_months: parseInt(deposit),
        rent_free_months:     parseInt(rentFree),
        executive_notes:      notes,
      },
      selected_unit_id: selectedUnit,
    })
  }

  function handleReject() {
    if (!rejectReason) return alert('Please provide a rejection reason.')
    onDecision('reject', 'gate_1', {}, rejectReason)
  }

  return (
    <div style={{ background: '#FFFBEB', border: '1px solid #FCD34D', borderRadius: '10px', padding: '20px' }}>
      <div style={{ fontSize: '15px', fontWeight: '500', color: '#0A2342', marginBottom: '16px' }}>
        ⚑ Gate 1 — Leasing Executive Review
      </div>

      {/* Lead score */}
      {lead.lead_score !== undefined && (
        <Card title="Tenant Lead Score">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 2fr', gap: '12px' }}>
            <div style={{ background: '#F9FAFB', borderRadius: '6px', padding: '10px' }}>
              <div style={{ fontSize: '11px', color: '#9CA3AF' }}>Score</div>
              <div style={{ fontSize: '20px', fontWeight: '500', color: '#0A2342' }}>{lead.lead_score?.toFixed(2)}</div>
            </div>
            <div style={{ background: '#F9FAFB', borderRadius: '6px', padding: '10px' }}>
              <div style={{ fontSize: '11px', color: '#9CA3AF' }}>Grade</div>
              <div style={{ marginTop: '4px' }}><GradeBadge grade={lead.lead_grade} /></div>
            </div>
            <div style={{ background: '#F9FAFB', borderRadius: '6px', padding: '10px' }}>
              <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '4px' }}>Assessment</div>
              <div style={{ fontSize: '11px', color: '#374151', lineHeight: '1.5' }}>{lead.reasoning}</div>
            </div>
          </div>
        </Card>
      )}

      {/* Matched units */}
      {matched.length > 0 && (
        <Card title="Matched Units">
          {state.weak_match_warning && (
            <div style={{ background: '#FFFBEB', border: '0.5px solid #FCD34D', borderRadius: '6px', padding: '8px 12px', fontSize: '12px', color: '#92400E', marginBottom: '12px' }}>
              ⚠ {state.weak_match_warning}
            </div>
          )}
          {matched.map(u => {
            const sc = u._scoring || {}
            return (
              <div key={u.unit_id} style={{ border: '0.5px solid #E5E7EB', borderRadius: '6px', padding: '12px', marginBottom: '8px', background: selectedUnit === u.unit_id ? '#F0F9FF' : 'white', cursor: 'pointer' }}
                onClick={() => setSelectedUnit(u.unit_id)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '500', color: '#0A2342' }}>{u.unit_id}</span>
                  <span style={{ fontSize: '12px', color: '#00C4B4', fontWeight: '500' }}>Match: {sc.match_score?.toFixed(2)}</span>
                </div>
                <div style={{ fontSize: '11px', color: '#6B7280', marginBottom: '4px' }}>
                  {u.mall_name} · {u.zone} · {u.sqm} sqm · AED {u.base_rent_sqm}/sqm
                </div>
                {sc.demand_signal && <div style={{ fontSize: '11px', color: '#0369A1', background: '#F0F9FF', padding: '4px 8px', borderRadius: '4px' }}>{sc.demand_signal}</div>}
                {selectedUnit === u.unit_id && <div style={{ marginTop: '6px', fontSize: '11px', color: '#00C4B4', fontWeight: '500' }}>✓ Selected</div>}
              </div>
            )
          })}
        </Card>
      )}

      {/* HoT form */}
      {Object.keys(hot).length > 0 && (
        <Card title="Heads of Terms">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '12px' }}>
            {[
              { label: 'Base Rent (AED/sqm)', value: rent, set: setRent, type: 'number' },
              { label: 'Fit-out Months', value: fitOut, set: setFitOut, type: 'number' },
              { label: 'Lease Duration (years)', value: duration, set: setDuration, type: 'number' },
              { label: 'Escalation (%)', value: escalation, set: setEscalation, type: 'number' },
              { label: 'Security Deposit (months)', value: deposit, set: setDeposit, type: 'number' },
              { label: 'Rent Free Months', value: rentFree, set: setRentFree, type: 'number' },
            ].map(f => (
              <div key={f.label}>
                <label style={{ fontSize: '11px', color: '#6B7280', display: 'block', marginBottom: '4px' }}>{f.label}</label>
                <input type={f.type} value={f.value} onChange={e => f.set(e.target.value)}
                  style={{ width: '100%', padding: '7px 10px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', outline: 'none', boxSizing: 'border-box' }} />
              </div>
            ))}
          </div>
          <div>
            <label style={{ fontSize: '11px', color: '#6B7280', display: 'block', marginBottom: '4px' }}>Executive notes</label>
            <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2} placeholder="Optional notes..."
              style={{ width: '100%', padding: '7px 10px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', outline: 'none', resize: 'vertical', boxSizing: 'border-box' }} />
          </div>
        </Card>
      )}

      {/* Buttons */}
      <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
        <button onClick={handleApprove} disabled={loading}
          style={{ padding: '10px 24px', fontSize: '13px', fontWeight: '500', background: '#0A2342', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
          {loading ? 'Processing...' : '✓ Approve & Proceed'}
        </button>
        <div style={{ flex: 1 }}>
          <input value={rejectReason} onChange={e => setRejectReason(e.target.value)} placeholder="Rejection reason (required to reject)..."
            style={{ width: '100%', padding: '9px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', outline: 'none', boxSizing: 'border-box' }} />
        </div>
        <button onClick={handleReject} disabled={loading}
          style={{ padding: '10px 20px', fontSize: '13px', background: 'white', color: '#E24B4A', border: '1px solid #E24B4A', borderRadius: '6px', cursor: 'pointer' }}>
          ✕ Reject
        </button>
      </div>
    </div>
  )
}

function Gate2Panel({ state, onDecision, loading }) {
  const docs   = state.documents_received || {}
  const issues = state.document_issues || []
  const [notes, setNotes]         = useState('')
  const [rejectReason, setRejectReason] = useState('')

  return (
    <div style={{ background: '#FFFBEB', border: '1px solid #FCD34D', borderRadius: '10px', padding: '20px' }}>
      <div style={{ fontSize: '15px', fontWeight: '500', color: '#0A2342', marginBottom: '16px' }}>
        ⚑ Gate 2 — LCM Document Review
      </div>

      <Card title="Document Status">
        {docs.documents_submitted?.map(doc => {
          const icon = doc.status === 'valid' ? '✓' : doc.status === 'expired' ? '✕' : '⚠'
          const color = doc.status === 'valid' ? '#0F6E56' : doc.status === 'expired' ? '#A32D2D' : '#854F0B'
          return (
            <div key={doc.document_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '0.5px solid #F9FAFB' }}>
              <span style={{ fontSize: '12px', color: '#374151' }}>{doc.doc_type?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
              <span style={{ fontSize: '12px', color, fontWeight: '500' }}>{icon} {doc.status?.toUpperCase()}</span>
            </div>
          )
        })}
        {docs.missing_documents?.map(m => (
          <div key={m} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '0.5px solid #F9FAFB' }}>
            <span style={{ fontSize: '12px', color: '#374151' }}>{m?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
            <span style={{ fontSize: '12px', color: '#A32D2D', fontWeight: '500' }}>✕ MISSING</span>
          </div>
        ))}
        {issues.map((issue, i) => (
          <div key={i} style={{ background: '#FAEEDA', borderRadius: '4px', padding: '6px 10px', marginTop: '8px', fontSize: '12px', color: '#854F0B' }}>⚠ {issue}</div>
        ))}
      </Card>

      <div style={{ marginBottom: '16px' }}>
        <label style={{ fontSize: '11px', color: '#6B7280', display: 'block', marginBottom: '4px' }}>LCM notes</label>
        <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2} placeholder="Add notes on document review decision..."
          style={{ width: '100%', padding: '7px 10px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', outline: 'none', resize: 'vertical', boxSizing: 'border-box' }} />
      </div>

      <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
        <button onClick={() => onDecision('approve', 'gate_2', { agent_note: notes })} disabled={loading}
          style={{ padding: '10px 24px', fontSize: '13px', fontWeight: '500', background: '#0A2342', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
          {loading ? 'Processing...' : '✓ Approve Document Package'}
        </button>
        <div style={{ flex: 1 }}>
          <input value={rejectReason} onChange={e => setRejectReason(e.target.value)} placeholder="Rejection reason..."
            style={{ width: '100%', padding: '9px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', outline: 'none', boxSizing: 'border-box' }} />
        </div>
        <button onClick={() => { if (!rejectReason) return alert('Provide rejection reason.'); onDecision('reject', 'gate_2', {}, rejectReason) }} disabled={loading}
          style={{ padding: '10px 20px', fontSize: '13px', background: 'white', color: '#E24B4A', border: '1px solid #E24B4A', borderRadius: '6px', cursor: 'pointer' }}>
          ✕ Request Resubmission
        </button>
      </div>
    </div>
  )
}

function Gate3Panel({ state, onDecision, loading }) {
  const lease = state.lease_draft || {}
  const check = state.consistency_check || {}
  const [notes, setNotes]         = useState('')
  const [rejectReason, setRejectReason] = useState('')

  return (
    <div style={{ background: '#FFFBEB', border: '1px solid #FCD34D', borderRadius: '10px', padding: '20px' }}>
      <div style={{ fontSize: '15px', fontWeight: '500', color: '#0A2342', marginBottom: '16px' }}>
        ⚑ Gate 3 — Senior Manager Final Approval
      </div>

      {Object.keys(lease).length > 0 && (
        <Card title="Deal Summary">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0' }}>
            <MetricRow label="Tenant"        value={lease.tenant_brand_name || '—'} />
            <MetricRow label="Unit"          value={lease.unit_id || '—'} mono />
            <MetricRow label="Annual Rent"   value={lease.annual_base_rent_aed ? `AED ${Number(lease.annual_base_rent_aed).toLocaleString()}` : '—'} />
            <MetricRow label="Lease Start"   value={lease.lease_start_date || '—'} />
            <MetricRow label="Lease End"     value={lease.lease_end_date || '—'} />
            <MetricRow label="Security Dep." value={lease.security_deposit_aed ? `AED ${Number(lease.security_deposit_aed).toLocaleString()}` : '—'} />
          </div>
        </Card>
      )}

      {check.status && (
        <Card title={`Consistency Check ${check.status === 'pass' ? '✓' : '✕'}`}>
          <div style={{ fontSize: '12px', color: '#6B7280', marginBottom: '8px' }}>
            {check.checks_run} checks · {check.issues_found} issues found
          </div>
          {check.checks_detail?.filter(c => c.result === 'fail').map(c => (
            <div key={c.check_id} style={{ background: '#FCEBEB', borderRadius: '4px', padding: '6px 10px', marginBottom: '6px', fontSize: '12px', color: '#A32D2D' }}>
              {c.check_id} — {c.detail}
            </div>
          ))}
          {check.status === 'pass' && (
            <div style={{ background: '#E1F5EE', borderRadius: '4px', padding: '6px 10px', fontSize: '12px', color: '#0F6E56' }}>All checks passed</div>
          )}
        </Card>
      )}

      <div style={{ marginBottom: '16px' }}>
        <label style={{ fontSize: '11px', color: '#6B7280', display: 'block', marginBottom: '4px' }}>Manager notes</label>
        <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2} placeholder="Optional approval notes..."
          style={{ width: '100%', padding: '7px 10px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', outline: 'none', resize: 'vertical', boxSizing: 'border-box' }} />
      </div>

      <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
        <button onClick={() => onDecision('approve', 'gate_3', { agent_note: notes })} disabled={loading}
          style={{ padding: '10px 24px', fontSize: '13px', fontWeight: '500', background: '#0A2342', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
          {loading ? 'Processing...' : '✓ Approve & Send to Tenant'}
        </button>
        <div style={{ flex: 1 }}>
          <input value={rejectReason} onChange={e => setRejectReason(e.target.value)} placeholder="Rejection reason..."
            style={{ width: '100%', padding: '9px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', outline: 'none', boxSizing: 'border-box' }} />
        </div>
        <button onClick={() => { if (!rejectReason) return alert('Provide rejection reason.'); onDecision('reject', 'gate_3', {}, rejectReason) }} disabled={loading}
          style={{ padding: '10px 20px', fontSize: '13px', background: 'white', color: '#E24B4A', border: '1px solid #E24B4A', borderRadius: '6px', cursor: 'pointer' }}>
          ✕ Send Back for Revision
        </button>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function WorkflowView() {
  const { threadId: inquiryId } = useParams()   // we pass inquiry_id in the URL
  const navigate = useNavigate()

  const [inquiry, setInquiry]       = useState(null)
  const [threadId, setThreadId]     = useState(null)
  const [workflowState, setWorkflowState] = useState(null)
  const [pausedAt, setPausedAt]     = useState(null)
  const [status, setStatus]         = useState(null)
  const [reasoningLog, setReasoningLog] = useState([])
  const [starting, setStarting]     = useState(false)
  const [gateLoading, setGateLoading] = useState(false)
  const [error, setError]           = useState(null)
  const pollRef = useRef(null)

  // Load inquiry on mount
  useEffect(() => {
    client.get(`/inquiries/${inquiryId}`)
      .then(res => setInquiry(res.data.inquiry))
      .catch(() => setError('Inquiry not found'))
  }, [inquiryId])

  // Cleanup polling on unmount
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  function startPolling(tid) {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(() => fetchState(tid), 2000)
  }

  async function fetchState(tid) {
    try {
      const res = await client.get(`/workflows/${tid}/state`)
      const data = res.data
      setWorkflowState(data.state || {})
      setPausedAt(data.paused_at)
      setStatus(data.status)
      setReasoningLog(data.state?.reasoning_log || [])
      if (data.status === 'completed' || data.paused_at) {
        clearInterval(pollRef.current)
      }
    } catch {
      clearInterval(pollRef.current)
    }
  }

  async function startWorkflow() {
    setStarting(true)
    setError(null)
    try {
      const res = await client.post('/workflows/start', { inquiry_id: inquiryId })
      const tid = res.data.thread_id
      setThreadId(tid)
      setStatus('running')
      await fetchState(tid)
      startPolling(tid)
    } catch (err) {
      setError('Failed to start workflow: ' + (err.response?.data?.detail || err.message))
    } finally {
      setStarting(false)
    }
  }

  async function handleDecision(decision, gate, extras = {}, rejectionReason = '') {
    if (!threadId) return
    setGateLoading(true)
    setError(null)
    try {
      await client.post(`/workflows/${threadId}/resume`, {
        decision,
        gate,
        agent_note:       rejectionReason || extras.agent_note || null,
        hot_edits:        extras.hot_edits || null,
        selected_unit_id: extras.selected_unit_id || null,
      })
      setStatus('running')
      setPausedAt(null)
      await fetchState(threadId)
      startPolling(threadId)
    } catch (err) {
      setError('Failed to resume workflow: ' + (err.response?.data?.detail || err.message))
    } finally {
      setGateLoading(false)
    }
  }

  const currentStep = workflowState?.current_step || 'node_intake'

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr 220px', gap: '16px', height: '100%' }}>

      {/* Left — step tracker */}
      <div style={{ background: '#0A2342', borderRadius: '10px', padding: '16px', alignSelf: 'start' }}>
        <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginBottom: '12px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>Workflow</div>
        {STEPS.map(step => (
          <StepItem key={step.key} step={step} currentStep={currentStep} pausedAt={pausedAt} />
        ))}
      </div>

      {/* Main content */}
      <div style={{ minWidth: 0 }}>

        {/* Inquiry bar */}
        {inquiry && (
          <div style={{ background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px', padding: '12px 16px', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <span style={{ fontSize: '14px', fontWeight: '500', color: '#0A2342' }}>{inquiry.brand_name}</span>
              <span style={{ fontSize: '12px', color: '#6B7280', marginLeft: '10px' }}>{inquiryId}</span>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              {inquiry.priority && (
                <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '20px', background: '#EEF2FF', color: '#0A2342' }}>{inquiry.priority}</span>
              )}
              {status && (
                <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '20px',
                  background: status === 'paused' ? '#FAEEDA' : status === 'completed' ? '#E1F5EE' : '#EEF2FF',
                  color: status === 'paused' ? '#854F0B' : status === 'completed' ? '#0F6E56' : '#0A2342',
                  fontWeight: '500' }}>
                  {status === 'paused' ? `Paused at ${pausedAt}` : status}
                </span>
              )}
            </div>
          </div>
        )}

        {error && (
          <div style={{ background: '#FCEBEB', border: '0.5px solid #F7C1C1', borderRadius: '8px', padding: '12px 16px', color: '#A32D2D', fontSize: '13px', marginBottom: '16px' }}>{error}</div>
        )}

        {/* Start workflow button */}
        {!threadId && !starting && (
          <div style={{ background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px', padding: '32px', textAlign: 'center' }}>
            <div style={{ fontSize: '14px', color: '#0A2342', marginBottom: '8px', fontWeight: '500' }}>Ready to start workflow</div>
            <div style={{ fontSize: '12px', color: '#6B7280', marginBottom: '20px' }}>
              The agent will run intake, unit matching, and HoT drafting — then pause at Gate 1.
            </div>
            <button onClick={startWorkflow}
              style={{ padding: '10px 28px', fontSize: '14px', fontWeight: '500', background: '#0A2342', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
              Start Leasing Workflow
            </button>
          </div>
        )}

        {starting && (
          <div style={{ background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px', padding: '32px', textAlign: 'center', color: '#6B7280', fontSize: '13px' }}>
            Agent running — intake, lead scoring, unit matching, HoT drafting...
          </div>
        )}

        {/* Running indicator */}
        {status === 'running' && !pausedAt && threadId && (
          <div style={{ background: '#EEF2FF', border: '0.5px solid #C7D2FE', borderRadius: '8px', padding: '12px 16px', fontSize: '13px', color: '#0A2342', marginBottom: '16px' }}>
            Agent running · {currentStep?.replace(/_/g, ' ')}...
          </div>
        )}

        {/* Reasoning log */}
        {reasoningLog.length > 0 && (
          <div style={{ marginBottom: '16px' }}>
            {reasoningLog.map((entry, i) => (
              <details key={i} style={{ background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '8px', padding: '10px 14px', marginBottom: '8px' }}>
                <summary style={{ fontSize: '13px', fontWeight: '500', color: '#0A2342', cursor: 'pointer', listStyle: 'none', display: 'flex', justifyContent: 'space-between' }}>
                  <span>✓ {entry.step?.replace(/_/g, ' ')}</span>
                  {entry.fallback_used && <span style={{ fontSize: '11px', padding: '1px 6px', background: '#FAEEDA', color: '#854F0B', borderRadius: '10px' }}>fallback</span>}
                </summary>
                {entry.reasoning && (
                  <div style={{ marginTop: '8px', padding: '8px', background: '#F9FAFB', borderRadius: '4px', fontSize: '12px', color: '#374151', lineHeight: '1.5', fontStyle: 'italic' }}>
                    {entry.reasoning}
                  </div>
                )}
              </details>
            ))}
          </div>
        )}

        {/* Gate panels */}
        {pausedAt === 'gate_1' && workflowState && (
          <Gate1Panel state={workflowState} onDecision={handleDecision} loading={gateLoading} />
        )}
        {pausedAt === 'gate_2' && workflowState && (
          <Gate2Panel state={workflowState} onDecision={handleDecision} loading={gateLoading} />
        )}
        {pausedAt === 'gate_3' && workflowState && (
          <Gate3Panel state={workflowState} onDecision={handleDecision} loading={gateLoading} />
        )}

        {/* Deal closed */}
        {status === 'completed' && workflowState?.deal_closed && (
          <div style={{ background: '#0A2342', borderRadius: '10px', padding: '24px', textAlign: 'center', color: 'white' }}>
            <div style={{ fontSize: '20px', marginBottom: '8px' }}>🎉 Deal Closed</div>
            <div style={{ fontSize: '13px', color: '#00C4B4', marginBottom: '4px' }}>
              EJARI: {workflowState.ejari_certificate?.registration_number || '—'}
            </div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>
              Status: {workflowState.ejari_certificate?.status}
            </div>
          </div>
        )}
      </div>

      {/* Right — state viewer */}
      <div style={{ alignSelf: 'start' }}>
        <div style={{ background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px', padding: '14px' }}>
          <div style={{ fontSize: '12px', fontWeight: '500', color: '#0A2342', marginBottom: '12px' }}>State</div>

          {workflowState?.lead_score_result && (
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '4px' }}>Lead</div>
              <GradeBadge grade={workflowState.lead_score_result.lead_grade} />
              <span style={{ fontSize: '12px', color: '#374151', marginLeft: '6px' }}>
                {workflowState.lead_score_result.lead_score?.toFixed(2)}
              </span>
            </div>
          )}

          {workflowState?.matched_units?.length > 0 && (
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '2px' }}>Units matched</div>
              <div style={{ fontSize: '13px', fontWeight: '500', color: '#0A2342' }}>{workflowState.matched_units.length}</div>
            </div>
          )}

          {workflowState?.document_issues?.length > 0 && (
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '2px' }}>Doc issues</div>
              <div style={{ fontSize: '13px', fontWeight: '500', color: '#E24B4A' }}>{workflowState.document_issues.length}</div>
            </div>
          )}

          {workflowState?.ejari_certificate && (
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '2px' }}>EJARI</div>
              <div style={{ fontSize: '11px', color: '#00C4B4', fontWeight: '500' }}>✓ Filed</div>
            </div>
          )}

          {workflowState?.errors?.length > 0 && (
            <div>
              <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '4px' }}>Errors</div>
              {workflowState.errors.map((e, i) => (
                <div key={i} style={{ fontSize: '11px', color: '#A32D2D', background: '#FCEBEB', borderRadius: '4px', padding: '4px 6px', marginBottom: '4px' }}>{e}</div>
              ))}
            </div>
          )}

          {!workflowState && (
            <div style={{ fontSize: '12px', color: '#9CA3AF' }}>State will appear once workflow starts.</div>
          )}
        </div>

        <button onClick={() => navigate('/inquiries')}
          style={{ width: '100%', marginTop: '10px', padding: '8px', fontSize: '12px', background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '6px', color: '#6B7280', cursor: 'pointer' }}>
          ← Back to Inquiries
        </button>
      </div>
    </div>
  )
}
