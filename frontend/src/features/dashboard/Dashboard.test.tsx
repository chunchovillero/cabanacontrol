import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { App } from '@/app/App'
import { api } from '@/lib/api'
import { propertyApi } from '@/features/properties/api'
import { dashboardApi } from './api'
import { monthPeriod } from './DashboardPage'

const clients: QueryClient[] = []
afterEach(() => {
  clients.forEach((client) => client.clear())
  clients.length = 0
})

it('calcula fin de mes exclusivo en diciembre y febrero bisiesto', () => {
  expect(monthPeriod('2026-12-14')).toEqual({ start: '2026-12-01', end: '2027-01-01' })
  expect(monthPeriod('2028-02-29')).toEqual({ start: '2028-02-01', end: '2028-03-01' })
})

it('muestra cifras de servidor sin compensar deuda y saldo a favor', async () => {
  vi.spyOn(api, 'me').mockResolvedValue({
    id: '11111111-1111-4111-8111-111111111111',
    email: 'staff@example.invalid',
    name: 'Colaborador ficticio',
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
  vi.spyOn(dashboardApi, 'get').mockResolvedValue({
    timezone: 'America/Santiago',
    from_date: '2026-10-01',
    to_date: '2026-11-01',
    today: {
      date: '2026-10-14',
      active_properties: 2,
      occupied: 1,
      retained: 0,
      blocked: 0,
      available: 1,
      arrivals: 1,
      departures: 0,
    },
    occupied_nights: 3,
    capacity_nights: 10,
    occupancy_percent: '30.00',
    blocked_nights: 2,
    money: [
      {
        currency: 'CLP',
        collected: '100.10',
        agreed: '100.25',
        outstanding: '60.15',
        credit: '10.00',
      },
    ],
  })
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  })
  clients.push(client)
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/panel']}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  expect(await screen.findByText('$ 100,10', { exact: true })).toBeVisible()
  expect(screen.getByText('$ 60,15', { exact: true })).toBeVisible()
  expect(screen.getByText('$ 10', { exact: true })).toBeVisible()
  expect(screen.getByText('30,00 %', { exact: true })).toBeVisible()
  expect(screen.getByRole('progressbar')).toHaveAttribute('value', '30')
})
