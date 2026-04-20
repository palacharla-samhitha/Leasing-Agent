import { useEffect, useState } from 'react'
import client from '../api/clients'

const EVENT_CONFIG = {
  node_completed:     { label: 'Node completed',     color: '#0A2342', bg: '#EEF2FF' },
  llm_called:         { label: 'LLM called',         color: '#0F6E56', bg: '#E1F5EE' },
  llm_failed:         { label: 'LLM failed',         color: '#A32D2D', bg: '#FCEBEB' },
  fallback_triggered: { label: 'Fallback triggered', color: '#854F0B', bg: '#FAEEDA' },
  gate_reached:       { label: 'Gate reached',       color: '#854F0B', bg: '#FAEEDA' },
  gate_approved:      { label: 'Gate approved',      color: '#0F6E56', bg: '#E1F5EE' },
  gate_rejected:      { label: 'Gate rejected',      color: '#A32D2D', bg: '#FCEBEB' },
  ejari_filed:        { label: 'EJARI filed',        color: '#0F6E56', bg: '#E1F5EE' },
  error_occurred:     { label: 'Error occurred',     color: '#A32D2D', bg: '#FCEBEB' },
}

function EventBadge({ type }) {
  const cfg = EVENT_CONFIG[type] || { label: type, color: '#6B7280', bg: '#F3F4F6' }
  return (
    <span style={{ fontSize: '11px', padding: '2px 7px', borderRadius: '20px', background: cfg.bg, color: cfg.color, fontWeight: '500', whiteSpace: 'nowrap' }}>
      {cfg.label}
    </span>
  )
}

function EventDot({ type }) {
  const cfg = EVENT_CONFIG[type] || { color: '#9CA3AF' }
  return <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: cfg.color, flexShrink: 0, marginTop: '3px' }} />
}

