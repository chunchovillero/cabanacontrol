import { beforeEach, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { ApiError, request, write } from '@/lib/api'
import { SettingsPage } from './SettingsPage'

const auth = vi.hoisted(() => ({ role: 'owner' }))
vi.mock('./AuthProvider', () => ({
  useAuth: () => ({ session: { id: 'user', active_tenant: { id: 'tenant', role: auth.role } } }),
}))
vi.mock('@/lib/api', async (original) => ({
  ...(await original<typeof import('@/lib/api')>()),
  request: vi.fn(),
  write: vi.fn(),
}))
const company = {
  id: 'tenant',
  name: 'Empresa',
  legal_name: '',
  contact_email: '',
  contact_phone: '',
  timezone: 'America/Santiago',
  currency: 'CLP',
  updated_at: '2026-10-15T12:00:00Z',
}
let name = 'Persona'
beforeEach(() => {
  vi.resetAllMocks()
  auth.role = 'owner'
  name = 'Persona'
  vi.mocked(request).mockImplementation(async (path) =>
    path.includes('company-settings')
      ? company
      : { first_name: name, last_name: '', email: 'user@example.invalid' },
  )
  vi.mocked(write).mockResolvedValue({})
})
function show() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
it('staff puede editar su perfil sin consultar configuración de empresa', async () => {
  auth.role = 'staff'
  show()
  const user = userEvent.setup()
  await user.clear(await screen.findByLabelText('Nombre', { exact: true }))
  await user.type(screen.getByLabelText('Nombre', { exact: true }), 'Nuevo')
  await user.click(screen.getByRole('button', { name: 'Guardar perfil' }))
  await waitFor(() =>
    expect(write).toHaveBeenCalledWith(
      '/api/v1/auth/profile/',
      {
        first_name: 'Nuevo',
        last_name: '',
        expected_first_name: 'Persona',
        expected_last_name: '',
      },
      'PATCH',
      {},
    ),
  )
  expect(vi.mocked(request).mock.calls.every(([path]) => !path.includes('company-settings'))).toBe(
    true,
  )
})
it('envía contexto y versión sin permitir editar moneda', async () => {
  show()
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Guardar empresa' }))
  await waitFor(() =>
    expect(write).toHaveBeenCalledWith(
      '/api/v1/company-settings/',
      {
        name: 'Empresa',
        legal_name: '',
        contact_email: '',
        contact_phone: '',
        expected_updated_at: company.updated_at,
      },
      'PATCH',
      { 'X-Tenant-Context': 'tenant' },
    ),
  )
  expect(screen.queryByRole('textbox', { name: 'Moneda' })).not.toBeInTheDocument()
})
it('ante conflicto recarga nombres y solicita revisión sin reintentar la escritura', async () => {
  show()
  const user = userEvent.setup()
  const input = await screen.findByLabelText('Nombre', { exact: true })
  await user.clear(input)
  await user.type(input, 'Borrador')
  vi.mocked(write).mockImplementation(async () => {
    name = 'Otra sesión'
    throw new ApiError(409, 'Conflicto')
  })
  await user.click(screen.getByRole('button', { name: 'Guardar perfil' }))
  await waitFor(() =>
    expect(screen.getByLabelText('Nombre', { exact: true })).toHaveValue('Otra sesión'),
  )
  expect(screen.getByRole('alert')).toHaveTextContent('Los datos cambiaron.')
  expect(write).toHaveBeenCalledTimes(1)
})
