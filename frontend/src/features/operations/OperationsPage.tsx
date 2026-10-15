import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { PropertyFilter } from '@/features/reports/PropertyFilter'
import { statusLabels } from '@/features/reservations/api'
import { formatDate, todayInZone } from '@/features/reservations/dates'
import { operationsApi, dayKinds, type DayKind } from './api'

export function OperationsPage() {
  const { tenant, canEdit } = useTenantContext()
  const [date, setDate] = useState(todayInZone(tenant.timezone))
  const [day, setDay] = useState(date)
  const [kind, setKind] = useState<DayKind>('arrivals')
  const [page, setPage] = useState(1)
  const [property, setProperty] = useState('')
  const result = useQuery({
    queryKey: ['operations', tenant.id, day, kind, page, property],
    queryFn: () => operationsApi.day(tenant.id, day, kind, page, property || undefined),
    refetchInterval: 30000,
  })
  return (
    <section>
      <p className="text-sm text-muted-foreground">{tenant.name}</p>
      <h1 className="mt-2 text-3xl font-bold">Operación diaria</h1>
      <p className="mt-3 text-sm text-muted-foreground">
        Fecha de la empresa en {tenant.timezone}. Entradas y salidas según fechas reservadas y
        estado actual; retenciones evaluadas al momento de consultar. Las alertas no cambian estados
        automáticamente.
      </p>
      <div className="mt-5 flex flex-wrap gap-3">
        <Button asChild variant="outline">
          <Link to="/reservas/bloqueos">Ver mantenimiento y bloqueos</Link>
        </Button>
        <Button asChild variant="outline">
          <Link to="/limpieza">Ver tareas de limpieza</Link>
        </Button>
        {canEdit && (
          <Button asChild>
            <Link to="/reservas/bloqueos/nuevo">Bloquear por mantenimiento</Link>
          </Button>
        )}
      </div>
      <form
        className="mt-6 flex flex-wrap items-end gap-4 rounded-xl border bg-white p-5"
        onSubmit={(e) => {
          e.preventDefault()
          setDay(date)
          setPage(1)
        }}
      >
        <label>
          Fecha de operación
          <input
            required
            type="date"
            className="mt-2 block rounded-lg border p-3"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>
        <Button type="submit">Consultar día</Button>
      </form>
      <div className="mt-4 rounded-xl border bg-white p-5">
        <PropertyFilter
          tenant={tenant.id}
          value={property}
          onChange={(value) => {
            setProperty(value)
            setPage(1)
          }}
        />
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {(Object.entries(dayKinds) as [DayKind, string][]).map(([value, label]) => (
          <Button
            key={value}
            variant={value === kind ? 'default' : 'outline'}
            aria-pressed={value === kind}
            onClick={() => {
              setKind(value)
              setPage(1)
            }}
          >
            {label} · {result.data?.counts[value] ?? '…'}
          </Button>
        ))}
      </div>
      <h2 className="mt-7 text-xl font-semibold">
        {dayKinds[kind]} · {formatDate(day)}
      </h2>
      {result.isPending && (
        <p role="status" className="mt-4">
          Cargando operación…
        </p>
      )}
      {result.error && (
        <div role="alert" className="mt-4">
          <p>{result.error.message}</p>
          <Button
            variant="outline"
            onClick={() => {
              void result.refetch()
            }}
          >
            Reintentar
          </Button>
        </div>
      )}
      {result.data && !result.data.count && (
        <p className="mt-4">No hay registros para esta consulta.</p>
      )}
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        {result.data?.results.map((row) => (
          <article key={row.id} className="min-w-0 rounded-xl border bg-white p-5">
            <h3 className="break-words font-semibold">
              <Link to={row.url} className="text-primary underline">
                {row.property_name}
              </Link>
            </h3>
            <p className="mt-2">
              {kind === 'cleaning'
                ? `Vence: ${formatDate(row.start)}`
                : `${formatDate(row.start)} → ${formatDate(row.end)} (salida)`}
            </p>
            <p className="mt-2">
              {row.status === 'maintenance'
                ? 'Mantenimiento'
                : row.status === 'in_progress'
                  ? 'En curso'
                  : statusLabels[row.status as keyof typeof statusLabels]}
            </p>
            {!row.property_active && <p className="mt-2 text-sm">Cabaña inactiva</p>}
            <p className="mt-3 text-sm text-muted-foreground">
              {kind === 'maintenance'
                ? 'Gestiona las fechas desde bloqueos.'
                : kind === 'cleaning'
                  ? 'Abre la tarea para asignar responsable y completar el checklist.'
                  : 'Revisa la ficha para registrar check-in/out o resolver la alerta.'}
            </p>
          </article>
        ))}
      </div>
      {result.data && (
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <Button
            variant="outline"
            disabled={!result.data.previous}
            onClick={() => setPage(page - 1)}
          >
            Anterior
          </Button>
          <span>Página {page}</span>
          <Button variant="outline" disabled={!result.data.next} onClick={() => setPage(page + 1)}>
            Siguiente
          </Button>
        </div>
      )}
    </section>
  )
}
