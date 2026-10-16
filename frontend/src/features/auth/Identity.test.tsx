import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { App } from '@/app/App'
import { api, ApiError, type Session, type Tenant } from '@/lib/api'

const tenant: Tenant = {
  id: '22222222-2222-4222-8222-222222222222',
  name: 'Empresa de prueba',
  role: 'owner',
  timezone: 'America/Santiago',
  currency: 'CLP',
}
const session: Session = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'owner@example.invalid',
  name: 'Propietario',
  is_platform_admin: false,
  active_tenant: null,
}
const clients: QueryClient[] = []

function mount(path = '/') {
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
  return client
}

afterEach(() => {
  clients.forEach((client) => client.clear())
  clients.length = 0
  window.history.replaceState(null, '', '/')
})

describe('Identidad', () => {
  it('valida el formulario antes de llamar a la API', async () => {
    vi.spyOn(api, 'me').mockResolvedValue(null)
    const login = vi.spyOn(api, 'login')
    mount('/ingresar')
    await userEvent.click(await screen.findByRole('button', { name: 'Iniciar sesión' }))
    expect(await screen.findByText('Ingresa un correo válido.')).toBeInTheDocument()
    expect(screen.getByText('Ingresa tu contraseña.')).toBeInTheDocument()
    expect(login).not.toHaveBeenCalled()
  })

  it('inicia sesión y entra directo cuando solo tiene una empresa', async () => {
    vi.spyOn(api, 'me').mockResolvedValue(null)
    vi.spyOn(api, 'login').mockImplementation(async () => {
      vi.spyOn(api, 'me').mockResolvedValue(session)
      return session
    })
    vi.spyOn(api, 'tenants').mockResolvedValue([tenant])
    const select = vi.spyOn(api, 'selectTenant').mockResolvedValue(tenant)
    mount('/ingresar')
    await userEvent.type(await screen.findByLabelText('Correo electrónico'), session.email)
    await userEvent.type(screen.getByLabelText('Contraseña'), 'Test-strong-passphrase-2026')
    await userEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
    await waitFor(() => expect(select).toHaveBeenCalledWith(tenant.id))
    expect(await screen.findByRole('heading', { name: 'Cabañas' })).toBeInTheDocument()
  })

  it('mantiene el selector cuando tiene varias empresas', async () => {
    vi.spyOn(api, 'me').mockResolvedValue(null)
    vi.spyOn(api, 'login').mockResolvedValue(session)
    const second = { ...tenant, id: '33333333-3333-4333-8333-333333333333', name: 'Otra empresa' }
    vi.spyOn(api, 'tenants').mockResolvedValue([tenant, second])
    const select = vi.spyOn(api, 'selectTenant')
    mount('/ingresar')
    await userEvent.type(await screen.findByLabelText('Correo electrónico'), session.email)
    await userEvent.type(screen.getByLabelText('Contraseña'), 'Test-strong-passphrase-2026')
    await userEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
    expect(
      await screen.findByRole('button', { name: 'Seleccionar Empresa de prueba' }),
    ).toBeVisible()
    expect(screen.getByRole('button', { name: 'Seleccionar Otra empresa' })).toBeVisible()
    expect(select).not.toHaveBeenCalled()
  })

  it('informa bloqueo por intentos y permite corregir datos', async () => {
    vi.spyOn(api, 'me').mockResolvedValue(null)
    vi.spyOn(api, 'login').mockRejectedValue(
      new ApiError(429, 'Demasiados intentos. Espera unos minutos.'),
    )
    mount('/ingresar')
    await userEvent.type(await screen.findByLabelText('Correo electrónico'), session.email)
    await userEvent.type(screen.getByLabelText('Contraseña'), 'wrong-password')
    await userEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Demasiados intentos')
    expect(screen.getByRole('button', { name: 'Iniciar sesión' })).toBeEnabled()
  })

  it('limpia la caché de empresa al seleccionar otra', async () => {
    vi.spyOn(api, 'me').mockResolvedValue(session)
    vi.spyOn(api, 'tenants').mockResolvedValue([tenant])
    vi.spyOn(api, 'selectTenant').mockResolvedValue(tenant)
    const client = mount()
    client.setQueryData(['private-company-data', 'previous'], {
      confidential: true,
    })
    await userEvent.click(
      await screen.findByRole('button', {
        name: 'Seleccionar Empresa de prueba',
      }),
    )
    await screen.findByRole('heading', { name: 'Cabañas' })
    expect(client.getQueryData(['private-company-data', 'previous'])).toBeUndefined()
  })

  it('no muestra éxito de selección si se revoca la membresía', async () => {
    vi.spyOn(api, 'me').mockResolvedValue(session)
    vi.spyOn(api, 'tenants').mockResolvedValue([tenant])
    vi.spyOn(api, 'selectTenant').mockRejectedValue(new ApiError(404, 'Empresa no disponible.'))
    mount()
    await userEvent.click(
      await screen.findByRole('button', {
        name: 'Seleccionar Empresa de prueba',
      }),
    )
    expect(await screen.findByRole('alert')).toHaveTextContent('Empresa no disponible')
    expect(screen.queryByRole('region', { name: 'Empresa activa' })).not.toBeInTheDocument()
  })

  it('cierra sesión y retira datos en caché', async () => {
    vi.spyOn(api, 'me').mockResolvedValue(session)
    vi.spyOn(api, 'tenants').mockResolvedValue([tenant])
    vi.spyOn(api, 'logout').mockImplementation(async () => {
      vi.spyOn(api, 'me').mockResolvedValue(null)
    })
    const client = mount()
    client.setQueryData(['private-company-data'], { confidential: true })
    await userEvent.click(await screen.findByRole('button', { name: 'Más opciones' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Cerrar sesión' }))
    expect(await screen.findByRole('link', { name: /Ingresar a mi cuenta/ })).toBeInTheDocument()
    expect(client.getQueryData(['private-company-data'])).toBeUndefined()
  })

  it('presenta el estado de cuenta sin empresas', async () => {
    vi.spyOn(api, 'me').mockResolvedValue(session)
    vi.spyOn(api, 'tenants').mockResolvedValue([])
    mount()
    expect(await screen.findByText(/todavía no tiene empresas asignadas/)).toBeInTheDocument()
  })

  it('ofrece reintentar cuando falla la conexión inicial', async () => {
    vi.spyOn(api, 'me').mockRejectedValue(new ApiError(0, 'No pudimos conectar.'))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos conectar')
    expect(screen.getByRole('button', { name: 'Reintentar conexión' })).toBeInTheDocument()
  })

  it('muestra una respuesta genérica de recuperación', async () => {
    vi.spyOn(api, 'me').mockResolvedValue(null)
    const reset = vi.spyOn(api, 'resetPassword').mockResolvedValue()
    mount('/recuperar')
    await userEvent.type(await screen.findByLabelText('Correo electrónico'), session.email)
    await userEvent.click(screen.getByRole('button', { name: 'Enviar instrucciones' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Si el correo corresponde')
    expect(reset).toHaveBeenCalledWith(session.email)
  })

  it('valida confirmación y retira el token de la barra de dirección', async () => {
    vi.spyOn(api, 'me').mockResolvedValue(null)
    const confirm = vi.spyOn(api, 'confirmPassword').mockResolvedValue()
    window.history.replaceState(null, '', '/restablecer#uid=test-uid&token=test-token')
    mount('/restablecer')
    await userEvent.type(
      await screen.findByLabelText('Nueva contraseña'),
      'New-test-passphrase-2026!',
    )
    await userEvent.type(screen.getByLabelText('Repite la contraseña'), 'mismatched')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar contraseña' }))
    expect(await screen.findByText('Las contraseñas no coinciden.')).toBeInTheDocument()
    expect(confirm).not.toHaveBeenCalled()
    expect(window.location.hash).toBe('')
    await userEvent.clear(screen.getByLabelText('Repite la contraseña'))
    await userEvent.type(screen.getByLabelText('Repite la contraseña'), 'New-test-passphrase-2026!')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar contraseña' }))
    await waitFor(() =>
      expect(confirm).toHaveBeenCalledWith('test-uid', 'test-token', 'New-test-passphrase-2026!'),
    )
    expect(
      within(await screen.findByRole('status')).getByText(/Contraseña actualizada/),
    ).toBeInTheDocument()
  })
})
