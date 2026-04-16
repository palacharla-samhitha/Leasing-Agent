import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const { setRole } = useAuth()
  const navigate = useNavigate()

  function handleRole(role) {
    setRole(role)
    navigate(role === 'admin' ? '/dashboard' : '/properties')
  }

  return (
    <div style={{ minHeight: '100vh', background: '#F5F6F8' }} className="flex items-center justify-center">
      <div style={{ width: '100%', maxWidth: '420px' }} className="flex flex-col items-center">

        {/* Logo block */}
        <div className="mb-8 text-center">
          <div style={{ fontSize: '28px', fontWeight: '500', marginBottom: '6px' }}>
            <span style={{ color: '#00C4B4' }}>re</span>
            <span style={{ color: '#0A2342' }}>knew</span>
          </div>
          <div style={{ color: '#0A2342', fontSize: '13px', opacity: 0.5, letterSpacing: '0.5px' }}>
            × MAF Properties
          </div>
        </div>

        {/* Card */}
        <div style={{
          background: 'white',
          border: '0.5px solid #E5E7EB',
          borderRadius: '12px',
          padding: '36px 32px',
          width: '100%',
          boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
        }}>
          {/* Title */}
          <div className="text-center mb-6">
            <h1 style={{ fontSize: '18px', fontWeight: '500', color: '#0A2342', marginBottom: '6px' }}>
              AI Leasing Agent
            </h1>
            <p style={{ fontSize: '13px', color: '#6B7280' }}>
              Select how you want to continue
            </p>
          </div>

          {/* Divider */}
          <div style={{ borderTop: '0.5px solid #F3F4F6', marginBottom: '24px' }} />

          {/* Buttons */}
          <div className="flex flex-col gap-3">
            <button
              onClick={() => handleRole('admin')}
              style={{
                background: '#0A2342',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                padding: '13px 20px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: 'pointer',
                width: '100%',
                textAlign: 'left',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div>MAF Admin</div>
                <div style={{ fontSize: '11px', opacity: 0.6, fontWeight: '400', marginTop: '2px' }}>
                  Full access — leasing, workflows, audit
                </div>
              </div>
              <span style={{ opacity: 0.5 }}>→</span>
            </button>

            <button
              onClick={() => handleRole('customer')}
              style={{
                background: 'white',
                color: '#0A2342',
                border: '1px solid #00C4B4',
                borderRadius: '8px',
                padding: '13px 20px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: 'pointer',
                width: '100%',
                textAlign: 'left',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ color: '#00C4B4' }}>Explore as Guest</div>
                <div style={{ fontSize: '11px', color: '#6B7280', fontWeight: '400', marginTop: '2px' }}>
                  Browse properties, units and submit an inquiry
                </div>
              </div>
              <span style={{ color: '#00C4B4', opacity: 0.7 }}>→</span>
            </button>
          </div>
        </div>

        {/* Footer */}
        <div style={{ marginTop: '24px', fontSize: '11px', color: '#9CA3AF', textAlign: 'center' }}>
          Confidential · ReKnew × Monetize360 × MAF Properties · April 2026
        </div>
      </div>
    </div>
  )
}
