import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { reservationApi } from './api'
import { todayInZone } from './dates'
import { inputClass } from './ReservationForm'

export function AvailabilityPage() {
  const { tenant } = useTenantContext()
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [guests, setGuests] = useState(1)
  const [query, setQuery] = useState<{ start: string; end: string; guests: number } | null>(null)
  const [page, setPage] = useState(1)
  const result = useQuery({
    refetchInterval: 30_000,
    queryKey: ['availability', tenant.id, query, page],
    queryFn: () =>
      reservationApi.availability(
        tenant.id,
        query!.start,
        query!.end,
        query!.guests,
        undefined,
        page,
      ),
    enabled: Boolean(query),
  })
  return (
    <section>
      <Link to="/reservas" className="text-primary underline">
        Volver a reservas
      </Link>
      <h1 className="mt-5 text-3xl font-bold">Consultar disponibilidad</h1>
      <p className="mt-3 text-muted-foreground">
        Las consultas no retienen fechas. La disponibilidad se comprueba nuevamente al guardar.
      </p>
      <form
        className="mt-7 grid gap-5 rounded-xl border bg-white p-5 sm:grid-cols-3"
        onSubmit={(e) => {
          e.preventDefault()
          setPage(1)
          setQuery({ start, end, guests })
        }}
      >
        <label className="text-sm font-medium">
          Entrada
          <input
            required
            type="date"
            className={inputClass}
            min={todayInZone(tenant.timezone)}
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>
        <label className="text-sm font-medium">
          Salida (exclusiva)
          <input
            required
            type="date"
            className={inputClass}
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </label>
        <label className="text-sm font-medium">
          Personas
          <input
            required
            type="number"
            min="1"
            max="32767"
            className={inputClass}
            value={guests}
            onChange={(e) => setGuests(Number(e.target.value))}
          />
        </label>
        <Button type="submit">Consultar</Button>
      </form>
      {result.isFetching && (
        <p role="status" className="mt-6">
          Consultando disponibilidad…
        </p>
      )}
      {result.error && (
        <p role="alert" className="mt-6 text-red-800">
          {result.error.message}
        </p>
      )}
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {result.data?.results.map((item) => (
          <article key={item.property_id} className="rounded-xl border bg-white p-5">
            <h2 className="text-lg font-semibold">{item.property_name}</h2>
            <p className="mt-2 text-sm">Hasta {item.capacity} personas</p>
            <p
              className={`mt-3 font-medium ${item.available ? 'text-primary' : 'text-muted-foreground'}`}
            >
              {item.available ? 'Disponible' : 'No disponible'}
            </p>
          </article>
        ))}
      </div>
      {result.data?.count === 0 && <p className="mt-6">No hay cabañas activas para consultar.</p>}
      {result.data && (
        <div className="mt-6 flex flex-wrap items-center gap-4">
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
