import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { paymentApi } from '@/features/payments/api'
import { App } from '@/app/App'
import { api, ApiError, type Session } from '@/lib/api'
import { guestApi } from '@/features/guests/api'
import { propertyApi } from '@/features/properties/api'
import { blockApi, reservationApi, type Reservation } from './api'
import { holdToIso, localHold, formatDate } from './dates'
import { blockFormSchema, reservationFormSchema } from './validation'

const tenant = {
  id: '22222222-2222-4222-8222-222222222222',
  name: 'Empresa ficticia',
  role: 'staff' as const,
  timezone: 'America/Santiago',
  currency: 'CLP',
}
const session: Session = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'staff@example.invalid',
  name: 'Colaborador ficticio',
  is_platform_admin: false,
  active_tenant: tenant,
}
const guest = {
  id: '33333333-3333-4333-8333-333333333333',
  first_name: 'Persona ficticia',
  last_name: 'Prueba',
  document_type: 'passport' as const,
  document_masked: '••••TEST',
  active: true,
}
const item: Reservation = {
  id: '44444444-4444-4444-8444-444444444444',
  property_id: '55555555-5555-4555-8555-555555555555',
  property_name: 'Cabaña ficticia',
  primary_guest_id: guest.id,
  guest,
  check_in: '2099-01-10',
  check_out: '2099-01-12',
  adults: 2,
  children: 0,
  status: 'draft',
  hold_until: null,
  hold_active: false,
  total_amount: '100000.25',
  received_amount: '0.00',
  balance: '100000.25',
  payment_state: 'unpaid',
  currency: 'CLP',
  source: 'direct',
  notes: 'Nota operativa',
  cancel_reason: '',
  created_at: '2026-10-13T00:00:00Z',
  updated_at: '2026-10-13T00:00:00Z',
}
const clients: QueryClient[] = []
beforeEach(() => {
  vi.spyOn(paymentApi, 'list').mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  })
})
function mount(path: string, user = session) {
  vi.spyOn(api, 'me').mockResolvedValue(user)
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  })
  clients.push(client)
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
afterEach(() => {
  clients.forEach((client) => client.clear())
  clients.length = 0
})

describe('Fechas y reglas de formulario', () => {
  it('conserva la cabaña del enlace cuando sus opciones cargan después del formulario', async () => {
    const property = {
      id: item.property_id,
      name: item.property_name,
      code: 'CAB',
      description: '',
      address: '',
      capacity: 4,
      base_rate: '50000.00',
      currency: 'CLP',
      check_in_time: '15:00:00',
      check_out_time: '11:00:00',
      active: true,
      photos: [],
      created_at: item.created_at,
      updated_at: item.updated_at,
    }
    let resolveProperty!: (value: typeof property) => void
    vi.spyOn(propertyApi, 'get').mockReturnValue(
      new Promise((resolve) => {
        resolveProperty = resolve
      }),
    )
    vi.spyOn(propertyApi, 'list').mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    })
    vi.spyOn(guestApi, 'search').mockResolvedValue({
      count: 0,
      page: 1,
      has_next: false,
      has_previous: false,
      results: [],
    })
    mount(`/reservas/nueva?property_id=${item.property_id}`)
    const select = await screen.findByLabelText('Cabaña')
    await act(async () => {
      resolveProperty(property)
    })
    await waitFor(() => expect(select).toHaveValue(item.property_name))
  })
  it.each([
    ['2026-01-10T15:00', '2026-01-10T18:00:00.000Z'],
    ['2026-07-10T15:00', '2026-07-10T19:00:00.000Z'],
  ])('convierte %s en la zona de la empresa', (value, iso) => {
    expect(holdToIso(value, 'America/Santiago')).toBe(iso)
    expect(localHold(iso, 'America/Santiago')).toBe(value)
  })
  it.each(['2026-09-06T00:30', '2026-04-04T23:30', '2026-02-30T12:00', ''])(
    'rechaza hora ambigua o inexistente: %s',
    (value) => {
      expect(() => holdToIso(value, 'America/Santiago')).toThrow()
    },
  )
  it('presenta fechas de estadía sin convertir a zona de navegador', () => {
    expect(formatDate('2026-09-06')).toBe('06/09/2026')
  })
  const valid = { ...item, status: 'draft' as const, hold_until: '' }
  it.each([
    { adults: 0 },
    { children: -1 },
    { total_amount: '1.234' },
    { total_amount: '-1' },
    { check_out: '2099-01-10' },
    { status: 'pending', hold_until: '' },
  ])('rechaza valores inválidos %j', (value) => {
    expect(reservationFormSchema.safeParse({ ...valid, ...value }).success).toBe(false)
  })
  it('valida fechas exclusivas del bloqueo', () => {
    expect(
      blockFormSchema.safeParse({
        property_id: item.property_id,
        start_date: '2099-01-10',
        end_date: '2099-01-10',
        reason: 'maintenance',
        notes: '',
      }).success,
    ).toBe(false)
  })
})

