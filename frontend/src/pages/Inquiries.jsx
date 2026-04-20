import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/clients'

const STATUS_CONFIG = {
  in_progress:       { label: 'In progress',     bg: '#EEF2FF', color: '#0A2342' },
  pending_gate_1:    { label: 'Pending Gate 1',  bg: '#E1F5EE', color: '#0F6E56' },
  blocked_documents: { label: 'Blocked — docs',  bg: '#FAEEDA', color: '#854F0B' },
  unit_matched:      { label: 'Unit matched',    bg: '#E1F5EE', color: '#0F6E56' },
  completed:         { label: 'Completed',       bg: '#E1F5EE', color: '#0F6E56' },
  cancelled:         { label: 'Cancelled',       bg: '#F3F4F6', color: '#6B7280' },
}

const GRADE_CONFIG = {
  A: { bg: '#E1F5EE', color: '#0F6E56' },
  B: { bg: '#FAEEDA', color: '#854F0B' },
  C: { bg: '#FCEBEB', color: '#A32D2D' },
}

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || { label: status, bg: '#F3F4F6', color: '#6B7280' }
  return (
    <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '20px', background: cfg.bg, color: cfg.color, fontWeight: '500', whiteSpace: 'nowrap' }}>
      {cfg.label}
    </span>
  )
}

function GradeBadge({ grade }) {
  if (!grade) return <span style={{ color: '#9CA3AF', fontSize: '12px' }}>—</span>
  const cfg = GRADE_CONFIG[grade] || { bg: '#F3F4F6', color: '#6B7280' }
  return (
    <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '20px', background: cfg.bg, color: cfg.color, fontWeight: '600' }}>
      {grade}
    </span>
  )
}

function PriorityDot({ priority }) {
  const color = priority === 'high' ? '#E24B4A' : priority === 'medium' ? '#EF9F27' : '#9CA3AF'
  return <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: color, marginRight: '6px' }} />
}

export default function Inquiries() {
  const navigate = useNavigate()
  const [inquiries, setInquiries] = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [statusFilter,   setStatusFilter]   = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [search,         setSearch]         = useState('')

  useEffect(() => { load() }, [statusFilter, priorityFilter])

  async function load() {
    setLoading(true)
    try {
      const params = {}
      if (statusFilter)   params.status   = statusFilter
      if (priorityFilter) params.priority = priorityFilter
      const res = await client.get('/inquiries/', { params })
      setInquiries(res.data.inquiries || [])
    } catch {
      setError('Failed to load inquiries')
    } finally {
      setLoading(false)
    }
  }

  const filtered = inquiries.filter(i =>
    !search ||
    i.brand_name?.toLowerCase().includes(search.toLowerCase()) ||
    i.inquiry_id?.toLowerCase().includes(search.toLowerCase()) ||
    i.category?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '18px', fontWeight: '500', color: '#0A2342', marginBottom: '2px' }}>Inquiries</h1>
        <p style={{ fontSize: '13px', color: '#6B7280' }}>All tenant leasing inquiries · {filtered.length} results</p>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder="Search brand, ID, category..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ flex: 1, minWidth: '200px', padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', outline: 'none', background: 'white', color: '#374151' }}
        />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          style={{ padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', background: 'white', color: '#374151', cursor: 'pointer' }}>
          <option value="">All statuses</option>
          <option value="in_progress">In progress</option>
          <option value="pending_gate_1">Pending Gate 1</option>
          <option value="blocked_documents">Blocked — docs</option>
          <option value="unit_matched">Unit matched</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)}
          style={{ padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', background: 'white', color: '#374151', cursor: 'pointer' }}>
          <option value="">All priorities</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        {(statusFilter || priorityFilter || search) && (
          <button onClick={() => { setStatusFilter(''); setPriorityFilter(''); setSearch('') }}
            style={{ padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', background: 'white', color: '#6B7280', cursor: 'pointer' }}>
            Clear
          </button>
        )}
      </div>

      {error && (
        <div style={{ background: '#FCEBEB', border: '0.5px solid #F7C1C1', borderRadius: '8px', padding: '12px 16px', color: '#A32D2D', fontSize: '13px', marginBottom: '16px' }}>
          {error}
        </div>
      )}

      {/* Table */}
      <div style={{ background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ background: '#F9FAFB' }}>
              {['Inquiry ID', 'Brand', 'Category', 'Mall', 'Priority', 'Lead', 'Status', 'Received', 'Action'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '10px 12px', color: '#6B7280', fontWeight: '500', fontSize: '11px', borderBottom: '0.5px solid #E5E7EB' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={9} style={{ padding: '32px', textAlign: 'center', color: '#9CA3AF', fontSize: '13px' }}>Loading...</td></tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr><td colSpan={9} style={{ padding: '32px', textAlign: 'center', color: '#9CA3AF', fontSize: '13px' }}>No inquiries found</td></tr>
            )}
            {!loading && filtered.map((inq, idx) => (
              <tr key={inq.inquiry_id}
                style={{ borderBottom: '0.5px solid #F3F4F6', background: idx % 2 === 0 ? 'white' : '#FAFAFA', cursor: 'pointer' }}
                onMouseEnter={e => e.currentTarget.style.background = '#F0F9FF'}
                onMouseLeave={e => e.currentTarget.style.background = idx % 2 === 0 ? 'white' : '#FAFAFA'}
              >
                <td style={{ padding: '10px 12px', color: '#6B7280', fontFamily: 'monospace', fontSize: '12px' }}>{inq.inquiry_id}</td>
                <td style={{ padding: '10px 12px', fontWeight: '500', color: '#0A2342' }}>{inq.brand_name}</td>
                <td style={{ padding: '10px 12px', color: '#6B7280', maxWidth: '160px' }}>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'block' }}>{inq.category}</span>
                </td>
                <td style={{ padding: '10px 12px', color: '#6B7280' }}>{inq.preferred_mall_name || inq.preferred_mall || '—'}</td>
                <td style={{ padding: '10px 12px' }}>
                  <PriorityDot priority={inq.priority} />
                  <span style={{ color: '#374151', textTransform: 'capitalize' }}>{inq.priority}</span>
                </td>
                <td style={{ padding: '10px 12px' }}><GradeBadge grade={inq.lead_grade} /></td>
                <td style={{ padding: '10px 12px' }}><StatusBadge status={inq.status} /></td>
                <td style={{ padding: '10px 12px', color: '#9CA3AF', fontSize: '12px', whiteSpace: 'nowrap' }}>
                  {new Date(inq.received_at).toLocaleDateString()}
                </td>
                <td style={{ padding: '10px 12px' }}>
                  <button
                    onClick={() => navigate(`/workflow/${inq.inquiry_id}`)}
                    style={{ padding: '4px 10px', fontSize: '11px', fontWeight: '500', background: '#0A2342', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
