import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { formatMoney } from '@/features/properties/api'
import { reservationApi, sourceLabels, statusLabels } from './api'
import { formatDate, formatHold, holdToIso } from './dates'
import { PaymentPanel } from '@/features/payments/PaymentPanel'
import { WhatsAppComposer } from '@/features/operations/WhatsAppComposer'

export function ReservationDetail() {
  const { id } = useParams()
  const { tenant } = useTenantContext()
  const client = useQueryClient()
  const result = useQuery({
    refetchInterval: 30_000,
    queryKey: ['reservation', tenant.id, id],
    queryFn: () => reservationApi.get(tenant.id, id!),
  })
  const [mode, setMode] = useState('')
  const [reason, setReason] = useState('')
  const [hold, setHold] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  async function action() {
    setError('')
    setSaving(true)
    try {
      const endpoint = mode === 'confirmed' ? 'confirm' : mode === 'cancelled' ? 'cancel' : 'status'
      const data: Record<string, string | null> =
        endpoint === 'confirm'
          ? {}
          : endpoint === 'cancel'
            ? { reason }
            : {
                status: mode,
                reason,
                ...(mode === 'pending' ? { hold_until: holdToIso(hold, tenant.timezone) } : {}),
              }
      const saved = await reservationApi.action(tenant.id, id!, endpoint, data)
      client.setQueryData(['reservation', tenant.id, id], saved)
      await client.invalidateQueries({ queryKey: ['reservations', tenant.id] })
      await client.invalidateQueries({ queryKey: ['availability', tenant.id] })
      await client.invalidateQueries({ queryKey: ['operations', tenant.id] })
      await client.invalidateQueries({ queryKey: ['housekeeping', tenant.id] })
      await client.invalidateQueries({ queryKey: ['whatsapp-draft', tenant.id, id] })
      setMode('')
      setReason('')
      setHold('')
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo cambiar el estado.')
    } finally {
      setSaving(false)
    }
  }
  if (result.isPending) return <p role="status">Cargando reserva…</p>
  if (result.error) return <p role="alert">{result.error.message}</p>
  const item = result.data!
  const actions: Record<string, string[]> = {
    draft: ['pending', 'confirmed', 'cancelled'],
    pending: ['draft', 'confirmed', 'cancelled'],
    confirmed: ['checked_in', 'no_show', 'cancelled'],
    checked_in: ['checked_out'],
  }
  return (
    <section>
      <Link to="/reservas" className="text-sm text-primary underline">
        Volver a reservas
      </Link>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-bold">Reserva · {item.property_name}</h1>
        {actions[item.status] && (
          <Button asChild variant="outline">
            <Link to={`/reservas/${item.id}/editar`}>Editar reserva</Link>
          </Button>
        )}
      </div>
      <span className="mt-5 inline-block rounded-full bg-muted px-3 py-1 text-sm">
        {statusLabels[item.status]}
      </span>
      {item.status === 'pending' && (
        <p className="mt-3 text-sm">
          {item.hold_active ? 'Retención vigente hasta' : 'Retención vencida desde'}{' '}
          {formatHold(item.hold_until!, tenant.timezone)} ({tenant.timezone}).
        </p>
      )}
      <dl className="mt-6 grid gap-6 rounded-xl border border-border bg-white p-6 sm:grid-cols-2">
        <div>
          <dt className="text-sm text-muted-foreground">Estadía</dt>
          <dd className="mt-2 font-medium">
            {formatDate(item.check_in)} → {formatDate(item.check_out)}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">Personas</dt>
          <dd className="mt-2">
            {item.adults} adultos · {item.children} niños
          </dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">Huésped principal</dt>
          <dd className="mt-2 break-words">
            <Link to={`/huespedes/${item.primary_guest_id}`} className="text-primary underline">
              {item.guest.first_name} {item.guest.last_name}
            </Link>
          </dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">Precio pactado</dt>
          <dd className="mt-2 text-xl font-semibold">
            {formatMoney(item.total_amount, item.currency)}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">Origen</dt>
          <dd className="mt-2">{sourceLabels[item.source]}</dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">Notas operativas</dt>
          <dd className="mt-2 whitespace-pre-wrap break-words">{item.notes || 'Sin notas'}</dd>
        </div>
        {item.cancel_reason && (
          <div>
            <dt className="text-sm text-muted-foreground">Motivo de cierre</dt>
            <dd className="mt-2 whitespace-pre-wrap break-words">{item.cancel_reason}</dd>
          </div>
        )}
      </dl>
      <div className="mt-6 flex flex-wrap gap-3">
        {actions[item.status]?.map((status) => (
          <Button
            key={status}
            variant="outline"
            onClick={() => {
              setMode(status)
              setError('')
            }}
          >
            {status === 'confirmed'
              ? 'Confirmar reserva'
              : status === 'cancelled'
                ? 'Cancelar reserva'
                : status === 'pending'
                  ? 'Retener fechas'
                  : statusLabels[status as keyof typeof statusLabels]}
          </Button>
        ))}
      </div>
      {mode && (
        <div
          role="dialog"
          aria-modal="false"
          aria-label="Confirmar cambio de estado"
          className="mt-6 space-y-4 rounded-xl border border-border bg-white p-6"
        >
          <h2 className="font-semibold">
            Cambiar a {statusLabels[mode as keyof typeof statusLabels]}
          </h2>
          {['cancelled', 'no_show'].includes(mode) && (
            <label className="block text-sm">
              Motivo obligatorio
              <textarea
                className="mt-2 w-full rounded-lg border p-3"
                maxLength={1000}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </label>
          )}
          {mode === 'pending' && (
            <label className="block text-sm">
              Retener hasta
              <input
                type="datetime-local"
                className="mt-2 w-full rounded-lg border p-3"
                value={hold}
                onChange={(e) => setHold(e.target.value)}
              />
              <span className="mt-2 block">Hora de {tenant.timezone}</span>
            </label>
          )}
          {error && (
            <p role="alert" className="text-red-800">
              {error}
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <Button
              disabled={
                saving ||
                (['cancelled', 'no_show'].includes(mode) && !reason.trim()) ||
                (mode === 'pending' && !hold)
              }
              onClick={() => {
                void action()
              }}
            >
              {saving ? 'Guardando…' : 'Aplicar cambio'}
            </Button>
            <Button disabled={saving} variant="outline" onClick={() => setMode('')}>
              Volver sin cambiar
            </Button>
          </div>
        </div>
      )}
      <PaymentPanel reservation={item} />
      <WhatsAppComposer reservationId={item.id} />
    </section>
  )
}
