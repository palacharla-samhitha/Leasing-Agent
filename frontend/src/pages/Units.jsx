import { useEffect, useState } from 'react'
import client from '../api/clients'
import { useAuth } from '../context/AuthContext'

const STATUS_COLORS = {
  vacant:               { bg: '#E1F5EE', color: '#0F6E56' },
  expiring_soon:        { bg: '#FAEEDA', color: '#854F0B' },
  reserved_informally:  { bg: '#EEF2FF', color: '#0A2342' },
  signed_unoccupied:    { bg: '#F3F4F6', color: '#6B7280' },
  held_strategically:   { bg: '#FCEBEB', color: '#A32D2D' },
}

function StatusBadge({ status }) {
  const cfg = STATUS_COLORS[status] || { bg: '#F3F4F6', color: '#6B7280' }
  return (
    <span style={{ fontSize: '10px', padding: '2px 8px', borderRadius: '20px', background: cfg.bg, color: cfg.color, fontWeight: '500', whiteSpace: 'nowrap' }}>
      {status?.replace(/_/g, ' ')}
    </span>
  )
}

function DemandBar({ score }) {
  if (score === null || score === undefined) return null
  const pct   = Math.round(score * 100)
  const color = pct >= 70 ? '#00C4B4' : pct >= 40 ? '#EF9F27' : '#E24B4A'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <div style={{ width: '50px', height: '4px', background: '#F3F4F6', borderRadius: '2px', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: '2px' }} />
      </div>
      <span style={{ fontSize: '11px', color, fontWeight: '500' }}>{pct}</span>
    </div>
  )
}

function UnitCard({ unit, isAdmin, onClick }) {
  const available = unit.status === 'vacant' || unit.status === 'expiring_soon'
  return (
    <div
      onClick={onClick}
      style={{
        background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px',
        padding: '16px', cursor: 'pointer',
        opacity: available ? 1 : 0.7,
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = '#00C4B4'}
      onMouseLeave={e => e.currentTarget.style.borderColor = '#E5E7EB'}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
        <div>
          <div style={{ fontSize: '13px', fontWeight: '500', color: '#0A2342', marginBottom: '2px' }}>{unit.unit_id}</div>
          <div style={{ fontSize: '11px', color: '#6B7280' }}>{unit.property_name} · {unit.floor}</div>
        </div>
        <StatusBadge status={unit.status} />
      </div>

      {/* Zone */}
      <div style={{ fontSize: '12px', color: '#374151', marginBottom: '10px', fontWeight: '500' }}>{unit.zone}</div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '10px' }}>
        <div>
          <div style={{ fontSize: '10px', color: '#9CA3AF' }}>Size</div>
          <div style={{ fontSize: '14px', fontWeight: '500', color: '#0A2342' }}>{unit.sqm} sqm</div>
        </div>
        {isAdmin && (
          <div>
            <div style={{ fontSize: '10px', color: '#9CA3AF' }}>Base rent</div>
            <div style={{ fontSize: '14px', fontWeight: '500', color: '#0A2342' }}>
              {unit.base_rent_sqm ? `AED ${unit.base_rent_sqm}/sqm` : '—'}
            </div>
          </div>
        )}
        {!isAdmin && (
          <div>
            <div style={{ fontSize: '10px', color: '#9CA3AF' }}>Type</div>
            <div style={{ fontSize: '14px', fontWeight: '500', color: '#0A2342', textTransform: 'capitalize' }}>{unit.unit_type}</div>
          </div>
        )}
      </div>

      {/* Demand score — admin only */}
      {isAdmin && unit.vp_demand_score !== null && unit.vp_demand_score !== undefined && (
        <div style={{ marginBottom: '10px' }}>
          <div style={{ fontSize: '10px', color: '#9CA3AF', marginBottom: '3px' }}>Demand score</div>
          <DemandBar score={unit.vp_demand_score} />
        </div>
      )}

      {/* Category tags */}
      {unit.category_fit?.length > 0 && (
        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
          {unit.category_fit.slice(0, 3).map(c => (
            <span key={c} style={{ fontSize: '10px', padding: '1px 6px', borderRadius: '10px', background: '#EEF2FF', color: '#0A2342' }}>{c}</span>
          ))}
        </div>
      )}

      {/* Customer CTA */}
      {!isAdmin && available && (
        <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '0.5px solid #F3F4F6' }}>
          <span style={{ fontSize: '11px', color: '#00C4B4', fontWeight: '500' }}>Available · Enquire for pricing →</span>
        </div>
      )}
    </div>
  )
}

