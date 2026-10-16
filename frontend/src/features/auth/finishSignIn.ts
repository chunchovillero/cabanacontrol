import { api, type Session } from '@/lib/api'

export async function finishSignIn(session: Session): Promise<{
  session: Session
  destination: string
}> {
  if (session.active_tenant) return { session, destination: '/cabanas' }
  const tenants = await api.tenants()
  if (tenants.length !== 1) return { session, destination: '/' }
  const selected = await api.selectTenant(tenants[0].id)
  return {
    session: { ...session, active_tenant: selected },
    destination: '/cabanas',
  }
}
