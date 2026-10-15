import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { formatMoney, propertyApi } from '@/features/properties/api'
import { formatDate, todayInZone } from '@/features/reservations/dates'
import { dashboardApi } from './api'

export function monthPeriod(today: string) {
  const [year, month] = today.split('-').map(Number)
  return {
    start: `${today.slice(0, 7)}-01`,
    end: new Date(Date.UTC(year, month, 1)).toISOString().slice(0, 10),
  }
}

export function DashboardPage() {
  const { tenant } = useTenantContext()
  const initial = monthPeriod(todayInZone(tenant.timezone))
  const [start, setStart] = useState(initial.start)
  const [end, setEnd] = useState(initial.end)
  const [property, setProperty] = useState('')
  const [selected, setSelected] = useState<{ id: string; name: string; active: boolean } | null>(
    null,
  )
  const [search, setSearch] = useState('')
  const [propertyPage, setPropertyPage] = useState(1)
  const [period, setPeriod] = useState(initial)
  const properties = useQuery({
    queryKey: ['properties', tenant.id, search, propertyPage, 'all'],
    queryFn: () => propertyApi.list(tenant.id, search, 'all', propertyPage),
  })
  const result = useQuery({
    queryKey: ['dashboard', tenant.id, period, property],
    queryFn: () => dashboardApi.get(tenant.id, period.start, period.end, property || undefined),
    refetchInterval: 30_000,
  })
  return (
    <section>
      <p className="text-sm text-muted-foreground">{tenant.name}</p>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-bold">Panel administrativo</h1>
        <Button asChild variant="outline">
          <Link to="/reservas">Ver reservas</Link>
        </Button>
      </div>
      <form
        className="mt-7 grid gap-5 rounded-xl border border-border bg-white p-5 sm:grid-cols-2"
        onSubmit={(event) => {
          event.preventDefault()
          setPeriod({ start, end })
        }}
      >
        <label className="text-sm font-medium">
          Desde
          <input
            required
            type="date"
            className="mt-2 w-full rounded-lg border border-border p-3"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>
        <label className="text-sm font-medium">
          Hasta (exclusiva)
          <input
            required
            type="date"
            className="mt-2 w-full rounded-lg border border-border p-3"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </label>
        <label className="text-sm font-medium">
          Buscar cabaña
          <input
            maxLength={150}
            className="mt-2 w-full rounded-lg border border-border p-3"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPropertyPage(1)
            }}
          />
        </label>
        <div>
          <label htmlFor="dashboard-property" className="text-sm font-medium">
            Cabaña
          </label>
          <select
            id="dashboard-property"
            className="mt-2 w-full rounded-lg border border-border bg-white p-3"
            value={property}
            onChange={(e) => {
              setProperty(e.target.value)
              setSelected(
                properties.data?.results.find((item) => item.id === e.target.value) ?? null,
              )
            }}
          >
            <option value="">Todas las cabañas</option>
            {selected && !properties.data?.results.some((item) => item.id === selected.id) && (
              <option value={selected.id}>
                {selected.name}
                {selected.active ? '' : ' · Inactiva'}
              </option>
            )}
            {properties.data?.results.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
                {item.active ? '' : ' · Inactiva'}
              </option>
            ))}
          </select>
          <div className="mt-3 flex flex-wrap gap-3">
            <Button
              type="button"
              variant="outline"
              disabled={!properties.data?.previous}
              onClick={() => setPropertyPage(propertyPage - 1)}
            >
              Cabañas anteriores
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={!properties.data?.next}
              onClick={() => setPropertyPage(propertyPage + 1)}
            >
              Más cabañas
            </Button>
          </div>
        </div>
        <Button type="submit">Actualizar periodo</Button>
      </form>
      {properties.error && (
        <p role="alert" className="mt-4 text-red-800">
          {properties.error.message}
        </p>
      )}
      {result.isPending && (
        <p role="status" className="mt-6">
          Cargando indicadores…
        </p>
      )}
      {result.error && (
        <div role="alert" className="mt-6">
          <p>{result.error.message}</p>
          <Button
            className="mt-3"
            variant="outline"
            onClick={() => {
              void result.refetch()
            }}
          >
            Reintentar
          </Button>
        </div>
      )}
      {result.data && (
        <>
          <h2 className="mt-8 text-xl font-semibold">Hoy · {formatDate(result.data.today.date)}</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Situación actual de las cabañas activas en {result.data.timezone}.
          </p>
          <dl className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(
              [
                ['Reservadas hoy', result.data.today.occupied],
                ['Disponibles hoy', result.data.today.available],
                ['Retenidas hoy', result.data.today.retained],
                ['Bloqueadas hoy', result.data.today.blocked],
                ['Entradas de hoy', result.data.today.arrivals],
                ['Salidas de hoy', result.data.today.departures],
              ] as const
            ).map(([label, value]) => (
              <div key={label} className="rounded-xl border border-border bg-white p-5">
                <dt className="text-sm text-muted-foreground">{label}</dt>
                <dd className="mt-2 text-3xl font-semibold">{value}</dd>
              </div>
            ))}
          </dl>
          <section className="mt-8 rounded-xl border border-border bg-white p-6">
            <h2 className="text-xl font-semibold">Ocupación del periodo</h2>
            <p className="mt-3 text-3xl font-semibold">
              {result.data.occupancy_percent.replace('.', ',')} %
            </p>
            <progress
              className="mt-4 w-full accent-primary"
              max={100}
              value={Number(result.data.occupancy_percent)}
              aria-label="Ocupación del periodo"
            />
            <p className="mt-3 text-sm text-muted-foreground">
              {result.data.occupied_nights} noches reservadas de {result.data.capacity_nights}{' '}
              noches de cabañas actualmente activas. {result.data.blocked_nights} noches bloqueadas,
              mostradas aparte. Las retenciones no suman ocupación.
            </p>
          </section>
          <h2 className="mt-8 text-xl font-semibold">Importes del periodo</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Cobrado: pagos válidos recibidos en el periodo. Pactado y saldos: reservas con entrada
            en el periodo. Deuda y saldo a favor se mantienen separados.
          </p>
          {result.data.money.map((group) => (
            <dl key={group.currency} className="mt-5 grid gap-4 sm:grid-cols-2">
              {(
                [
                  ['Cobrado', group.collected],
                  ['Pactado', group.agreed],
                  ['Deuda', group.outstanding],
                  ['Saldo a favor', group.credit],
                ] as const
              ).map(([label, value]) => (
                <div key={label} className="rounded-xl border border-border bg-white p-5">
                  <dt className="text-sm text-muted-foreground">
                    {label} · {group.currency}
                  </dt>
                  <dd className="mt-2 break-words text-2xl font-semibold">
                    {formatMoney(value, group.currency)}
                  </dd>
                </div>
              ))}
            </dl>
          ))}
        </>
      )}
    </section>
  )
}
