import { useEffect, useState } from 'react'
import client from '../api/clients'

const EVENT_CONFIG = {
  node_completed:      { label: 'Node completed',      color: '#0A2342', bg: '#EEF2FF' },
  llm_called:          { label: 'LLM called',          color: '#0F6E56', bg: '#E1F5EE' },
  llm_failed:          { label: 'LLM failed',          color: '#A32D2D', bg: '#FCEBEB' },
  fallback_triggered:  { label: 'Fallback triggered',  color: '#854F0B', bg: '#FAEEDA' },
  gate_reached:        { label: 'Gate reached',        color: '#854F0B', bg: '#FAEEDA' },
  gate_approved:       { label: 'Gate approved',       color: '#0F6E56', bg: '#E1F5EE' },
  gate_rejected:       { label: 'Gate rejected',       color: '#A32D2D', bg: '#FCEBEB' },
  ejari_filed:         { label: 'EJARI filed',         color: '#0F6E56', bg: '#E1F5EE' },
  error_occurred:      { label: 'Error occurred',      color: '#A32D2D', bg: '#FCEBEB' },
}

function EventBadge({ type }) {
  const cfg = EVENT_CONFIG[type] || { label: type, color: '#6B7280', bg: '#F3F4F6' }
  return (
    <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '20px', background: cfg.bg, color: cfg.color, fontWeight: '500', whiteSpace: 'nowrap' }}>
      {cfg.label}
    </span>
  )
}

function EventDot({ type }) {
  const cfg = EVENT_CONFIG[type] || { color: '#9CA3AF' }
  return (
    <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: cfg.color, flexShrink: 0, marginTop: '3px' }} />
  )
}

