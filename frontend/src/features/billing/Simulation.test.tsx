import { beforeEach, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { request, write } from '@/lib/api'
import { SimulationPage } from './SimulationPage'

const auth = vi.hoisted(() => ({ role: 'owner' }))
vi.mock('@/features/auth/AuthProvider', () => ({
  useAuth: () => ({
    session: { active_tenant: { id: 'tenant', role: auth.role, timezone: 'America/Santiago' } },
  }),
}))
vi.mock('@/lib/api', () => ({ request: vi.fn(), write: vi.fn() }))
beforeEach(() => {
  vi.resetAllMocks()
  auth.role = 'owner'
  vi.mocked(request).mockResolvedValue({
    enabled: true,
    terms_version: 'simulation-v1',
    prices: [{ code: 'initial', name: 'Inicial', amount: '4500.00', currency: 'CLP', version: 1 }],
    contract: null,
    attempts: [],
  })
  vi.mocked(write).mockResolvedValue({
    id: 'quote',
    kind: 'purchase',
    code: 'initial',
    amount: '4500.00',
    state: 'quoted',
    expires_at: '2030-01-01T12:00:00Z',
    quoted_at: '2030-01-01T11:45:00Z',
    contract_revision: 0,
  })
})
function show() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        <SimulationPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
it('staff no consulta ni gestiona contratación', () => {
  auth.role = 'staff'
  show()
  expect(screen.getByRole('alert')).toHaveTextContent('Solo el propietario')
  expect(request).not.toHaveBeenCalled()
})
it('no permite confirmar sin consentimiento y envía contexto, términos y clave', async () => {
  show()
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Obtener cotización simulada' }))
  const confirm = await screen.findByRole('button', { name: 'Confirmar contratación simulada' })
  expect(confirm).toBeDisabled()
  await user.click(screen.getByRole('checkbox'))
  await user.click(confirm)
  expect(write).toHaveBeenLastCalledWith(
    '/api/v1/billing/simulation/attempts/quote/accept/',
    expect.objectContaining({ consent: true, terms: 'simulation-v1', key: expect.any(String) }),
    'POST',
    { 'X-Tenant-Context': 'tenant' },
  )
})
it('empresa no habilitada no ofrece crear cotizaciones', async () => {
  vi.mocked(request).mockResolvedValue({
    enabled: false,
    terms_version: 'simulation-v1',
    prices: [],
    contract: null,
    attempts: [],
  })
  show()
  expect(await screen.findByText(/La simulación no está habilitada/)).toBeVisible()
  expect(
    screen.queryByRole('button', { name: 'Obtener cotización simulada' }),
  ).not.toBeInTheDocument()
})
