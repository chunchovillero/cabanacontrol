import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/AuthProvider'
import { teamApi, type Member, type MemberRole } from './api'

const labels = { owner: 'Propietario', manager: 'Administrador', staff: 'Colaborador' }
const states = {
  pending: 'Pendiente',
  accepted: 'Aceptada',
  expired: 'Vencida',
  revoked: 'Revocada',
}
const input = 'mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm'

export function UsersPage() {
  const { session } = useAuth()
  const tenant = session?.active_tenant
  if (!tenant || tenant.role !== 'owner')
    return <p role="alert">Solo el propietario puede administrar los usuarios de su empresa.</p>
  return <UsersContent key={tenant.id} tenantId={tenant.id} tenantName={tenant.name} />
}

function MemberEditor({
  member,
  tenant,
  changed,
}: {
  member: Member
  tenant: string
  changed: () => void
}) {
  const [role, setRole] = useState<MemberRole>(member.role === 'manager' ? 'manager' : 'staff')
  const [active, setActive] = useState(member.active)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [reviewed, setReviewed] = useState(false)
  async function save() {
    setBusy(true)
    setError('')
    try {
      await teamApi.change(tenant, member, role, active)
      changed()
      setReviewed(false)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo guardar.')
      changed()
    } finally {
      setBusy(false)
    }
  }
  return (
    <article className="min-w-0 rounded-xl border border-border bg-white p-4">
      <h3 className="break-all font-semibold">{member.name || member.email}</h3>
      <p className="break-all text-sm text-muted-foreground">{member.email}</p>
      {member.role === 'owner' ? (
        <p className="mt-3 text-sm">Propietario · Acceso protegido</p>
      ) : (
        <fieldset disabled={busy} className="mt-4 space-y-3">
          <label className="block break-all text-sm">
            Permiso
            <select
              aria-label={`Permiso de ${member.email}`}
              className={input}
              value={role}
              onChange={(event) => {
                setRole(event.target.value as MemberRole)
                setReviewed(false)
              }}
            >
              <option value="staff">Colaborador</option>
              <option value="manager">Administrador</option>
            </select>
          </label>
          <label className="flex items-center gap-2 break-all text-sm">
            <input
              type="checkbox"
              aria-label={`Acceso activo de ${member.email}`}
              checked={active}
              onChange={(event) => {
                setActive(event.target.checked)
                setReviewed(false)
              }}
            />
            Acceso activo
          </label>
          <label className="flex items-start gap-2 break-all text-sm">
            <input
              type="checkbox"
              aria-label={`Revisé el cambio de acceso de ${member.email}.`}
              checked={reviewed}
              onChange={(event) => setReviewed(event.target.checked)}
            />
            Revisé este cambio de acceso.
          </label>
          <Button
            variant="outline"
            disabled={!reviewed || (role === member.role && active === member.active)}
            onClick={() => {
              void save()
            }}
          >
            {busy ? 'Guardando…' : 'Guardar acceso'}
          </Button>
        </fieldset>
      )}
      {error && (
        <p role="alert" className="mt-3 text-sm text-red-800">
          {error}
        </p>
      )}
    </article>
  )
}

