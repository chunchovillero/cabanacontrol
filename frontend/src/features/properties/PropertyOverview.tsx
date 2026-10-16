import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { reservationApi, statusLabels } from '@/features/reservations/api'
import { todayInZone, formatDate } from '@/features/reservations/dates'
import { dashboardApi } from '@/features/dashboard/api'
import { formatMoney } from './api'

function PropertyReservations({
  tenantId,
  propertyId,
  scope,
}: {
  tenantId: string
  propertyId: string
  scope: 'upcoming' | 'history'
}) {
  const [page, setPage] = useState(1)
  const query = useQuery({
    queryKey: ['reservations', tenantId, propertyId, scope, page],
    queryFn: () =>
      reservationApi.list(tenantId, { property_id: propertyId, scope, page: String(page) }),
  })
  return (
    <section className="mt-8">
      <h2 className="text-xl font-semibold">
        {scope === 'upcoming' ? 'Próximas reservas y estadías actuales' : 'Historial de reservas'}
      </h2>
      {query.isPending && (
        <p role="status" className="mt-4">
          Cargando reservas…
        </p>
      )}
      {query.error && (
        <p role="alert" className="mt-4">
          {query.error.message}{' '}
          <button className="underline" onClick={() => void query.refetch()}>
            Reintentar
          </button>
        </p>
      )}
      {query.data?.count === 0 && (
        <p className="mt-4 rounded-xl border border-dashed border-border p-5 text-muted-foreground">
          {scope === 'upcoming'
            ? 'No hay próximas reservas para esta cabaña.'
            : 'Todavía no hay reservas en el historial.'}
        </p>
      )}
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {query.data?.results.map((reservation) => (
          <Link
            key={reservation.id}
            to={`/reservas/${reservation.id}`}
            className="rounded-xl border border-border bg-white p-4 transition hover:border-primary"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold">
                {formatDate(reservation.check_in)} → {formatDate(reservation.check_out)}
              </span>
              <span className="rounded-full bg-muted px-2 py-1 text-xs">
                {statusLabels[reservation.status]}
              </span>
            </div>
            <p className="mt-3 text-sm">{reservation.adults + reservation.children} personas</p>
            <div className="mt-3 flex flex-wrap justify-between gap-2 text-sm">
              <span>Total: {formatMoney(reservation.total_amount, reservation.currency)}</span>
              <span>Saldo: {formatMoney(reservation.balance, reservation.currency)}</span>
            </div>
            <span className="mt-3 block text-sm font-medium text-primary">Ver reserva →</span>
          </Link>
        ))}
      </div>
      {!!query.data?.count && (
        <div className="mt-4 flex items-center justify-between gap-2">
          <span className="text-sm text-muted-foreground">
            {query.data.count} reservas · Página {page}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              disabled={!query.data.previous}
              onClick={() => setPage(page - 1)}
            >
              Anterior
            </Button>
            <Button variant="outline" disabled={!query.data.next} onClick={() => setPage(page + 1)}>
              Siguiente
            </Button>
          </div>
        </div>
      )}
    </section>
  )
}

export function PropertyOverview({
  tenantId,
  propertyId,
  timezone,
  active,
}: {
  tenantId: string
  propertyId: string
  timezone: string
  active: boolean
}) {
  const today = todayInZone(timezone)
  const [start, setStart] = useState(`${today.slice(0, 7)}-01`)
  const [end, setEnd] = useState(() => {
    const [year, month] = today.split('-').map(Number)
    return new Date(Date.UTC(year, month, 1)).toISOString().slice(0, 10)
  })
  const validPeriod = !!start && !!end && start < end
  const summary = useQuery({
    queryKey: ['dashboard', tenantId, propertyId, start, end],
    queryFn: () => dashboardApi.get(tenantId, start, end, propertyId),
    enabled: validPeriod,
  })
  return (
    <>
      {active && (
        <Button asChild className="mt-6 w-full sm:w-auto">
          <Link to={`/reservas/nueva?property_id=${encodeURIComponent(propertyId)}`}>
            Crear reserva para esta cabaña
          </Link>
        </Button>
      )}
      <section className="mt-8 rounded-2xl border border-border bg-white p-4 sm:p-6">
        <h2 className="text-xl font-semibold">Ingresos de esta cabaña</h2>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <label className="min-w-0 text-sm">
            Desde
            <input
              type="date"
              value={start}
              onChange={(event) => setStart(event.target.value)}
              className="mt-2 w-full min-w-0 rounded-lg border border-border p-2"
            />
          </label>
          <label className="min-w-0 text-sm">
            Hasta (exclusiva)
            <input
              type="date"
              value={end}
              onChange={(event) => setEnd(event.target.value)}
              className="mt-2 w-full min-w-0 rounded-lg border border-border p-2"
            />
          </label>
        </div>
        {!validPeriod && (
          <p role="alert" className="mt-3">
            La fecha final debe ser posterior a la inicial.
          </p>
        )}
        {validPeriod && summary.isPending && (
          <p role="status" className="mt-4">
            Cargando ingresos…
          </p>
        )}
        {summary.error && (
          <p role="alert" className="mt-4">
            {summary.error.message}{' '}
            <button className="underline" onClick={() => void summary.refetch()}>
              Reintentar
            </button>
          </p>
        )}
        {validPeriod && summary.data && (
          <>
            {summary.data.money.length === 0 && (
              <p className="mt-4 text-muted-foreground">Sin movimientos en este periodo.</p>
            )}
            {summary.data.money.map((money) => (
              <dl key={money.currency} className="mt-5 grid grid-cols-2 gap-4">
                {[
                  ['Cobrado en el periodo', money.collected],
                  ['Pactado para entradas del periodo', money.agreed],
                  ['Saldo pendiente de esas reservas', money.outstanding],
                  ['Saldo a favor del huésped', money.credit],
                ].map(([label, amount]) => (
                  <div key={label} className="rounded-xl bg-muted p-3">
                    <dt className="text-xs text-muted-foreground">{label}</dt>
                    <dd className="mt-2 break-words text-lg font-semibold">
                      {formatMoney(amount, money.currency)}
                    </dd>
                  </div>
                ))}
              </dl>
            ))}
            <p className="mt-4 text-sm text-muted-foreground">
              Ocupación del periodo: {summary.data.occupancy_percent}%
            </p>
          </>
        )}
        <p className="mt-4 text-xs text-muted-foreground">
          Los ingresos cobrados corresponden a pagos recibidos en las fechas elegidas. La ganancia
          neta requiere registrar gastos, una función aún no disponible.
        </p>
      </section>
      <PropertyReservations tenantId={tenantId} propertyId={propertyId} scope="upcoming" />
      <PropertyReservations tenantId={tenantId} propertyId={propertyId} scope="history" />
    </>
  )
}
