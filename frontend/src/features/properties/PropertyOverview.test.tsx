import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, it, vi } from 'vitest'
import { reservationApi } from '@/features/reservations/api'
import { dashboardApi } from '@/features/dashboard/api'
import { PropertyOverview } from './PropertyOverview'

it('consulta solo esta cabaña y ofrece crear su reserva, próximos ingresos e historial', async () => {
  const list = vi.spyOn(reservationApi, 'list').mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  })
  const summary = vi.spyOn(dashboardApi, 'get').mockRejectedValue(new Error('Sin conexión'))
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <PropertyOverview
          tenantId="tenant"
          propertyId="property"
          timezone="America/Santiago"
          active
        />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  expect(screen.getByRole('link', { name: 'Crear reserva para esta cabaña' })).toHaveAttribute(
    'href',
    '/reservas/nueva?property_id=property',
  )
  await waitFor(() =>
    expect(list).toHaveBeenCalledWith('tenant', {
      property_id: 'property',
      scope: 'upcoming',
      page: '1',
    }),
  )
  expect(list).toHaveBeenCalledWith('tenant', {
    property_id: 'property',
    scope: 'history',
    page: '1',
  })
  expect(summary).toHaveBeenCalledWith('tenant', expect.any(String), expect.any(String), 'property')
  expect(await screen.findByText('Todavía no hay reservas en el historial.')).toBeVisible()
  expect(screen.getByText('No hay próximas reservas para esta cabaña.')).toBeVisible()
  client.clear()
})
