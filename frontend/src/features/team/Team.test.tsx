import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { Session } from '@/lib/api'
import { UsersPage } from './UsersPage'
import { AcceptInvitationPage } from './AcceptInvitationPage'
import { teamApi } from './api'

const auth = vi.hoisted(() => ({ session: null as Session | null }))
vi.mock('@/features/auth/AuthProvider', () => ({ useAuth: () => ({ session: auth.session }) }))
vi.mock('./api', () => ({
  teamApi: {
    members: vi.fn(),
    invitations: vi.fn(),
    create: vi.fn(),
    change: vi.fn(),
    revoke: vi.fn(),
    preview: vi.fn(),
    accept: vi.fn(),
  },
}))
const company = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
const member = {
  id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  user_id: company,
  name: 'Colaborador ficticio',
  email: 'staff@example.invalid',
  role: 'staff' as const,
  active: true,
}
const owner: Session = {
  id: company,
  email: 'owner@example.invalid',
  name: 'Propietario',
  is_platform_admin: false,
  active_tenant: {
    id: company,
    name: 'Empresa de prueba',
    timezone: 'America/Santiago',
    currency: 'CLP',
    role: 'owner',
  },
}
function show(page: React.ReactNode) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
        })
      }
    >
      <MemoryRouter>{page}</MemoryRouter>
    </QueryClientProvider>,
  )
}
beforeEach(() => {
  vi.resetAllMocks()
  auth.session = owner
  window.history.replaceState({}, '', '/')
  vi.mocked(teamApi.members).mockResolvedValue({ results: [member], next: null, previous: null })
  vi.mocked(teamApi.invitations).mockResolvedValue({ results: [], next: null, previous: null })
})
describe('Usuarios por empresa', () => {
  it('oculta gestión a staff y no consulta datos del equipo', () => {
    auth.session = { ...owner, active_tenant: { ...owner.active_tenant!, role: 'staff' } }
    show(<UsersPage />)
    expect(screen.getByRole('alert')).toHaveTextContent('Solo el propietario')
    expect(teamApi.members).not.toHaveBeenCalled()
  })
  it('requiere revisar un cambio y envía el estado observado', async () => {
    const user = userEvent.setup()
    vi.mocked(teamApi.change).mockResolvedValue({ ...member, role: 'manager' })
    show(<UsersPage />)
    const save = await screen.findByRole('button', { name: 'Guardar acceso' })
    expect(save).toBeDisabled()
    await user.selectOptions(screen.getByLabelText('Permiso de staff@example.invalid'), 'manager')
    expect(save).toBeDisabled()
    await user.click(screen.getByLabelText('Revisé el cambio de acceso de staff@example.invalid.'))
    await user.click(save)
    await waitFor(() =>
      expect(teamApi.change).toHaveBeenCalledWith(company, member, 'manager', true),
    )
  })
  it('muestra el enlace una sola vez y permite ocultarlo sin guardarlo en storage', async () => {
    const user = userEvent.setup()
    const link = 'http://localhost:15173/invitacion#token=' + 'x'.repeat(43)
    vi.mocked(teamApi.create).mockResolvedValue({
      invitation: {
        id: company,
        email: 'new@example.invalid',
        role: 'staff',
        state: 'pending',
        expires_at: '2030-01-01T00:00:00Z',
      },
      link,
    })
    show(<UsersPage />)
    await user.type(screen.getByLabelText('Correo del invitado'), 'new@example.invalid')
    await user.click(screen.getByRole('button', { name: 'Crear invitación' }))
    expect(await screen.findByLabelText('Enlace privado de invitación')).toHaveValue(link)
    expect(localStorage.length).toBe(0)
    await user.click(screen.getByRole('button', { name: 'Ocultar enlace' }))
    expect(screen.queryByLabelText('Enlace privado de invitación')).not.toBeInTheDocument()
  })
})
describe('Aceptación de invitación', () => {
  beforeEach(() => {
    auth.session = null
    window.history.replaceState({}, '', '/invitacion#token=' + 'a'.repeat(43))
    vi.mocked(teamApi.preview).mockResolvedValue({
      company_name: 'Empresa invitante',
      role: 'staff',
      email_hint: 'n***@example.invalid',
      expires_at: '2030-01-01T00:00:00Z',
    })
    vi.mocked(teamApi.accept).mockResolvedValue({ detail: 'Aceptada' })
  })
  it('borra fragmento y no crea cuenta hasta la acción explícita con contraseñas iguales', async () => {
    const user = userEvent.setup()
    show(<AcceptInvitationPage />)
    await screen.findByText('Empresa invitante')
    expect(window.location.hash).toBe('')
    expect(teamApi.accept).not.toHaveBeenCalled()
    await user.type(screen.getByLabelText('Nombre'), 'Persona')
    await user.type(screen.getByLabelText('Contraseña nueva'), 'Fresh-fictional-passphrase-2026!')
    await user.type(screen.getByLabelText('Repite tu contraseña'), 'Other-fictional-passphrase!')
    await user.click(screen.getByRole('button', { name: 'Crear cuenta y aceptar' }))
    expect(screen.getByRole('alert')).toHaveTextContent('no coinciden')
    expect(teamApi.accept).not.toHaveBeenCalled()
    await user.clear(screen.getByLabelText('Repite tu contraseña'))
    await user.type(
      screen.getByLabelText('Repite tu contraseña'),
      'Fresh-fictional-passphrase-2026!',
    )
    await user.click(screen.getByRole('button', { name: 'Crear cuenta y aceptar' }))
    expect(await screen.findByRole('heading', { name: 'Invitación aceptada' })).toBeVisible()
    expect(teamApi.accept).toHaveBeenCalledWith({
      token: 'a'.repeat(43),
      mode: 'new',
      first_name: 'Persona',
      last_name: '',
      password: 'Fresh-fictional-passphrase-2026!',
    })
  })
  it('para cuenta autenticada acepta sin campos de contraseña', async () => {
    auth.session = owner
    const user = userEvent.setup()
    show(<AcceptInvitationPage />)
    await screen.findByText('Empresa invitante')
    expect(screen.queryByLabelText('Contraseña nueva')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Aceptar invitación' }))
    await waitFor(() =>
      expect(teamApi.accept).toHaveBeenCalledWith({ token: 'a'.repeat(43), mode: 'existing' }),
    )
  })
})