function UsersContent({ tenantId, tenantName }: { tenantId: string; tenantName: string }) {
  const queryClient = useQueryClient()
  const [memberPage, setMemberPage] = useState(1)
  const [invitePage, setInvitePage] = useState(1)
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<MemberRole>('staff')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [link, setLink] = useState('')
  const [notice, setNotice] = useState('')
  const members = useQuery({
    queryKey: ['team', tenantId, 'members', memberPage],
    queryFn: () => teamApi.members(tenantId, memberPage),
    retry: false,
  })
  const invitations = useQuery({
    queryKey: ['team', tenantId, 'invitations', invitePage],
    queryFn: () => teamApi.invitations(tenantId, invitePage),
    retry: false,
  })
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['team', tenantId] })
  }
  async function invite(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setLink('')
    setNotice('')
    try {
      const result = await teamApi.create(tenantId, email, role)
      setLink(result.link)
      setEmail('')
      refresh()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo invitar.')
      refresh()
    } finally {
      setBusy(false)
    }
  }
  async function revoke(id: string) {
    setBusy(true)
    setError('')
    setLink('')
    setNotice('')
    try {
      await teamApi.revoke(tenantId, id)
      refresh()
      setNotice('Invitación revocada.')
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo revocar.')
      refresh()
    } finally {
      setBusy(false)
    }
  }
  return (
    <section className="space-y-8">
      <header>
        <p className="text-sm font-semibold text-primary">{tenantName}</p>
        <h1 className="mt-2 text-3xl font-bold">Usuarios</h1>
        <p className="mt-3 text-muted-foreground">
          Invita a tu equipo y administra sus permisos dentro de esta empresa.
        </p>
      </header>
      <form
        onSubmit={(event) => {
          void invite(event)
        }}
        className="rounded-xl border border-border bg-white p-5"
      >
        <h2 className="text-xl font-semibold">Invitar a una persona</h2>
        <fieldset disabled={busy} className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="text-sm">
            Correo del invitado
            <input
              className={input}
              type="email"
              autoComplete="email"
              required
              maxLength={254}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="text-sm">
            Permiso inicial
            <select
              className={input}
              value={role}
              onChange={(event) => setRole(event.target.value as MemberRole)}
            >
              <option value="staff">Colaborador</option>
              <option value="manager">Administrador</option>
            </select>
          </label>
          <Button type="submit" className="sm:col-span-2">
            {busy ? 'Procesando…' : 'Crear invitación'}
          </Button>
        </fieldset>
        <p className="mt-3 text-sm text-muted-foreground">
          Vence en 72 horas. Copia el enlace y compártelo personalmente con el destinatario; no se
          envía un correo automático.
        </p>
      </form>
      {link && (
        <section
          className="rounded-xl border border-primary/30 bg-primary/5 p-5"
          aria-label="Invitación creada"
        >
          <h2 className="font-semibold">Invitación creada</h2>
          <p className="mt-2 text-sm">
            Guarda este enlace ahora; solo se muestra al crearlo. Verifica el destinatario antes de
            compartirlo.
          </p>
          <label className="mt-3 block text-sm">
            Enlace privado de invitación
            <textarea readOnly className={input} value={link} rows={3} />
          </label>
          <Button
            className="mt-3"
            onClick={() => {
              if (!navigator.clipboard) {
                setNotice('Selecciona y copia el enlace manualmente.')
                return
              }
              void navigator.clipboard
                .writeText(link)
                .then(() => setNotice('Enlace copiado.'))
                .catch(() => setNotice('Selecciona y copia el enlace manualmente.'))
            }}
          >
            Copiar enlace
          </Button>
          <Button className="ml-2 mt-3" variant="outline" onClick={() => setLink('')}>
            Ocultar enlace
          </Button>
        </section>
      )}
      {error && (
        <p role="alert" className="text-red-800">
          {error}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      <section>
        <h2 className="mb-4 text-xl font-semibold">Equipo</h2>
        {members.isPending && <p role="status">Cargando equipo…</p>}
        {members.error && <p role="alert">{members.error.message}</p>}
        <div className="grid gap-4 sm:grid-cols-2">
          {members.data?.results.map((member) => (
            <MemberEditor
              key={`${member.id}:${member.role}:${member.active}`}
              member={member}
              tenant={tenantId}
              changed={refresh}
            />
          ))}
        </div>
        <div className="mt-4 flex gap-3">
          <Button
            variant="outline"
            disabled={!members.data?.previous}
            onClick={() => setMemberPage((p) => p - 1)}
          >
            Equipo anterior
          </Button>
          <Button
            variant="outline"
            disabled={!members.data?.next}
            onClick={() => setMemberPage((p) => p + 1)}
          >
            Equipo siguiente
          </Button>
        </div>
      </section>
      <section>
        <h2 className="mb-4 text-xl font-semibold">Invitaciones</h2>
        {invitations.isPending && <p role="status">Cargando invitaciones…</p>}
        {invitations.error && <p role="alert">{invitations.error.message}</p>}
        {invitations.data?.results.length === 0 && (
          <p className="text-muted-foreground">Aún no has creado invitaciones.</p>
        )}
        <div className="space-y-3">
          {invitations.data?.results.map((invitation) => (
            <article
              key={invitation.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-white p-4"
            >
              <div>
                <p className="break-all font-medium">{invitation.email}</p>
                <p className="text-sm text-muted-foreground">
                  {labels[invitation.role]} · {states[invitation.state]}
                </p>
                <p className="text-xs text-muted-foreground">
                  Vence: {new Date(invitation.expires_at).toLocaleString('es-CL')}
                </p>
              </div>
              {invitation.state === 'pending' && (
                <Button
                  variant="outline"
                  disabled={busy}
                  aria-label={`Revocar invitación de ${invitation.email}`}
                  onClick={() => {
                    void revoke(invitation.id)
                  }}
                >
                  Revocar invitación
                </Button>
              )}
            </article>
          ))}
        </div>
        <div className="mt-4 flex gap-3">
          <Button
            variant="outline"
            disabled={!invitations.data?.previous}
            onClick={() => setInvitePage((p) => p - 1)}
          >
            Invitaciones anteriores
          </Button>
          <Button
            variant="outline"
            disabled={!invitations.data?.next}
            onClick={() => setInvitePage((p) => p + 1)}
          >
            Invitaciones siguientes
          </Button>
        </div>
      </section>
    </section>
  )
}