function PayloadPanel({ eventId, onClose }) {
  const [event, setEvent]   = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    client.get(`/audit/events/${eventId}`)
      .then(res => setEvent(res.data.event))
      .catch(() => setEvent(null))
      .finally(() => setLoading(false))
  }, [eventId])

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.4)', zIndex: 100,
      display: 'flex', alignItems: 'flex-start', justifyContent: 'flex-end',
    }} onClick={onClose}>
      <div style={{ background: 'white', width: '480px', height: '100%', overflowY: 'auto', padding: '24px', boxShadow: '-4px 0 16px rgba(0,0,0,0.08)' }}
        onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '15px', fontWeight: '500', color: '#0A2342' }}>Event detail</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '18px', color: '#9CA3AF', cursor: 'pointer' }}>✕</button>
        </div>

        {loading && <p style={{ color: '#9CA3AF', fontSize: '13px' }}>Loading...</p>}

        {event && (
          <>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
              {[
                { label: 'Event type', value: <EventBadge type={event.event_type} /> },
                { label: 'Node',       value: event.node_name || '—', mono: true },
                { label: 'Inquiry',    value: event.inquiry_id || '—', mono: true },
                { label: 'Actor',      value: `${event.actor_type} · ${event.actor_id}` },
                { label: 'Timestamp', value: new Date(event.created_at).toLocaleString() },
              ].map(row => (
                <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', color: '#9CA3AF' }}>{row.label}</span>
                  {typeof row.value === 'string'
                    ? <span style={{ fontSize: '12px', color: '#374151', fontFamily: row.mono ? 'monospace' : 'inherit' }}>{row.value}</span>
                    : row.value}
                </div>
              ))}
            </div>

            <div style={{ borderTop: '0.5px solid #F3F4F6', paddingTop: '16px' }}>
              <div style={{ fontSize: '12px', fontWeight: '500', color: '#0A2342', marginBottom: '8px' }}>Payload</div>
              {event.payload
                ? <pre style={{ background: '#F9FAFB', border: '0.5px solid #E5E7EB', borderRadius: '6px', padding: '12px', fontSize: '11px', color: '#374151', overflowX: 'auto', lineHeight: '1.6', fontFamily: 'monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {JSON.stringify(event.payload, null, 2)}
                  </pre>
                : <p style={{ fontSize: '12px', color: '#9CA3AF' }}>No payload</p>
              }
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default function Audit() {
  const [inquiries, setInquiries]       = useState([])
  const [selectedInquiry, setSelectedInquiry] = useState(null)
  const [events, setEvents]             = useState([])
  const [eventTotal, setEventTotal]     = useState(0)
  const [loadingInquiries, setLoadingInquiries] = useState(true)
  const [loadingEvents, setLoadingEvents]       = useState(false)
  const [selectedEventId, setSelectedEventId]   = useState(null)
  const [eventTypeFilter, setEventTypeFilter]   = useState('')

  // Load all inquiries that have audit events
  useEffect(() => {
    async function load() {
      try {
        // Get all inquiries
        const inqRes = await client.get('/inquiries/')
        const allInquiries = inqRes.data.inquiries || []

        // Get audit events grouped — fetch summary for each inquiry
        // Use the /audit/events endpoint to get unique inquiry_ids
        const auditRes = await client.get('/audit/events', { params: { limit: 500 } })
        const allEvents = auditRes.data.events || []

        // Build unique inquiry set from events
        const inquiryMap = {}
        allEvents.forEach(e => {
          if (e.inquiry_id) {
            if (!inquiryMap[e.inquiry_id]) {
              inquiryMap[e.inquiry_id] = { inquiry_id: e.inquiry_id, count: 0 }
            }
            inquiryMap[e.inquiry_id].count++
          }
        })

        // Merge with inquiry details
        const merged = Object.values(inquiryMap).map(item => {
          const inq = allInquiries.find(i => i.inquiry_id === item.inquiry_id)
          return {
            ...item,
            brand_name: inq?.brand_name || 'Unknown',
            status:     inq?.status || '—',
          }
        }).sort((a, b) => b.count - a.count)

        setInquiries(merged)

        // Auto-select first
        if (merged.length > 0) {
          setSelectedInquiry(merged[0])
        }
      } catch {
        setInquiries([])
      } finally {
        setLoadingInquiries(false)
      }
    }
    load()
  }, [])

  // Load events for selected inquiry
  useEffect(() => {
    if (!selectedInquiry) return
    loadEvents()
  }, [selectedInquiry, eventTypeFilter])

  async function loadEvents() {
    setLoadingEvents(true)
    try {
      const params = { limit: 500 }
      if (eventTypeFilter) params.event_type = eventTypeFilter
      const res = await client.get(`/audit/inquiry/${selectedInquiry.inquiry_id}`, { params })
      // Filter by event type client-side since the inquiry endpoint doesn't support it
      let evts = res.data.events || []
      if (eventTypeFilter) {
        evts = evts.filter(e => e.event_type === eventTypeFilter)
      }
      setEvents(evts)
      setEventTotal(res.data.total_events || evts.length)
    } catch {
      setEvents([])
    } finally {
      setLoadingEvents(false)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '18px', fontWeight: '500', color: '#0A2342', marginBottom: '2px' }}>Audit Trail</h1>
        <p style={{ fontSize: '13px', color: '#6B7280' }}>Immutable event log · grouped by inquiry</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: '0', background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px', overflow: 'hidden', minHeight: '500px' }}>

        {/* Left — inquiry list */}
        <div style={{ borderRight: '0.5px solid #E5E7EB', background: '#FAFAFA' }}>
          <div style={{ padding: '14px 16px', borderBottom: '0.5px solid #E5E7EB' }}>
            <div style={{ fontSize: '13px', fontWeight: '500', color: '#0A2342' }}>Inquiries</div>
            <div style={{ fontSize: '11px', color: '#9CA3AF', marginTop: '2px' }}>
              {loadingInquiries ? 'Loading...' : `${inquiries.length} with audit events`}
            </div>
          </div>

          {inquiries.map(inq => (
            <div
              key={inq.inquiry_id}
              onClick={() => setSelectedInquiry(inq)}
              style={{
                padding: '12px 16px',
                borderBottom: '0.5px solid #F3F4F6',
                cursor: 'pointer',
                borderLeft: selectedInquiry?.inquiry_id === inq.inquiry_id ? '3px solid #0A2342' : '3px solid transparent',
                background: selectedInquiry?.inquiry_id === inq.inquiry_id ? '#EEF2FF' : 'transparent',
              }}
            >
              <div style={{ fontSize: '11px', fontFamily: 'monospace', color: '#6B7280', marginBottom: '2px' }}>{inq.inquiry_id}</div>
              <div style={{ fontSize: '13px', fontWeight: '500', color: '#0A2342', marginBottom: '4px' }}>{inq.brand_name}</div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={{ fontSize: '11px', padding: '1px 6px', borderRadius: '10px', background: '#EEF2FF', color: '#0A2342' }}>
                  {inq.count} events
                </span>
                <span style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'capitalize' }}>
                  {inq.status?.replace(/_/g, ' ')}
                </span>
              </div>
            </div>
          ))}

          {!loadingInquiries && inquiries.length === 0 && (
            <div style={{ padding: '24px 16px', fontSize: '12px', color: '#9CA3AF', textAlign: 'center' }}>
              No audit events yet
            </div>
          )}
        </div>

        {/* Right — event timeline */}
        <div>
          {!selectedInquiry ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#9CA3AF', fontSize: '13px' }}>
              Select an inquiry to view its audit trail
            </div>
          ) : (
            <>
              {/* Header */}
              <div style={{ padding: '14px 16px', borderBottom: '0.5px solid #E5E7EB', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: '500', color: '#0A2342' }}>
                    {selectedInquiry.inquiry_id} — {selectedInquiry.brand_name}
                  </div>
                  <div style={{ fontSize: '11px', color: '#9CA3AF', marginTop: '2px' }}>
                    {loadingEvents ? 'Loading...' : `${events.length} events · oldest first`}
                  </div>
                </div>
                <select
                  value={eventTypeFilter}
                  onChange={e => setEventTypeFilter(e.target.value)}
                  style={{ padding: '6px 10px', fontSize: '12px', border: '0.5px solid #E5E7EB', borderRadius: '6px', background: 'white', color: '#374151', cursor: 'pointer' }}
                >
                  <option value="">All event types</option>
                  {Object.entries(EVENT_CONFIG).map(([key, cfg]) => (
                    <option key={key} value={key}>{cfg.label}</option>
                  ))}
                </select>
              </div>

              {/* Events */}
              {loadingEvents && (
                <div style={{ padding: '32px', textAlign: 'center', color: '#9CA3AF', fontSize: '13px' }}>Loading events...</div>
              )}

              {!loadingEvents && events.length === 0 && (
                <div style={{ padding: '32px', textAlign: 'center', color: '#9CA3AF', fontSize: '13px' }}>No events found</div>
              )}

              {!loadingEvents && events.map((e, idx) => (
                <div
                  key={e.event_id}
                  onClick={() => setSelectedEventId(e.event_id)}
                  style={{
                    display: 'flex', gap: '12px', padding: '10px 16px',
                    borderBottom: '0.5px solid #F9FAFB',
                    background: idx % 2 === 0 ? 'white' : '#FAFAFA',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={el => el.currentTarget.style.background = '#F0F9FF'}
                  onMouseLeave={el => el.currentTarget.style.background = idx % 2 === 0 ? 'white' : '#FAFAFA'}
                >
                  <EventDot type={e.event_type} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px', flexWrap: 'wrap' }}>
                      <EventBadge type={e.event_type} />
                      {e.node_name && <span style={{ fontSize: '11px', color: '#6B7280', fontFamily: 'monospace' }}>{e.node_name}</span>}
                      {e.gate_name && <span style={{ fontSize: '11px', padding: '1px 6px', borderRadius: '10px', background: '#FAEEDA', color: '#854F0B' }}>{e.gate_name}</span>}
                    </div>
                    <div style={{ fontSize: '11px', color: '#9CA3AF' }}>
                      {e.actor_type} · {e.actor_id}
                    </div>
                  </div>
                  <div style={{ fontSize: '11px', color: '#9CA3AF', whiteSpace: 'nowrap', alignSelf: 'center' }}>
                    {new Date(e.created_at).toLocaleString()}
                  </div>
                  <div style={{ alignSelf: 'center', color: '#9CA3AF', fontSize: '12px' }}>→</div>
                </div>
              ))}
            </>
          )}
        </div>
      </div>

      {selectedEventId && (
        <PayloadPanel eventId={selectedEventId} onClose={() => setSelectedEventId(null)} />
      )}
    </div>
  )
}