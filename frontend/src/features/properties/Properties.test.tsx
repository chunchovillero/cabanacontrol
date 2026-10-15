import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { App } from '@/app/App'
import { api, type Session } from '@/lib/api'
import { formatMoney, propertyApi, type Property } from './api'

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
const property: Property = {
  id: '33333333-3333-4333-8333-333333333333',
  name: 'Cabaña de prueba',
  code: 'CAB-1',
  description: '',
  address: '',
  capacity: 5,
  base_rate: '50000.10',
  currency: 'CLP',
  check_in_time: '15:00:00',
  check_out_time: '11:00:00',
  active: true,
  photos: [],
  created_at: '2026-10-13T00:00:00Z',
  updated_at: '2026-10-13T00:00:00Z',
}
const clients: QueryClient[] = []

function mount(path = '/cabanas', user = session) {
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

describe('Cabañas', () => {
  it('muestra una lista filtrada por empresa con tarifa exacta', async () => {
    const list = vi
      .spyOn(propertyApi, 'list')
      .mockResolvedValue({ count: 1, next: null, previous: null, results: [property] })
    mount()
    expect(await screen.findByRole('heading', { name: property.name })).toBeInTheDocument()
    expect(list).toHaveBeenCalledWith(tenant.id, '', 'true', 1)
    expect(screen.getByText('$ 50.000,10')).toBeInTheDocument()
  })

  it('busca por nombre y cambia el filtro de estado', async () => {
    const list = vi
      .spyOn(propertyApi, 'list')
      .mockResolvedValue({ count: 0, next: null, previous: null, results: [] })
    mount()
    await userEvent.type(await screen.findByLabelText('Buscar por nombre o código'), 'Bosque')
    await userEvent.click(screen.getByRole('button', { name: 'Buscar' }))
    await waitFor(() => expect(list).toHaveBeenCalledWith(tenant.id, 'Bosque', 'true', 1))
    await userEvent.selectOptions(screen.getByLabelText('Estado'), 'false')
    await waitFor(() => expect(list).toHaveBeenCalledWith(tenant.id, 'Bosque', 'false', 1))
  })

  it('no ofrece creación ni edición a colaboradores', async () => {
    vi.spyOn(propertyApi, 'list').mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [property],
    })
    mount('/cabanas', { ...session, active_tenant: { ...tenant, role: 'staff' } })
    await screen.findByRole('heading', { name: property.name })
    expect(screen.queryByRole('link', { name: 'Nueva cabaña' })).not.toBeInTheDocument()
  })

  it('valida campos obligatorios sin asumir horarios ni tarifas', async () => {
    const create = vi.spyOn(propertyApi, 'create')
    mount('/cabanas/nueva')
    await userEvent.click(await screen.findByRole('button', { name: 'Guardar cabaña' }))
    expect(await screen.findByText('Ingresa el nombre.')).toBeInTheDocument()
    expect(screen.getByLabelText('Hora de entrada')).toHaveValue('')
    expect(screen.getByLabelText('Tarifa base (CLP)')).toHaveValue('')
    expect(create).not.toHaveBeenCalled()
  })

  it('envía dinero como texto decimal y capacidad como entero', async () => {
    const create = vi.spyOn(propertyApi, 'create').mockResolvedValue(property)
    vi.spyOn(propertyApi, 'get').mockResolvedValue(property)
    mount('/cabanas/nueva')
    await userEvent.type(await screen.findByLabelText('Nombre'), property.name)
    await userEvent.type(screen.getByLabelText('Código'), 'cab-1')
    await userEvent.type(screen.getByLabelText('Capacidad máxima'), '5')
    await userEvent.type(screen.getByLabelText('Tarifa base (CLP)'), '50000,10')
    await userEvent.type(screen.getByLabelText('Hora de entrada'), '15:00')
    await userEvent.type(screen.getByLabelText('Hora de salida'), '11:00')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cabaña' }))
    await waitFor(() =>
      expect(create).toHaveBeenCalledWith(
        tenant.id,
        expect.objectContaining({ base_rate: '50000.10', capacity: 5, code: 'CAB-1' }),
      ),
    )
  })

  it('pide confirmación antes de desactivar y conserva la ficha', async () => {
    vi.spyOn(propertyApi, 'get').mockResolvedValue(property)
    const update = vi.spyOn(propertyApi, 'update').mockResolvedValue({ ...property, active: false })
    mount(`/cabanas/${property.id}`)
    await userEvent.click(await screen.findByRole('button', { name: 'Desactivar cabaña' }))
    expect(update).not.toHaveBeenCalled()
    await userEvent.click(
      within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirmar' }),
    )
    await waitFor(() =>
      expect(update).toHaveBeenCalledWith(tenant.id, property.id, { active: false }),
    )
    expect(await screen.findByRole('button', { name: 'Reactivar cabaña' })).toBeInTheDocument()
  })

  it('rechaza archivos inválidos antes de subirlos', async () => {
    vi.spyOn(propertyApi, 'get').mockResolvedValue(property)
    const upload = vi.spyOn(propertyApi, 'upload')
    mount(`/cabanas/${property.id}`)
    await userEvent.type(
      await screen.findByLabelText('Descripción de la fotografía'),
      'Archivo de prueba',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Subir foto' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Selecciona una imagen')
    expect(upload).not.toHaveBeenCalled()
  })

  it('muestra errores del servidor sin inventar resultados', async () => {
    vi.spyOn(propertyApi, 'list').mockRejectedValue(
      new Error('La empresa activa cambió. Recarga antes de continuar.'),
    )
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('La empresa activa cambió')
  })

  it('formatea importes grandes sin precisión de punto flotante', () => {
    expect(formatMoney('999999999999.99', 'CLP')).toBe('$ 999.999.999.999,99')
  })
})
