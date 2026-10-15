import { beforeEach, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { request } from '@/lib/api'
import { PlanPage } from './PlanPage'

const auth = vi.hoisted(() => ({ role: 'owner', tenantId: 'tenant-a' }))
vi.mock('@/features/auth/AuthProvider', () => ({
  useAuth: () => ({
    session: {
      active_tenant: { id: auth.tenantId, role: auth.role, timezone: 'America/Santiago' },
    },
  }),
}))
vi.mock('@/lib/api', () => ({ request: vi.fn() }))
const plan = {
  code: 'trial',
  version: 1,
  name: 'Prueba de 14 días',
  property_limit: 1,
  member_limit: 1,
}
beforeEach(() => {
  vi.resetAllMocks()
  auth.role = 'owner'
  auth.tenantId = 'tenant-a'
  vi.mocked(request).mockResolvedValue({
    subscription: {
      status: 'expired',
      enforced: true,
      plan,
      usage: { properties: 1, members: 1 },
      trial_ends_at: '2026-10-15T12:00:00Z',
      over_capacity: false,
    },
    catalog: [{ ...plan, code: 'initial', name: 'Inicial', property_limit: 3, member_limit: 2 }],
  })
})
function show() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        <PlanPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
it('staff no consulta datos comerciales', () => {
  auth.role = 'staff'
  show()
  expect(screen.getByRole('alert')).toHaveTextContent('Solo el propietario')
  expect(request).not.toHaveBeenCalled()
})
it('muestra prueba vencida sin prometer bloqueo ni cobros, con contexto', async () => {
  show()
  expect(await screen.findByRole('heading', { name: 'Prueba de 14 días' })).toBeVisible()
  expect(screen.getByRole('alert')).toHaveTextContent('sin suspensión automática ni cobros')
  expect(screen.getByText('$4.500 CLP/mes · Referencia de simulación')).toBeVisible()
  expect(screen.getByText(/El propietario ocupa una plaza/)).toBeVisible()
  expect(request).toHaveBeenCalledWith('/api/v1/billing/plan/', {
    headers: { 'X-Tenant-Context': 'tenant-a' },
  })
})
it('empresa sin asignación no se presenta como plan ilimitado o pagado', async () => {
  vi.mocked(request).mockResolvedValue({
    subscription: {
      status: 'unassigned',
      enforced: false,
      plan: null,
      usage: { properties: 7, members: 4 },
      trial_ends_at: null,
      over_capacity: false,
    },
    catalog: [],
  })
  show()
  expect(await screen.findByRole('heading', { name: 'Empresa sin plan asignado' })).toBeVisible()
  expect(screen.getByText('7 / Sin asignar')).toBeVisible()
  expect(screen.getByText('Pendientes de habilitación manual', { exact: false })).toBeVisible()
})
