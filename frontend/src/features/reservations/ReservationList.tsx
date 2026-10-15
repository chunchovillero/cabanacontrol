import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { formatMoney } from '@/features/properties/api'
import { reservationApi, statusLabels } from './api'
import { formatDate } from './dates'
import { paymentLabels } from '@/features/payments/api'

export function ReservationList() {
  const { tenant } = useTenantContext()
  const [status, setStatus] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [page, setPage] = useState(1)
  const [debt, setDebt] = useState(false)
  const filters = {
    ...(debt ? { debt: 'true' } : {}),
    page: String(page),
    ...(status ? { status } : {}),
    ...(start ? { from_date: start } : {}),
    ...(end ? { to_date: end } : {}),
  }
  const result = useQuery({
    refetchInterval: 30_000,
    queryKey: ['reservations', tenant.id, filters],
    queryFn: () => reservationApi.list(tenant.id, filters),
  })
  return (
    <section>
      <p className="text-sm text-muted-foreground">{tenant.name}</p>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-bold">Reservas</h1>
        <Button asChild>
          <Link to="/reservas/nueva">Nueva reserva</Link>
        </Button>
      </div>
      <div className="mt-5 flex flex-wrap gap-5 text-sm text-primary underline">
        <Link to="/reservas/disponibilidad">Consultar disponibilidad</Link>
        <Link to="/reservas/bloqueos">Bloqueos de fechas</Link>
      </div>
      <div className="mt-7 grid gap-4 rounded-xl border border-border bg-white p-5 sm:grid-cols-3">
        <label className="text-sm font-medium">
          Estado
          <select
            className="mt-2 w-full rounded-lg border p-3"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value)
              setPage(1)
            }}
          >
            <option value="">Todos</option>
            {Object.entries(statusLabels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium">
          Desde
          <input
            type="date"
            className="mt-2 w-full rounded-lg border p-3"
            value={start}
            onChange={(e) => {
              setStart(e.target.value)
              setPage(1)
            }}
          />
        </label>
        <label className="text-sm font-medium">
          Hasta (exclusiva)
          <input
            type="date"
            className="mt-2 w-full rounded-lg border p-3"
            value={end}
            onChange={(e) => {
              setEnd(e.target.value)
              setPage(1)
            }}
          />
        </label>
      </div>
      <label className="mt-5 flex items-center gap-3 text-sm font-medium">
        <input
          type="checkbox"
          checked={debt}
          onChange={(e) => {
            setDebt(e.target.checked)
            setPage(1)
          }}
        />
        Solo reservas con deuda
      </label>
      {result.isPending && (
        <p role="status" className="mt-6">
          Cargando reservas…
        </p>
      )}
      {result.error && (
        <p role="alert" className="mt-6 text-red-800">
          {result.error.message}
        </p>
      )}
      {result.data?.count === 0 && (
        <p className="mt-8 rounded-xl border border-dashed p-8 text-center">
          No hay reservas para mostrar.
        </p>
      )}
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {result.data?.results.map((item) => (
          <article key={item.id} className="rounded-xl border border-border bg-white p-5 shadow-sm">
            <span className="rounded-full bg-muted px-3 py-1 text-xs">
              {statusLabels[item.status]}
              {item.status === 'pending' && !item.hold_active ? ' · Retención vencida' : ''}
            </span>
            <h2 className="mt-4 text-xl font-semibold">
              <Link className="hover:underline" to={`/reservas/${item.id}`}>
                {item.property_name}
              </Link>
            </h2>
            <p className="mt-2">
              {formatDate(item.check_in)} → {formatDate(item.check_out)}
            </p>
            <p className="mt-2 break-words text-sm text-muted-foreground">
              {item.guest.first_name} {item.guest.last_name} · {item.adults + item.children}{' '}
              personas
            </p>
            <p className="mt-3 font-semibold">{formatMoney(item.total_amount, item.currency)}</p>
            <p className="mt-2 text-sm text-muted-foreground">
              {paymentLabels[item.payment_state]} ·{' '}
              {item.payment_state === 'credit' ? 'A favor' : 'Saldo'}{' '}
              {formatMoney(item.balance.replace(/^-/, ''), item.currency)}
            </p>
            <Link className="mt-4 inline-block text-primary underline" to={`/reservas/${item.id}`}>
              Ver reserva
            </Link>
          </article>
        ))}
      </div>
      {result.data && (
        <div className="mt-6 flex flex-wrap items-center gap-4">
          <Button
            variant="outline"
            disabled={!result.data.previous}
            onClick={() => setPage(page - 1)}
          >
            Anterior
          </Button>
          <span className="text-sm">
            Página {page} · {result.data.count} reservas
          </span>
          <Button variant="outline" disabled={!result.data.next} onClick={() => setPage(page + 1)}>
            Siguiente
          </Button>
        </div>
      )}
    </section>
  )
}
