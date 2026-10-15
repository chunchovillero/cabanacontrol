import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { App } from '@/app/App'
import { api, ApiError, type Session } from '@/lib/api'
import { guestApi, type Guest } from './api'
import { guestFormSchema, normalizeRut } from './validation'

const tenant = {
  id: '22222222-2222-4222-8222-222222222222',
  name: 'Empresa ficticia',
  role: 'owner' as const,
  timezone: 'America/Santiago',
  currency: 'CLP',
}
const session: Session = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'owner@example.invalid',
  name: 'Usuario ficticio',
  is_platform_admin: false,
  active_tenant: tenant,
}
const guest: Guest = {
  id: '33333333-3333-4333-8333-333333333333',
  first_name: 'Persona ficticia',
  last_name: 'De prueba',
  document_type: 'rut',
  document_number: '12345678-5',
  document_masked: '••••78-5',
  phone: '',
  email: '',
  notes: 'Nota privada ficticia',
  active: true,
  created_at: '2026-10-13T00:00:00Z',
  updated_at: '2026-10-13T00:00:00Z',
}
const clients: QueryClient[] = []

function mount(path = '/huespedes', user = session) {
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

async function fillGuest(document = '12.345.678-5') {
  await userEvent.type(await screen.findByLabelText('Nombres'), guest.first_name)
  await userEvent.type(screen.getByLabelText('Apellidos'), guest.last_name)
  await userEvent.type(screen.getByLabelText('RUT', { exact: true }), document)
}

describe('Huéspedes', () => {
  it('lista datos mínimos con documento enmascarado', async () => {
    vi.spyOn(guestApi, 'search').mockResolvedValue({
      count: 1,
      page: 1,
      has_next: false,
      has_previous: false,
      results: [guest],
    })
    mount()
    expect(
      await screen.findByRole('heading', { name: `${guest.first_name} ${guest.last_name}` }),
    ).toBeInTheDocument()
    expect(screen.queryByText('12345678-5')).not.toBeInTheDocument()
    expect(screen.queryByText(guest.notes!)).not.toBeInTheDocument()
  })

  it('busca sin incluir documentos en la navegación', async () => {
    const search = vi
      .spyOn(guestApi, 'search')
      .mockResolvedValue({ count: 0, page: 1, has_next: false, has_previous: false, results: [] })
    mount()
    await userEvent.type(
      await screen.findByLabelText('Buscar por nombre o documento completo'),
      '12.345.678-5',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Buscar' }))
    await waitFor(() => expect(search).toHaveBeenCalledWith(tenant.id, '12.345.678-5', 'true', 1))
    expect(window.location.search).toBe('')
  })

  it('valida RUT antes de crear', async () => {
    const create = vi.spyOn(guestApi, 'create')
    mount('/huespedes/nuevo')
    await fillGuest('12345678-9')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar huésped' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('El RUT no es válido')
    expect(create).not.toHaveBeenCalled()
  })

  it('normaliza RUT y permite contactos opcionales', async () => {
    const create = vi.spyOn(guestApi, 'create').mockResolvedValue(guest)
    vi.spyOn(guestApi, 'get').mockResolvedValue(guest)
    mount('/huespedes/nuevo')
    await fillGuest()
    await userEvent.click(screen.getByRole('button', { name: 'Guardar huésped' }))
    await waitFor(() =>
      expect(create).toHaveBeenCalledWith(
        tenant.id,
        expect.objectContaining({ document_number: '12345678-5', phone: '', email: '' }),
      ),
    )
  })

  it('acepta pasaporte sin exigir RUT', async () => {
    const create = vi
      .spyOn(guestApi, 'create')
      .mockResolvedValue({ ...guest, document_type: 'passport', document_number: 'P-TEST-0001' })
    vi.spyOn(guestApi, 'get').mockResolvedValue(guest)
    mount('/huespedes/nuevo')
    await userEvent.type(await screen.findByLabelText('Nombres'), 'Persona extranjera ficticia')
    await userEvent.type(screen.getByLabelText('Apellidos'), 'De prueba')
    await userEvent.selectOptions(screen.getByLabelText('Tipo de documento'), 'passport')
    await userEvent.type(screen.getByLabelText('Número de documento'), 'P-TEST-0001')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar huésped' }))
    await waitFor(() =>
      expect(create).toHaveBeenCalledWith(
        tenant.id,
        expect.objectContaining({ document_type: 'passport', document_number: 'P-TEST-0001' }),
      ),
    )
  })

  it('ofrece reutilizar una ficha cuando el servidor detecta RUT duplicado', async () => {
    vi.spyOn(guestApi, 'create').mockRejectedValue(
      new ApiError(409, 'Duplicate', {
        error: { code: 'duplicate_document', details: { existing_guest_id: guest.id } },
      }),
    )
    mount('/huespedes/nuevo')
    await fillGuest()
    await userEvent.click(screen.getByRole('button', { name: 'Guardar huésped' }))
    expect(await screen.findByRole('link', { name: 'Abrir ficha existente' })).toHaveAttribute(
      'href',
      `/huespedes/${guest.id}`,
    )
  })

  it('staff no puede crear y no ve notas ni documento completo', async () => {
    vi.spyOn(guestApi, 'get').mockResolvedValue({ ...guest, document_number: null, notes: null })
    mount(`/huespedes/${guest.id}`, { ...session, active_tenant: { ...tenant, role: 'staff' } })
    await screen.findByRole('heading', { name: `${guest.first_name} ${guest.last_name}` })
    expect(screen.queryByRole('link', { name: 'Editar huésped' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Notas restringidas' })).not.toBeInTheDocument()
    expect(screen.queryByText('12345678-5')).not.toBeInTheDocument()
    expect(screen.getByText(guest.document_masked)).toBeInTheDocument()
  })

  it('pide confirmación y conserva la ficha al desactivar', async () => {
    vi.spyOn(guestApi, 'get').mockResolvedValue(guest)
    const update = vi.spyOn(guestApi, 'update').mockResolvedValue({ ...guest, active: false })
    mount(`/huespedes/${guest.id}`)
    await userEvent.click(await screen.findByRole('button', { name: 'Desactivar huésped' }))
    expect(update).not.toHaveBeenCalled()
    await userEvent.click(
      within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirmar' }),
    )
    expect(await screen.findByRole('button', { name: 'Reactivar huésped' })).toBeInTheDocument()
  })
})

describe('Validación chilena', () => {
  it.each([
    ['12.345.678-5', '12345678-5'],
    ['1.000.005-k', '1000005-K'],
    ['1.000.013-0', '1000013-0'],
  ])('normaliza %s', (input, expected) => {
    expect(normalizeRut(input)).toBe(expected)
  })
  it.each(['0-0', '12345678-9', '12..345.678-5', '12345678--5'])('rechaza %s', (input) => {
    expect(normalizeRut(input)).toBeNull()
  })
  it('acepta documento alternativo y rechaza un teléfono inválido', () => {
    const data = {
      first_name: 'Persona ficticia',
      last_name: 'De prueba',
      document_type: 'passport',
      document_number: 'P-TEST-0001',
      phone: '',
      email: '',
      notes: '',
    }
    expect(guestFormSchema.safeParse(data).success).toBe(true)
    expect(guestFormSchema.safeParse({ ...data, phone: 'call-me' }).success).toBe(false)
  })
})
