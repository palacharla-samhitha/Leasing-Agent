import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const ADMIN_LINKS = [
  { to: '/dashboard',  label: 'Dashboard',   icon: '▦' },
  { to: '/inquiries',  label: 'Inquiries',   icon: '◈' },
  { to: '/workflow',   label: 'Workflow',     icon: '⬡' },
  { to: '/properties', label: 'Properties',  icon: '⊞' },
  { to: '/units',      label: 'Units',       icon: '⊟' },
  { to: '/audit',      label: 'Audit Trail', icon: '≡' },
]

const CUSTOMER_LINKS = [
  { to: '/properties',  label: 'Properties',    icon: '⊞' },
  { to: '/units',       label: 'Units',         icon: '⊟' },
  { to: '/inquiry/new', label: 'Submit Inquiry', icon: '+' },
]

export default function Sidebar() {
  const { role } = useAuth()
  const links = role === 'admin' ? ADMIN_LINKS : CUSTOMER_LINKS

  return (
    <aside
      style={{ background: '#0A2342', width: '200px', flexShrink: 0 }}
      className="flex flex-col py-4 overflow-y-auto"
    >

      {/* Section label */}
      <div className="px-4 mb-3">
        <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: '10px', letterSpacing: '1px', textTransform: 'uppercase' }}>
          {role === 'admin' ? 'Admin Panel' : 'Explorer'}
        </span>
      </div>

      {/* Nav links */}
      <nav className="flex flex-col gap-1 px-2">
        {links.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '8px 12px',
              borderRadius: '6px',
              fontSize: '13px',
              fontWeight: isActive ? '500' : '400',
              color: isActive ? '#00C4B4' : 'rgba(255,255,255,0.6)',
              background: isActive ? 'rgba(0,196,180,0.1)' : 'transparent',
              textDecoration: 'none',
              transition: 'all 0.15s',
            })}
          >
            <span style={{ fontSize: '14px', width: '16px', textAlign: 'center' }}>{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Bottom — version */}
      <div className="mt-auto px-4">
        <span style={{ color: 'rgba(255,255,255,0.2)', fontSize: '10px' }}>
          v2.0 · Phase 2
        </span>
      </div>
    </aside>
  )
}