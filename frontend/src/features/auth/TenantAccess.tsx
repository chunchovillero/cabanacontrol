import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './AuthProvider'

export function TenantAccess() {
  const { session } = useAuth()
  if (!session) return <Navigate to="/ingresar" replace />
  if (!session.active_tenant) return <Navigate to="/" replace />
  return (
    <div key={session.active_tenant.id}>
      <Outlet />
    </div>
  )
}

export function useTenantContext() {
  const { session } = useAuth()
  const tenant = session?.active_tenant
  if (!tenant) throw new Error('Empresa activa requerida')
  return { tenant, canEdit: tenant.role === 'owner' || tenant.role === 'manager' }
}
