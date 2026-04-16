import { useEffect, useState } from 'react'
import client from '../api/clients'

function StatCard({ label, value, sub, accentColor }) {
  return (
    <div style={{
      background: 'white',
      border: '0.5px solid #E5E7EB',
      borderRadius: '10px',
      padding: '16px',
      borderTop: `3px solid ${accentColor}`,
    }}>
      <div style={{ fontSize: '12px', color: '#6B7280', marginBottom: '6px' }}>{label}</div>
      <div style={{ fontSize: '24px', fontWeight: '500', color: '#0A2342', marginBottom: '2px' }}>{value}</div>
      <div style={{ fontSize: '12px', color: '#9CA3AF' }}>{sub}</div>
    </div>
  )
}

function PipelineBar({ label, count, max, color }) {
  const pct = max > 0 ? (count / max) * 100 : 0
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
      <span style={{ fontSize: '12px', color: '#6B7280', width: '130px', flexShrink: 0 }}>{label}</span>
      <div style={{ flex: 1, background: '#F3F4F6', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: '4px', transition: 'width 0.4s' }} />
      </div>
      <span style={{ fontSize: '12px', fontWeight: '500', color: '#374151', width: '16px', textAlign: 'right' }}>{count}</span>
    </div>
  )
}

function OccupancyBar({ pct }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <div style={{ width: '60px', height: '6px', background: '#F3F4F6', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: '#00C4B4', borderRadius: '3px' }} />
      </div>
      <span style={{ fontSize: '12px', color: '#374151' }}>{pct}%</span>
    </div>
  )
}

function StatusBadge({ pct }) {
  if (pct === 0) return <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '20px', background: '#FCEBEB', color: '#A32D2D', fontWeight: '500' }}>Urgent</span>
  if (pct < 50) return <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '20px', background: '#FAEEDA', color: '#854F0B', fontWeight: '500' }}>Needs attention</span>
  return <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '20px', background: '#E1F5EE', color: '#0F6E56', fontWeight: '500' }}>Healthy</span>
}

const STAGE_CONFIG = [
  { key: 'in_progress',       label: 'In progress',     color: '#0A2342' },
  { key: 'pending_gate_1',    label: 'Pending Gate 1',  color: '#00C4B4' },
  { key: 'blocked_documents', label: 'Blocked — docs',  color: '#EF9F27' },
  { key: 'unit_matched',      label: 'Unit matched',    color: '#639922' },
  { key: 'completed',         label: 'Completed',       color: '#0F6E56' },
  { key: 'cancelled',         label: 'Cancelled',       color: '#B4B2A9' },
]