function PayloadViewer({ eventId, onClose }) {
  const [event, setEvent]   = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const res = await client.get(`/audit/events/${eventId}`)
        setEvent(res.data.event)
      } catch {
        setEvent(null)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [eventId])

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.4)', zIndex: 100,
      display: 'flex', alignItems: 'flex-start', justifyContent: 'flex-end',
    }} onClick={onClose}>
      <div
        style={{ background: 'white', width: '500px', height: '100%', overflowY: 'auto', padding: '24px', boxShadow: '-4px 0 16px rgba(0,0,0,0.08)' }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '15px', fontWeight: '500', color: '#0A2342' }}>Event detail</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '18px', color: '#9CA3AF', cursor: 'pointer' }}>✕</button>
        </div>

        {loading && <p style={{ color: '#9CA3AF', fontSize: '13px' }}>Loading...</p>}

        {event && (
          <>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '12px', color: '#9CA3AF' }}>Event type</span>
                <EventBadge type={event.event_type} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '12px', color: '#9CA3AF' }}>Node</span>
                <span style={{ fontSize: '12px', color: '#374151', fontFamily: 'monospace' }}>{event.node_name || '—'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '12px', color: '#9CA3AF' }}>Inquiry</span>
                <span style={{ fontSize: '12px', color: '#374151', fontFamily: 'monospace' }}>{event.inquiry_id || '—'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '12px', color: '#9CA3AF' }}>Actor</span>
                <span style={{ fontSize: '12px', color: '#374151' }}>{event.actor_type} · {event.actor_id}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '12px', color: '#9CA3AF' }}>Timestamp</span>
                <span style={{ fontSize: '12px', color: '#374151' }}>{new Date(event.created_at).toLocaleString()}</span>
              </div>
            </div>

            <div style={{ borderTop: '0.5px solid #F3F4F6', paddingTop: '16px' }}>
              <div style={{ fontSize: '12px', fontWeight: '500', color: '#0A2342', marginBottom: '8px' }}>Payload</div>
              {event.payload ? (
                <pre style={{
                  background: '#F9FAFB', border: '0.5px solid #E5E7EB', borderRadius: '6px',
                  padding: '12px', fontSize: '11px', color: '#374151', overflowX: 'auto',
                  lineHeight: '1.6', fontFamily: 'monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                }}>
                  {JSON.stringify(event.payload, null, 2)}
                </pre>
              ) : (
                <p style={{ fontSize: '12px', color: '#9CA3AF' }}>No payload</p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default function Audit() {
  const [events, setEvents]         = useState([])
  const [total, setTotal]           = useState(0)
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [selectedId, setSelectedId] = useState(null)

  const [eventTypeFilter, setEventTypeFilter] = useState('')
  const [inquiryFilter, setInquiryFilter]     = useState('')
  const [inquiryInput, setInquiryInput]       = useState('')
  const [offset, setOffset]                   = useState(0)
  const LIMIT = 50

  useEffect(() => { load() }, [eventTypeFilter, inquiryFilter, offset])

  async function load() {
    setLoading(true)
    try {
      const params = { limit: LIMIT, offset }
      if (eventTypeFilter) params.event_type = eventTypeFilter
      if (inquiryFilter)   params.inquiry_id = inquiryFilter
      const res = await client.get('/audit/events', { params })
      setEvents(res.data.events || [])
      setTotal(res.data.total || 0)
    } catch {
      setError('Failed to load audit events')
    } finally {
      setLoading(false)
    }
  }

  function handleInquirySearch() {
    setInquiryFilter(inquiryInput.trim())
    setOffset(0)
  }

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '18px', fontWeight: '500', color: '#0A2342', marginBottom: '2px' }}>Audit Trail</h1>
        <p style={{ fontSize: '13px', color: '#6B7280' }}>Immutable event log · {total} total events</p>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <select value={eventTypeFilter} onChange={e => { setEventTypeFilter(e.target.value); setOffset(0) }}
          style={{ padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', background: 'white', color: '#374151', cursor: 'pointer' }}>
          <option value="">All event types</option>
          {Object.entries(EVENT_CONFIG).map(([key, cfg]) => (
            <option key={key} value={key}>{cfg.label}</option>
          ))}
        </select>

        <div style={{ display: 'flex', gap: '6px', flex: 1, minWidth: '240px' }}>
          <input
            type="text" placeholder="Filter by inquiry ID e.g. INQ-2026-0041"
            value={inquiryInput} onChange={e => setInquiryInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleInquirySearch()}
            style={{ flex: 1, padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', outline: 'none', background: 'white', color: '#374151' }}
          />
          <button onClick={handleInquirySearch}
            style={{ padding: '8px 14px', fontSize: '13px', background: '#0A2342', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
            Search
          </button>
        </div>

        {(eventTypeFilter || inquiryFilter) && (
          <button onClick={() => { setEventTypeFilter(''); setInquiryFilter(''); setInquiryInput(''); setOffset(0) }}
            style={{ padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', background: 'white', color: '#6B7280', cursor: 'pointer' }}>
            Clear
          </button>
        )}
      </div>

      {error && (
        <div style={{ background: '#FCEBEB', border: '0.5px solid #F7C1C1', borderRadius: '8px', padding: '12px 16px', color: '#A32D2D', fontSize: '13px', marginBottom: '16px' }}>{error}</div>
      )}

      {/* Event timeline */}
      <div style={{ background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px', overflow: 'hidden' }}>
        {loading && (
          <div style={{ padding: '32px', textAlign: 'center', color: '#9CA3AF', fontSize: '13px' }}>Loading events...</div>
        )}

        {!loading && events.length === 0 && (
          <div style={{ padding: '32px', textAlign: 'center', color: '#9CA3AF', fontSize: '13px' }}>No events found</div>
        )}

        {!loading && events.map((e, idx) => (
          <div
            key={e.event_id}
            style={{
              display: 'flex', gap: '14px', padding: '12px 16px',
              borderBottom: idx < events.length - 1 ? '0.5px solid #F9FAFB' : 'none',
              background: idx % 2 === 0 ? 'white' : '#FAFAFA',
              cursor: 'pointer',
            }}
            onMouseEnter={el => el.currentTarget.style.background = '#F0F9FF'}
            onMouseLeave={el => el.currentTarget.style.background = idx % 2 === 0 ? 'white' : '#FAFAFA'}
            onClick={() => setSelectedId(e.event_id)}
          >
            <EventDot type={e.event_type} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
                <EventBadge type={e.event_type} />
                {e.node_name && (
                  <span style={{ fontSize: '11px', color: '#6B7280', fontFamily: 'monospace' }}>{e.node_name}</span>
                )}
                {e.gate_name && (
                  <span style={{ fontSize: '11px', padding: '1px 6px', borderRadius: '10px', background: '#FAEEDA', color: '#854F0B' }}>{e.gate_name}</span>
                )}
              </div>
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                {e.inquiry_id && (
                  <span style={{ fontSize: '11px', color: '#9CA3AF', fontFamily: 'monospace' }}>{e.inquiry_id}</span>
                )}
                <span style={{ fontSize: '11px', color: '#9CA3AF' }}>{e.actor_type} · {e.actor_id}</span>
              </div>
            </div>
            <div style={{ fontSize: '11px', color: '#9CA3AF', whiteSpace: 'nowrap', alignSelf: 'center' }}>
              {new Date(e.created_at).toLocaleString()}
            </div>
            <div style={{ alignSelf: 'center', color: '#9CA3AF', fontSize: '12px' }}>→</div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {total > LIMIT && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px' }}>
          <span style={{ fontSize: '12px', color: '#6B7280' }}>
            Showing {offset + 1}–{Math.min(offset + LIMIT, total)} of {total} events
          </span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setOffset(Math.max(0, offset - LIMIT))}
              disabled={offset === 0}
              style={{ padding: '6px 14px', fontSize: '12px', border: '0.5px solid #E5E7EB', borderRadius: '6px', background: 'white', color: offset === 0 ? '#D1D5DB' : '#374151', cursor: offset === 0 ? 'default' : 'pointer' }}
            >
              Previous
            </button>
            <button
              onClick={() => setOffset(offset + LIMIT)}
              disabled={offset + LIMIT >= total}
              style={{ padding: '6px 14px', fontSize: '12px', border: '0.5px solid #E5E7EB', borderRadius: '6px', background: 'white', color: offset + LIMIT >= total ? '#D1D5DB' : '#374151', cursor: offset + LIMIT >= total ? 'default' : 'pointer' }}
            >
              Next
            </button>
          </div>
        </div>
      )}

      {selectedId && <PayloadViewer eventId={selectedId} onClose={() => setSelectedId(null)} />}
    </div>
  )
}
