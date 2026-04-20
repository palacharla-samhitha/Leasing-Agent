import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Inquiries from './pages/Inquiries'
import Properties from './pages/Properties'
import Units from './pages/Units'
import Audit from './pages/Audit'
import InquiryForm from './pages/InquiryForm'
import WorkflowView from './pages/WorkflowView'

function ProtectedLayout({ children, adminOnly = false }) {
  const { role } = useAuth()

  if (!role) return <Navigate to="/" replace />
  if (adminOnly && role !== 'admin') return <Navigate to="/properties" replace />

  return (
    <div className="flex flex-col h-screen">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto bg-gray-50 p-6">
          {children}
        </main>
      </div>
    </div>
  )
}

export default function App() {
  const { role } = useAuth()

  return (
    <Routes>
      {/* Login */}
      <Route
        path="/"
        element={role ? <Navigate to={role === 'admin' ? '/dashboard' : '/properties'} replace /> : <Login />}
      />

      {/* Admin only */}
      <Route path="/dashboard" element={<ProtectedLayout adminOnly><Dashboard /></ProtectedLayout>} />
      <Route path="/inquiries" element={<ProtectedLayout adminOnly><Inquiries /></ProtectedLayout>} />
      <Route path="/workflow/:threadId" element={<ProtectedLayout adminOnly><WorkflowView /></ProtectedLayout>} />
      <Route path="/audit" element={<ProtectedLayout adminOnly><Audit /></ProtectedLayout>} />

      {/* Admin + Customer */}
      <Route path="/properties" element={<ProtectedLayout><Properties /></ProtectedLayout>} />
      <Route path="/units" element={<ProtectedLayout><Units /></ProtectedLayout>} />
      <Route path="/inquiry/new" element={<ProtectedLayout><InquiryForm /></ProtectedLayout>} />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