export default function Dashboard() {
  const [summary, setSummary]   = useState(null)
  const [pipeline, setPipeline] = useState(null)
  const [units, setUnits]       = useState(null)
  const [events, setEvents]     = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)

  useEffect(() => {
    async function load() {
      try {
        const [s, p, u, e] = await Promise.all([
          client.get('/dashboard/summary'),
          client.get('/dashboard/pipeline'),
          client.get('/dashboard/units'),
          client.get('/audit/events?limit=5'),
        ])
        setSummary(s.data)
        setPipeline(p.data)
        setUnits(u.data)
        setEvents(e.data.events || [])
      } catch (err) {
        setError('Failed to load dashboard data')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px', color: '#6B7280', fontSize: '14px' }}>
      Loading dashboard...
    </div>
  )

  if (error) return (
    <div style={{ background: '#FCEBEB', border: '0.5px solid #F7C1C1', borderRadius: '8px', padding: '12px 16px', color: '#A32D2D', fontSize: '13px' }}>
      {error}
    </div>
  )

  const maxPipeline = Math.max(...Object.values(pipeline?.pipeline || {}), 1)

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '18px', fontWeight: '500', color: '#0A2342', marginBottom: '2px' }}>Dashboard</h1>
        <p style={{ fontSize: '13px', color: '#6B7280' }}>Live overview · MAF Properties Portfolio</p>
      </div>

      {summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0,1fr))', gap: '12px', marginBottom: '20px' }}>
          <StatCard label="Active leases" value={summary.active_leases} sub={`AED ${Number(summary.active_lease_value_aed).toLocaleString()} annual value`} accentColor="#00C4B4" />
          <StatCard label="Pipeline inquiries" value={summary.pipeline_inquiries} sub={`AED ${Number(summary.pipeline_value_aed).toLocaleString()} est. value`} accentColor="#0A2342" />
          <StatCard label="Vacant units" value={summary.vacant_units} sub={`${summary.expiring_units} expiring soon`} accentColor="#EF9F27" />
          <StatCard label="Portfolio occupancy" value={`${summary.occupancy_rate}%`} sub={`${summary.occupied_units} of ${summary.total_units} units occupied`} accentColor="#639922" />
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1.6fr)', gap: '16px' }}>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px', padding: '16px' }}>
            <div style={{ fontSize: '14px', fontWeight: '500', color: '#0A2342', marginBottom: '14px', paddingBottom: '10px', borderBottom: '0.5px solid #F3F4F6' }}>
              Pipeline by stage
            </div>
            {pipeline && STAGE_CONFIG.map(({ key, label, color }) => (
              <PipelineBar key={key} label={label} count={pipeline.pipeline[key] || 0} max={maxPipeline} color={color} />
            ))}
          </div>

          <div style={{ background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px', padding: '16px' }}>
            <div style={{ fontSize: '14px', fontWeight: '500', color: '#0A2342', marginBottom: '14px', paddingBottom: '10px', borderBottom: '0.5px solid #F3F4F6' }}>
              Recent activity
            </div>
            {events.length === 0 && <p style={{ fontSize: '12px', color: '#9CA3AF' }}>No recent events</p>}
            {events.map(e => (
              <div key={e.event_id} style={{ display: 'flex', gap: '10px', paddingBottom: '10px', marginBottom: '10px', borderBottom: '0.5px solid #F9FAFB', alignItems: 'flex-start' }}>
                <div style={{
                  width: '8px', height: '8px', borderRadius: '50%', marginTop: '4px', flexShrink: 0,
                  background: e.event_type === 'fallback_triggered' ? '#EF9F27' : e.event_type === 'ejari_filed' ? '#00C4B4' : e.event_type === 'llm_failed' ? '#E24B4A' : '#0A2342'
                }} />
                <div>
                  <div style={{ fontSize: '12px', color: '#374151', lineHeight: '1.4' }}>
                    {e.event_type.replace(/_/g, ' ')} · {e.node_name || 'system'}
                  </div>
                  <div style={{ fontSize: '11px', color: '#9CA3AF', marginTop: '2px' }}>
                    {new Date(e.created_at).toLocaleString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px', padding: '16px' }}>
          <div style={{ fontSize: '14px', fontWeight: '500', color: '#0A2342', marginBottom: '14px', paddingBottom: '10px', borderBottom: '0.5px solid #F3F4F6' }}>
            Vacancy by property
          </div>
          {units && (
            <>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                <thead>
                  <tr>
                    {['Property', 'City', 'Vacant', 'Expiring', 'Occupancy', 'Status'].map(h => (
                      <th key={h} style={{ textAlign: 'left', padding: '6px 8px', color: '#9CA3AF', fontWeight: '500', fontSize: '11px', borderBottom: '0.5px solid #F3F4F6' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {units.properties.map(p => (
                    <tr key={p.property_id}>
                      <td style={{ padding: '8px', borderBottom: '0.5px solid #F9FAFB', fontWeight: '500', color: '#0A2342' }}>{p.property_name}</td>
                      <td style={{ padding: '8px', borderBottom: '0.5px solid #F9FAFB', color: '#6B7280' }}>{p.city}</td>
                      <td style={{ padding: '8px', borderBottom: '0.5px solid #F9FAFB', color: '#374151' }}>{p.vacant_units}</td>
                      <td style={{ padding: '8px', borderBottom: '0.5px solid #F9FAFB', color: '#374151' }}>{p.expiring_units}</td>
                      <td style={{ padding: '8px', borderBottom: '0.5px solid #F9FAFB' }}><OccupancyBar pct={parseFloat(p.occupancy_rate) || 0} /></td>
                      <td style={{ padding: '8px', borderBottom: '0.5px solid #F9FAFB' }}><StatusBadge pct={parseFloat(p.occupancy_rate) || 0} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '0.5px solid #F3F4F6', display: 'flex', gap: '24px' }}>
                <div>
                  <div style={{ fontSize: '11px', color: '#9CA3AF' }}>Total units</div>
                  <div style={{ fontSize: '16px', fontWeight: '500', color: '#0A2342' }}>{units.portfolio.total_units}</div>
                </div>
                <div>
                  <div style={{ fontSize: '11px', color: '#9CA3AF' }}>Total vacant</div>
                  <div style={{ fontSize: '16px', fontWeight: '500', color: '#EF9F27' }}>{units.portfolio.vacant_units}</div>
                </div>
                <div>
                  <div style={{ fontSize: '11px', color: '#9CA3AF' }}>Portfolio occupancy</div>
                  <div style={{ fontSize: '16px', fontWeight: '500', color: '#00C4B4' }}>{units.portfolio.occupancy_rate}%</div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