describe('Reservas y permisos', () => {
  it('staff puede consultar y crear reservas', async () => {
    vi.spyOn(reservationApi, 'list').mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [item],
    })
    mount('/reservas')
    expect(await screen.findByRole('link', { name: 'Nueva reserva' })).toBeVisible()
    expect(await screen.findByRole('heading', { name: item.property_name })).toBeVisible()
  })
  it('muestra rechazo de disponibilidad al confirmar sin cambiar la ficha', async () => {
    vi.spyOn(reservationApi, 'get').mockResolvedValue(item)
    vi.spyOn(reservationApi, 'action').mockRejectedValue(
      new ApiError(409, 'La cabaña no está disponible.'),
    )
    mount(`/reservas/${item.id}`)
    await userEvent.click(await screen.findByRole('button', { name: 'Confirmar reserva' }))
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar cambio' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('no está disponible')
    expect(screen.getByText('Borrador', { exact: true })).toBeVisible()
    expect(reservationApi.action).toHaveBeenCalledWith(tenant.id, item.id, 'confirm', {})
  })
  it('cancelación requiere motivo y confirmación explícita', async () => {
    vi.spyOn(reservationApi, 'get').mockResolvedValue({ ...item, status: 'confirmed' })
    vi.spyOn(reservationApi, 'action').mockResolvedValue({
      ...item,
      status: 'cancelled',
      cancel_reason: 'Motivo ficticio',
    })
    mount(`/reservas/${item.id}`)
    await userEvent.click(await screen.findByRole('button', { name: 'Cancelar reserva' }))
    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByRole('button', { name: 'Aplicar cambio' })).toBeDisabled()
    await userEvent.type(within(dialog).getByLabelText('Motivo obligatorio'), 'Motivo ficticio')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Aplicar cambio' }))
    expect(await screen.findByText('Cancelada', { exact: true })).toBeVisible()
    expect(reservationApi.action).toHaveBeenCalledWith(tenant.id, item.id, 'cancel', {
      reason: 'Motivo ficticio',
    })
  })
  it('staff no tiene controles para modificar bloqueos', async () => {
    vi.spyOn(blockApi, 'list').mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    })
    mount('/reservas/bloqueos')
    expect(await screen.findByRole('heading', { name: 'Bloqueos de fechas' })).toBeVisible()
    expect(screen.queryByRole('link', { name: 'Nuevo bloqueo' })).not.toBeInTheDocument()
  })
  it('formulario conserva precio exacto y permite huésped existente a staff', async () => {
    vi.spyOn(propertyApi, 'list').mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          id: item.property_id,
          name: item.property_name,
          code: 'FAKE',
          description: '',
          capacity: 4,
          address: '',
          base_rate: '50000.00',
          currency: 'CLP',
          check_in_time: '15:00',
          check_out_time: '11:00',
          active: true,
          photos: [],
          created_at: item.created_at,
          updated_at: item.updated_at,
        },
      ],
    })
    vi.spyOn(guestApi, 'search').mockResolvedValue({
      count: 1,
      page: 1,
      has_next: false,
      has_previous: false,
      results: [guest],
    })
    vi.spyOn(reservationApi, 'availability').mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          property_id: item.property_id,
          property_name: item.property_name,
          capacity: 4,
          available: true,
        },
      ],
    })
    vi.spyOn(reservationApi, 'save').mockResolvedValue(item)
    vi.spyOn(reservationApi, 'get').mockResolvedValue(item)
    mount('/reservas/nueva')
    await userEvent.click(await screen.findByLabelText('Cabaña'))
    await userEvent.click(
      await screen.findByRole('option', { name: 'Cabaña ficticia · 4 personas' }),
    )
    await userEvent.click(await screen.findByLabelText('Huésped principal'))
    await userEvent.click(await screen.findByRole('option', { name: /Persona ficticia Prueba/ }))
    await userEvent.type(screen.getByLabelText('Entrada'), '2099-01-10')
    await userEvent.type(screen.getByLabelText('Salida (exclusiva)'), '2099-01-12')
    await userEvent.type(screen.getByLabelText('Precio total pactado (CLP)'), '100000.25')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar reserva' }))
    expect(
      await screen.findByRole('heading', { name: `Reserva · ${item.property_name}` }),
    ).toBeVisible()
    expect(reservationApi.save).toHaveBeenCalledWith(
      tenant.id,
      expect.objectContaining({
        total_amount: '100000.25',
        primary_guest_id: guest.id,
        status: 'draft',
      }),
      undefined,
    )
  })
})
