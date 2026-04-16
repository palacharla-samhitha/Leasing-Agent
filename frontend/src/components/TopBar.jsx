import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'

export default function TopBar() {
  const { role, setRole } = useAuth()
  const navigate = useNavigate()

  function handleSignOut() {
    setRole(null)
    navigate('/')
  }

  return (
    <header
      style={{ background: '#0A2342', height: '48px', flexShrink: 0 }}
      className="flex items-center justify-between px-5"
    >
      {/* Logo */}
      <div style={{ fontSize: '14px', fontWeight: '500' }}>
        <span style={{ color: '#00C4B4' }}>re</span>
        <span style={{ color: 'white' }}>knew</span>
        <span style={{ color: 'rgba(255,255,255,0.3)', margin: '0 8px' }}>×</span>
        <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: '13px' }}>MAF Properties</span>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Role badge */}
        <span style={{
          background: 'rgba(0,196,180,0.12)',
          color: '#00C4B4',
          border: '1px solid rgba(0,196,180,0.25)',
          fontSize: '11px',
          padding: '3px 10px',
          borderRadius: '20px',
          fontWeight: '500',
        }}>
          {role === 'admin' ? 'MAF Admin' : 'Guest Explorer'}
        </span>

        {/* Sign out */}
        <button
          onClick={handleSignOut}
          style={{
            color: 'rgba(255,255,255,0.4)',
            fontSize: '12px',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: '4px 8px',
          }}
        >
          Sign out
        </button>
      </div>
    </header>
  )
}
