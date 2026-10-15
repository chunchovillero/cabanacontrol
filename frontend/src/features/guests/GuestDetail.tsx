import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { documentLabels, guestApi } from './api'

export function GuestDetail() {
  const { tenant, canEdit } = useTenantContext()
  const { id = '' } = useParams()
  const client = useQueryClient()
  const [confirm, setConfirm] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const query = useQuery({
    queryKey: ['guest', tenant.id, id],
    queryFn: () => guestApi.get(tenant.id, id),
    retry: false,
  })
  if (query.isPending) return <p role="status">Cargando ficha…</p>
  if (query.error || !query.data)
    return (
      <section role="alert">
        <p>{query.error?.message ?? 'Huésped no disponible.'}</p>
        <Link to="/huespedes" className="mt-4 inline-block text-primary underline">
          Volver a huéspedes
        </Link>
      </section>
    )
  const guest = query.data
  const toggle = async () => {
    setPending(true)
    setError('')
    try {
      const saved = await guestApi.update(tenant.id, id, { active: !guest.active })
      client.setQueryData(['guest', tenant.id, id], saved)
      await client.invalidateQueries({ queryKey: ['guests', tenant.id] })
      setConfirm(false)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo cambiar el estado.')
    } finally {
      setPending(false)
    }
  }
  return (
    <section>
      <Link to="/huespedes" className="text-sm text-primary underline">
        Volver a huéspedes
      </Link>
      <div className="mt-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">{guest.active ? 'Activo' : 'Inactivo'}</p>
          <h1 className="mt-2 break-words text-3xl font-bold">
            {guest.first_name} {guest.last_name}
          </h1>
        </div>
        {canEdit && (
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline">
              <Link to={`/huespedes/${id}/editar`}>Editar huésped</Link>
            </Button>
            <Button variant="outline" onClick={() => setConfirm(true)}>
              {guest.active ? 'Desactivar huésped' : 'Reactivar huésped'}
            </Button>
          </div>
        )}
      </div>
      {confirm && (
        <section
          role="alertdialog"
          aria-modal="false"
          aria-labelledby="guest-state-title"
          className="mt-6 rounded-xl border border-border bg-white p-6"
        >
          <h2 id="guest-state-title" className="font-semibold">
            {guest.active ? '¿Desactivar esta ficha?' : '¿Reactivar esta ficha?'}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Se conservarán sus datos y trazabilidad.
          </p>
          <div className="mt-4 flex gap-3">
            <Button
              disabled={pending}
              onClick={() => {
                void toggle()
              }}
            >
              {pending ? 'Guardando…' : 'Confirmar'}
            </Button>
            <Button disabled={pending} variant="outline" onClick={() => setConfirm(false)}>
              Cancelar
            </Button>
          </div>
        </section>
      )}
      {error && (
        <p role="alert" className="mt-5 text-red-800">
          {error}
        </p>
      )}
      <dl className="mt-8 grid gap-6 rounded-xl border border-border bg-white p-6 sm:grid-cols-3">
        <div>
          <dt className="text-sm text-muted-foreground">{documentLabels[guest.document_type]}</dt>
          <dd className="mt-2 break-words font-semibold">
            {canEdit ? guest.document_number : guest.document_masked}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">Teléfono</dt>
          <dd className="mt-2 break-words font-semibold">
            {guest.phone || 'Sin teléfono registrado'}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">Correo electrónico</dt>
          <dd className="mt-2 break-all font-semibold">{guest.email || 'Sin correo registrado'}</dd>
        </div>
      </dl>
      {canEdit && (
        <section className="mt-6 rounded-xl border border-border bg-white p-6">
          <h2 className="font-semibold">Notas restringidas</h2>
          <p className="mt-3 whitespace-pre-wrap text-sm">
            {guest.notes || 'Sin notas registradas.'}
          </p>
        </section>
      )}
    </section>
  )
}
