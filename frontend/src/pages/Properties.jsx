import { useEffect, useState } from 'react'
import client from '../api/clients'
import { useAuth } from '../context/AuthContext'

function OccupancyBar({ pct }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <div style={{ width: '80px', height: '5px', background: '#F3F4F6', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: '#00C4B4', borderRadius: '3px' }} />
      </div>
      <span style={{ fontSize: '12px', color: '#374151' }}>{pct}%</span>
    </div>
  )
}

function PropertyCard({ prop, isAdmin, onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: 'white', border: '0.5px solid #E5E7EB', borderRadius: '10px',
        padding: '20px', cursor: 'pointer', transition: 'box-shadow 0.15s',
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = '#00C4B4'}
      onMouseLeave={e => e.currentTarget.style.borderColor = '#E5E7EB'}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
        <div>
          <div style={{ fontSize: '15px', fontWeight: '500', color: '#0A2342', marginBottom: '2px' }}>{prop.name}</div>
          <div style={{ fontSize: '12px', color: '#6B7280' }}>{prop.address_city}, {prop.address_country}</div>
        </div>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {prop.ejari_applicable && (
            <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '20px', background: '#E1F5EE', color: '#0F6E56', fontWeight: '500' }}>EJARI</span>
          )}
          <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '20px', background: '#EEF2FF', color: '#0A2342', fontWeight: '500' }}>{prop.code}</span>
        </div>
      </div>

      {/* Divider */}
      <div style={{ borderTop: '0.5px solid #F3F4F6', margin: '12px 0' }} />

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '12px' }}>
        <div>
          <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '2px' }}>Total units</div>
          <div style={{ fontSize: '18px', fontWeight: '500', color: '#0A2342' }}>{prop.total_units}</div>
        </div>
        <div>
          <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '2px' }}>Vacant</div>
          <div style={{ fontSize: '18px', fontWeight: '500', color: '#EF9F27' }}>{prop.vacant_units}</div>
        </div>
        <div>
          <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '2px' }}>Expiring</div>
          <div style={{ fontSize: '18px', fontWeight: '500', color: '#E24B4A' }}>{prop.expiring_units}</div>
        </div>
      </div>

      {/* Occupancy — admin only */}
      {isAdmin && (
        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '4px' }}>Occupancy</div>
          <OccupancyBar pct={parseFloat(prop.signed_units > 0 ? Math.round((prop.signed_units / prop.total_units) * 100) : 0)} />
        </div>
      )}

      {/* Footer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '11px', color: '#9CA3AF' }}>{prop.portfolio}</span>
        <span style={{ fontSize: '12px', color: '#00C4B4', fontWeight: '500' }}>View units →</span>
      </div>
    </div>
  )
}

function PropertyDetail({ prop, onClose, isAdmin }) {
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const res = await client.get(`/properties/${prop.property_id}`)
        setDetail(res.data)
      } catch {
        setDetail(null)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [prop.property_id])

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.4)', zIndex: 100,
      display: 'flex', alignItems: 'flex-start', justifyContent: 'flex-end',
    }} onClick={onClose}>
      <div
        style={{ background: 'white', width: '480px', height: '100%', overflowY: 'auto', padding: '24px', boxShadow: '-4px 0 16px rgba(0,0,0,0.08)' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: '500', color: '#0A2342', marginBottom: '2px' }}>{prop.name}</h2>
            <p style={{ fontSize: '12px', color: '#6B7280' }}>{prop.address_city}, {prop.address_country}</p>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '18px', color: '#9CA3AF', cursor: 'pointer' }}>✕</button>
        </div>

        {loading && <p style={{ color: '#9CA3AF', fontSize: '13px' }}>Loading...</p>}

        {detail && (
          <>
            {/* Pricing rules — admin only */}
            {isAdmin && detail.pricing_rules?.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '13px', fontWeight: '500', color: '#0A2342', marginBottom: '10px' }}>Pricing rules</div>
                {detail.pricing_rules.map(r => (
                  <div key={r.rule_id} style={{ background: '#F9FAFB', border: '0.5px solid #E5E7EB', borderRadius: '6px', padding: '10px 12px', marginBottom: '8px' }}>
                    <div style={{ fontSize: '12px', fontWeight: '500', color: '#0A2342', marginBottom: '4px', textTransform: 'capitalize' }}>{r.category}</div>
                    <div style={{ fontSize: '11px', color: '#6B7280' }}>
                      AED {r.base_rent_sqm_min}–{r.base_rent_sqm_max}/sqm · {r.annual_escalation_pct}% escalation · {r.security_deposit_months}mo deposit
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Units */}
            <div>
              <div style={{ fontSize: '13px', fontWeight: '500', color: '#0A2342', marginBottom: '10px' }}>
                Units ({detail.units?.length || 0})
              </div>
              {detail.units?.map(u => (
                <div key={u.unit_id} style={{ border: '0.5px solid #E5E7EB', borderRadius: '6px', padding: '10px 12px', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontSize: '12px', fontWeight: '500', color: '#0A2342' }}>{u.unit_id}</span>
                    <span style={{
                      fontSize: '10px', padding: '2px 6px', borderRadius: '20px', fontWeight: '500',
                      background: u.status === 'vacant' ? '#E1F5EE' : u.status === 'expiring_soon' ? '#FAEEDA' : '#F3F4F6',
                      color: u.status === 'vacant' ? '#0F6E56' : u.status === 'expiring_soon' ? '#854F0B' : '#6B7280',
                    }}>
                      {u.status?.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div style={{ fontSize: '11px', color: '#6B7280' }}>
                    {u.floor} · {u.zone} · {u.sqm} sqm
                    {isAdmin && u.base_rent_sqm ? ` · AED ${u.base_rent_sqm}/sqm` : ''}
                  </div>
                  {u.category_fit?.length > 0 && (
                    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginTop: '6px' }}>
                      {u.category_fit.slice(0, 3).map(c => (
                        <span key={c} style={{ fontSize: '10px', padding: '1px 6px', borderRadius: '10px', background: '#EEF2FF', color: '#0A2342' }}>{c}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default function Properties() {
  const { role } = useAuth()
  const isAdmin  = role === 'admin'

  const [properties, setProperties] = useState([])
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [selected, setSelected]     = useState(null)
  const [countryFilter, setCountryFilter] = useState('')
  const [cityFilter, setCityFilter]       = useState('')
  const [search, setSearch]               = useState('')

  useEffect(() => { load() }, [countryFilter, cityFilter])

  async function load() {
    setLoading(true)
    try {
      const params = { status: 'active' }
      if (countryFilter) params.country = countryFilter
      if (cityFilter)    params.city    = cityFilter
      const res = await client.get('/properties/', { params })
      setProperties(res.data.properties || [])
    } catch {
      setError('Failed to load properties')
    } finally {
      setLoading(false)
    }
  }

  const filtered = properties.filter(p =>
    !search || p.name?.toLowerCase().includes(search.toLowerCase()) || p.address_city?.toLowerCase().includes(search.toLowerCase())
  )

  const countries = [...new Set(properties.map(p => p.address_country))].sort()
  const cities    = [...new Set(properties.filter(p => !countryFilter || p.address_country === countryFilter).map(p => p.address_city))].sort()

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '18px', fontWeight: '500', color: '#0A2342', marginBottom: '2px' }}>Properties</h1>
        <p style={{ fontSize: '13px', color: '#6B7280' }}>
          {isAdmin ? 'MAF Properties portfolio' : 'Browse MAF shopping destinations'} · {filtered.length} properties
        </p>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <input
          type="text" placeholder="Search properties..."
          value={search} onChange={e => setSearch(e.target.value)}
          style={{ flex: 1, minWidth: '180px', padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', outline: 'none', background: 'white', color: '#374151' }}
        />
        <select value={countryFilter} onChange={e => { setCountryFilter(e.target.value); setCityFilter('') }}
          style={{ padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', background: 'white', color: '#374151', cursor: 'pointer' }}>
          <option value="">All countries</option>
          {countries.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={cityFilter} onChange={e => setCityFilter(e.target.value)}
          style={{ padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', background: 'white', color: '#374151', cursor: 'pointer' }}>
          <option value="">All cities</option>
          {cities.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        {(countryFilter || cityFilter || search) && (
          <button onClick={() => { setCountryFilter(''); setCityFilter(''); setSearch('') }}
            style={{ padding: '8px 12px', fontSize: '13px', border: '0.5px solid #E5E7EB', borderRadius: '6px', background: 'white', color: '#6B7280', cursor: 'pointer' }}>
            Clear
          </button>
        )}
      </div>

      {error && (
        <div style={{ background: '#FCEBEB', border: '0.5px solid #F7C1C1', borderRadius: '8px', padding: '12px 16px', color: '#A32D2D', fontSize: '13px', marginBottom: '16px' }}>{error}</div>
      )}

      {loading && (
        <div style={{ textAlign: 'center', padding: '40px', color: '#9CA3AF', fontSize: '13px' }}>Loading properties...</div>
      )}

      {/* Grid */}
      {!loading && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
          {filtered.map(prop => (
            <PropertyCard key={prop.property_id} prop={prop} isAdmin={isAdmin} onClick={() => setSelected(prop)} />
          ))}
          {filtered.length === 0 && (
            <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: '40px', color: '#9CA3AF', fontSize: '13px' }}>
              No properties found
            </div>
          )}
        </div>
      )}

      {/* Detail panel */}
      {selected && <PropertyDetail prop={selected} onClose={() => setSelected(null)} isAdmin={isAdmin} />}
    </div>
  )
}