function UnitDetail({ unit, isAdmin, onClose }) {
  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.4)', zIndex: 100,
      display: 'flex', alignItems: 'flex-start', justifyContent: 'flex-end',
    }} onClick={onClose}>
      <div
        style={{ background: 'white', width: '420px', height: '100%', overflowY: 'auto', padding: '24px', boxShadow: '-4px 0 16px rgba(0,0,0,0.08)' }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: '500', color: '#0A2342', marginBottom: '2px' }}>{unit.unit_id}</h2>
            <p style={{ fontSize: '12px', color: '#6B7280' }}>{unit.property_name} · {unit.floor} · {unit.zone}</p>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '18px', color: '#9CA3AF', cursor: 'pointer' }}>✕</button>
        </div>

        <StatusBadge status={unit.status} />

        <div style={{ marginTop: '16px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div style={{ background: '#F9FAFB', borderRadius: '6px', padding: '10px' }}>
            <div style={{ fontSize: '11px', color: '#9CA3AF' }}>Size</div>
            <div style={{ fontSize: '16px', fontWeight: '500', color: '#0A2342' }}>{unit.sqm} sqm</div>
          </div>
          <div style={{ background: '#F9FAFB', borderRadius: '6px', padding: '10px' }}>
            <div style={{ fontSize: '11px', color: '#9CA3AF' }}>Frontage</div>
            <div style={{ fontSize: '16px', fontWeight: '500', color: '#0A2342' }}>{unit.frontage_m ? `${unit.frontage_m}m` : '—'}</div>
          </div>
          {isAdmin && (
            <>
              <div style={{ background: '#F9FAFB', borderRadius: '6px', padding: '10px' }}>
                <div style={{ fontSize: '11px', color: '#9CA3AF' }}>Base rent</div>
                <div style={{ fontSize: '16px', fontWeight: '500', color: '#0A2342' }}>{unit.base_rent_sqm ? `AED ${unit.base_rent_sqm}` : '—'}</div>
              </div>
              <div style={{ background: '#F9FAFB', borderRadius: '6px', padding: '10px' }}>
                <div style={{ fontSize: '11px', color: '#9CA3AF' }}>Fit-out months</div>
                <div style={{ fontSize: '16px', fontWeight: '500', color: '#0A2342' }}>{unit.typical_fit_out_months || '—'}</div>
              </div>
            </>
          )}
        </div>

        {isAdmin && unit.vp_demand_signal && (
          <div style={{ marginTop: '16px', background: '#F0F9FF', border: '0.5px solid #BAE6FD', borderRadius: '6px', padding: '12px' }}>
            <div style={{ fontSize: '11px', color: '#0369A1', fontWeight: '500', marginBottom: '4px' }}>Demand signal</div>
            <div style={{ fontSize: '12px', color: '#0C4A6E', lineHeight: '1.5' }}>{unit.vp_demand_signal}</div>
          </div>
        )}

        {unit.notes && (
          <div style={{ marginTop: '12px', background: '#F9FAFB', borderRadius: '6px', padding: '12px' }}>
            <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '4px' }}>Notes</div>
            <div style={{ fontSize: '12px', color: '#374151', lineHeight: '1.5' }}>{unit.notes}</div>
          </div>
        )}

        {unit.category_fit?.length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '6px' }}>Category fit</div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {unit.category_fit.map(c => (
                <span key={c} style={{ fontSize: '11px', padding: '3px 8px', borderRadius: '20px', background: '#EEF2FF', color: '#0A2342' }}>{c}</span>
              ))}
            </div>
          </div>
        )}

        {!isAdmin && (unit.status === 'vacant' || unit.status === 'expiring_soon') && (
          <div style={{ marginTop: '20px', padding: '16px', background: '#F0FDF4', border: '0.5px solid #BBF7D0', borderRadius: '8px' }}>
            <div style={{ fontSize: '13px', fontWeight: '500', color: '#0F6E56', marginBottom: '4px' }}>Interested in this unit?</div>
            <div style={{ fontSize: '12px', color: '#166534' }}>Submit an inquiry and our leasing team will be in touch with pricing details.</div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Units() {
  const { role } = useAuth()
  const isAdmin  = role === 'admin'

  const [units, setUnits]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [selected, setSelected] = useState(null)

  const [propertyFilter, setPropertyFilter] = useState('')
  const [statusFilter, setStatusFilter]     = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [sizeMin, setSizeMin]               = useState('')
  const [sizeMax, setSizeMax]               = useState('')
  const [search, setSearch]                 = useState('')

  useEffect(() => { load() }, [propertyFilter, statusFilter, categoryFilter, sizeMin, sizeMax])

  async function load() {
    setLoading(true)
    try {
      const params = {}
      if (propertyFilter) params.property_id = propertyFilter
      if (statusFilter)   params.status      = statusFilter
      if (categoryFilter) params.category    = categoryFilter
      if (sizeMin)        params.size_min    = sizeMin
      if (sizeMax)        params.size_max    = sizeMax
      const res = await client.get('/units/', { params })
      setUnits(res.data.units || [])
    } catch {
      setError('Failed to load units')
    } finally {
      setLoading(false)
    }
  }

  const filtered = units.filter(u =>
    !search ||
    u.unit_id?.toLowerCase().includes(search.toLowerCase()) ||
    u.zone?.toLowerCase().includes(search.toLowerCase()) ||
    u.property_name?.toLowerCase().includes(search.toLowerCase())
  )

  const properties = [...new Set(units.map(u => u.property_id))].map(id => {
    const u = units.find(x => x.property_id === id)
    return { id, name: u?.property_name || id }
  })

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '18px', fontWeight: '500', color: '#0A2342', marginBottom: '2px' }}>Units</h1>
        <p style={{ fontSize: '13px', color: '#6B7280' }}>
          {isAdmin ? 'All leasable units across the portfolio' : 'Browse available spaces'} · {filtered.length} units
        </p>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <input
          type="text" placeholder="Search unit, zone, mall..."
          value={search} onChange={e => setSearch(e.target.value)}
          style={{ flex: 1, minWidth: '160px', padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', outline: 'none', background: 'white', color: '#374151' }}
        />
        <select value={propertyFilter} onChange={e => setPropertyFilter(e.target.value)}
          style={{ padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', background: 'white', color: '#374151', cursor: 'pointer' }}>
          <option value="">All properties</option>
          {properties.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          style={{ padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', background: 'white', color: '#374151', cursor: 'pointer' }}>
          <option value="">All statuses</option>
          <option value="vacant">Vacant</option>
          <option value="expiring_soon">Expiring soon</option>
          {isAdmin && <option value="reserved_informally">Reserved</option>}
          {isAdmin && <option value="signed_unoccupied">Signed</option>}
          {isAdmin && <option value="held_strategically">Held</option>}
        </select>
        <input
          type="number" placeholder="Min sqm"
          value={sizeMin} onChange={e => setSizeMin(e.target.value)}
          style={{ width: '90px', padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', outline: 'none', background: 'white', color: '#374151' }}
        />
        <input
          type="number" placeholder="Max sqm"
          value={sizeMax} onChange={e => setSizeMax(e.target.value)}
          style={{ width: '90px', padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', outline: 'none', background: 'white', color: '#374151' }}
        />
        {(propertyFilter || statusFilter || categoryFilter || sizeMin || sizeMax || search) && (
          <button onClick={() => { setPropertyFilter(''); setStatusFilter(''); setCategoryFilter(''); setSizeMin(''); setSizeMax(''); setSearch('') }}
            style={{ padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', background: 'white', color: '#6B7280', cursor: 'pointer' }}>
            Clear
          </button>
        )}
      </div>

      {error && (
        <div style={{ background: '#FCEBEB', border: '0.5px solid #F7C1C1', borderRadius: '8px', padding: '12px 16px', color: '#A32D2D', fontSize: '13px', marginBottom: '16px' }}>{error}</div>
      )}

      {loading && (
        <div style={{ textAlign: 'center', padding: '40px', color: '#9CA3AF', fontSize: '13px' }}>Loading units...</div>
      )}

      {!loading && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '14px' }}>
          {filtered.map(unit => (
            <UnitCard key={unit.unit_id} unit={unit} isAdmin={isAdmin} onClick={() => setSelected(unit)} />
          ))}
          {filtered.length === 0 && (
            <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: '40px', color: '#9CA3AF', fontSize: '13px' }}>No units found</div>
          )}
        </div>
      )}

      {selected && <UnitDetail unit={selected} isAdmin={isAdmin} onClose={() => setSelected(null)} />}
    </div>
  )
}
