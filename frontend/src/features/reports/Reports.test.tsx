import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { App } from '@/app/App'
import { api } from '@/lib/api'
import { propertyApi } from '@/features/properties/api'
import { reportApi } from './api'

const clients: QueryClient[] = []
afterEach(() => {
  clients.forEach((client) => client.clear())
  clients.length = 0
})
it('staff consulta canceladas y cambia de filtro conservando el periodo aplicado', async () => {
  vi.spyOn(api, 'me').mockResolvedValue({
    id: '11111111-1111-4111-8111-111111111111',
    email: 'staff@example.invalid',
    name: 'Ficticio',
    is_platform_admin: false,
    active_tenant: {
      id: '22222222-2222-4222-8222-222222222222',
      name: 'Empresa ficticia',
      role: 'staff',
      timezone: 'America/Santiago',
      currency: 'CLP',
    },
  })
  vi.spyOn(propertyApi, 'list').mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  })
  const get = vi.spyOn(reportApi, 'get').mockResolvedValue({
    kind: 'reservations',
    data: { count: 0, page: 1, next: false, previous: false, results: [] },
  })
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  })
  clients.push(client)
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/reportes']}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  expect(await screen.findByRole('heading', { name: 'Reportes y exportaciones' })).toBeVisible()
  const user = userEvent.setup()
  await user.selectOptions(screen.getByLabelText('Reporte'), 'reservations')
  await user.selectOptions(screen.getByLabelText('Estado de reserva'), 'cancelled')
  expect(get).toHaveBeenLastCalledWith(
    '22222222-2222-4222-8222-222222222222',
    expect.objectContaining({ kind: 'reservations', status: 'cancelled' }),
    1,
  )
  expect(await screen.findByText('No hay registros para estos filtros.')).toBeVisible()
  expect(screen.getByRole('button', { name: 'Descargar CSV' })).toBeEnabled()
  await user.selectOptions(screen.getByLabelText('Reporte'), 'payments')
  expect(get).toHaveBeenLastCalledWith(
    '22222222-2222-4222-8222-222222222222',
    expect.objectContaining({ kind: 'payments', status: '' }),
    1,
  )
  expect(screen.queryByLabelText('Estado de reserva')).not.toBeInTheDocument()
})
