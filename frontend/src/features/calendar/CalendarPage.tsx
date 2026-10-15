import { useCallback, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import FullCalendar, {
  type DatesSetInfo,
  type EventClickInfo,
  type EventInput,
} from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/react/daygrid'
import themePlugin from '@fullcalendar/react/themes/monarch'
import esLocale from '@fullcalendar/react/locales/es'
import '@fullcalendar/react/skeleton.css'
import '@fullcalendar/react/themes/monarch/theme.css'
import '@fullcalendar/react/themes/monarch/palettes/green.css'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { propertyApi } from '@/features/properties/api'
import { formatDate, todayInZone } from '@/features/reservations/dates'
import { monthPeriod } from '@/features/dashboard/DashboardPage'
import { calendarApi, type CalendarEvent } from './api'
import './calendar.css'

const plugins = [dayGridPlugin, themePlugin]
const colors: Record<string, string> = {
  draft: '#475569',
  pending: '#92400e',
  confirmed: '#166534',
  checked_in: '#075985',
  checked_out: '#4338ca',
  cancelled: '#991b1b',
  no_show: '#831843',
}
export function calendarInput(event: CalendarEvent): EventInput {
  return {
    id: event.id,
    title: event.title,
    start: event.start,
    end: event.end,
    allDay: true,
    url: event.url,
    color: event.kind === 'block' ? '#374151' : (colors[event.status] ?? '#475569'),
    contrastColor: '#ffffff',
  }
}

export function CalendarPage() {
  const { tenant } = useTenantContext()
  const navigate = useNavigate()
  const today = todayInZone(tenant.timezone)
  const [period, setPeriod] = useState(() => monthPeriod(today))
  const [property, setProperty] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<{ id: string; name: string; active: boolean } | null>(
    null,
  )
  const [filter, setFilter] = useState('all')
  const properties = useQuery({
    queryKey: ['properties', tenant.id, search, page, 'all'],
    queryFn: () => propertyApi.list(tenant.id, search, 'all', page),
  })
  const result = useQuery({
    queryKey: ['calendar', tenant.id, period, property],
    queryFn: () => calendarApi.get(tenant.id, period.start, period.end, property || undefined),
    refetchInterval: 30_000,
  })
  const visible = useMemo(
    () =>
      (result.data?.events ?? []).filter(
        (event) =>
          filter === 'all' ||
          (filter === 'blocking' ? event.blocks_inventory : event.kind === filter),
      ),
    [result.data, filter],
  )
  const events = useMemo(() => visible.map(calendarInput), [visible])
  const datesSet = useCallback((info: DatesSetInfo) => {
    const next = { start: info.startStr.slice(0, 10), end: info.endStr.slice(0, 10) }
    setPeriod((previous) =>
      previous.start === next.start && previous.end === next.end ? previous : next,
    )
  }, [])
  const eventClick = useCallback(
    (info: EventClickInfo) => {
      info.jsEvent.preventDefault()
      if (info.event.url) navigate(info.event.url)
    },
    [navigate],
  )
  return (
    <section>
      <p className="text-sm text-muted-foreground">{tenant.name}</p>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-bold">Calendario de reservas</h1>
        <Button asChild variant="outline">
          <Link to="/panel">Ver panel</Link>
        </Button>
      </div>
      <p className="mt-3 text-sm text-muted-foreground">
        Estadías por noche: la fecha de salida queda libre. Hora de la empresa: {tenant.timezone}.
        Incluye historial de cabañas inactivas.
      </p>
      <div className="mt-6 grid gap-4 rounded-xl border border-border bg-white p-4 sm:grid-cols-2">
        <label>
          Buscar cabaña
          <input
            className="mt-2 w-full rounded-lg border p-3"
            maxLength={150}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
          />
        </label>
        <label>
          Cabaña
          <select
            aria-label="Cabaña"
            className="mt-2 w-full rounded-lg border bg-white p-3"
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
        </label>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            disabled={!properties.data?.previous}
            onClick={() => setPage(page - 1)}
          >
            Cabañas anteriores
          </Button>
          <Button
            variant="outline"
            disabled={!properties.data?.next}
            onClick={() => setPage(page + 1)}
          >
            Más cabañas
          </Button>
        </div>
        <label>
          Mostrar
          <select
            aria-label="Mostrar"
            className="mt-2 w-full rounded-lg border bg-white p-3"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">Todos los estados</option>
            <option value="blocking">Solo inventario retenido u ocupado</option>
            <option value="reservation">Reservas</option>
            <option value="block">Bloqueos</option>
          </select>
        </label>
      </div>
      {properties.error && (
        <p role="alert" className="mt-4">
          {properties.error.message}
        </p>
      )}
      {result.isPending && (
        <p role="status" className="mt-4">
          Cargando calendario…
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
      <div className="cabin-calendar mt-6 min-w-0 rounded-xl border border-border bg-white p-2 sm:p-5">
        <FullCalendar
          plugins={plugins}
          locale={esLocale}
          initialDate={today}
          now={today}
          timeZone="UTC"
          initialView="dayGridMonth"
          headerToolbar={{
            start: 'prev,next today',
            center: 'title',
            end: 'dayGridMonth,dayGridWeek',
          }}
          headerToolbarClass="calendar-toolbar"
          toolbarTitleClass="calendar-title"
          eventClass="calendar-event"
          height="auto"
          editable={false}
          selectable={false}
          dayMaxEvents={3}
          events={events}
          datesSet={datesSet}
          eventClick={eventClick}
        />
      </div>
      <h2 className="mt-6 text-xl font-semibold">Eventos del periodo visible</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Los títulos indican el estado. Borradores, canceladas, ausencias y retenciones vencidas no
        bloquean disponibilidad.
      </p>
      {result.data && !visible.length && <p className="mt-4">No hay eventos para estos filtros.</p>}
      <ul className="mt-4 grid gap-3 sm:grid-cols-2">
        {visible.map((event) => (
          <li key={event.id} className="min-w-0 rounded-lg border bg-white p-4">
            <Link to={event.url} className="break-words font-medium text-primary underline">
              {event.title}
            </Link>
            <p className="mt-2 text-sm">
              {formatDate(event.start)} → {formatDate(event.end)} (salida)
            </p>
            <p className="text-sm text-muted-foreground">
              {event.blocks_inventory ? 'Retiene disponibilidad' : 'Sin retención'}
              {event.property_active ? '' : ' · Cabaña inactiva'}
            </p>
          </li>
        ))}
      </ul>
    </section>
  )
}
