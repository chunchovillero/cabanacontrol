import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { PropertyFilter } from '@/features/reports/PropertyFilter'
import { holdToIso, localHold, todayInZone } from '@/features/reservations/dates'
import { housekeepingApi, taskLabels, type Task } from './housekeepingApi'

const checklist = {
  bathroom: 'Baño',
  kitchen: 'Cocina',
  bedrooms: 'Dormitorios',
  inventory: 'Inventario',
}
const dueLabel = (value: string, zone: string) =>
  new Intl.DateTimeFormat('es-CL', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: zone,
  }).format(new Date(value))

export function HousekeepingList() {
  const { tenant } = useTenantContext()
  const [status, setStatus] = useState('pending')
  const [page, setPage] = useState(1)
  const result = useQuery({
    queryKey: ['housekeeping', tenant.id, status, page],
    queryFn: () => housekeepingApi.list(tenant.id, status, page),
    refetchInterval: 30000,
  })
  return (
    <section>
      <p className="text-sm text-muted-foreground">{tenant.name}</p>
      <div className="mt-2 flex flex-wrap justify-between gap-3">
        <h1 className="text-3xl font-bold">Tareas de limpieza</h1>
        <Button asChild>
          <Link to="/limpieza/nueva">Nueva limpieza</Link>
        </Button>
      </div>
      <p className="mt-3 text-sm text-muted-foreground">
        Cada check-out crea una limpieza. Las tareas pendientes generan alertas y no bloquean
        disponibilidad. Vencimientos en {tenant.timezone}.
      </p>
      <div className="mt-5">
        <label htmlFor="task-state">Estado de tarea</label>
        <select
          id="task-state"
          className="ml-3 rounded-lg border bg-white p-3"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value)
            setPage(1)
          }}
        >
          <option value="">Todos los estados</option>
          {Object.entries(taskLabels).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </div>
      {result.isPending && (
        <p role="status" className="mt-5">
          Cargando tareas…
        </p>
      )}
      {result.error && (
        <p role="alert" className="mt-5">
          {result.error.message}
        </p>
      )}
      {result.data?.count === 0 && <p className="mt-5">No hay tareas para este filtro.</p>}
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        {result.data?.results.map((task) => (
          <article key={task.id} className="min-w-0 rounded-xl border bg-white p-5">
            <h2 className="break-words font-semibold">
              <Link to={`/limpieza/${task.id}`} className="text-primary underline">
                {task.property_name}
              </Link>
            </h2>
            <p className="mt-2">
              {taskLabels[task.status]} · {task.source === 'checkout' ? 'Check-out' : 'Manual'}
            </p>
            <p>Vence: {dueLabel(task.due_at, tenant.timezone)}</p>
            <p>Responsable: {task.assigned_name || 'Sin asignar'}</p>
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

function TaskEditor({ task }: { task?: Task }) {
  const { tenant } = useTenantContext()
  const navigate = useNavigate()
  const client = useQueryClient()
  const [property, setProperty] = useState(task?.property_id ?? '')
  const [assigned, setAssigned] = useState(task?.assigned_to_id ?? '')
  const [due, setDue] = useState(
    task ? localHold(task.due_at, tenant.timezone) : `${todayInZone(tenant.timezone)}T18:00`,
  )
  const [status, setStatus] = useState<Task['status']>(task?.status ?? 'pending')
  const [checks, setChecks] = useState(
    Object.fromEntries(
      Object.keys(checklist).map((key) => [key, task?.[key as keyof typeof checklist] ?? false]),
    ) as Record<keyof typeof checklist, boolean>,
  )
  const [notes, setNotes] = useState(task?.notes ?? '')
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const assignees = useQuery({
    queryKey: ['housekeeping-assignees', tenant.id],
    queryFn: () => housekeepingApi.assignees(tenant.id),
  })
  return (
    <form
      className="mt-5 space-y-5 rounded-xl border bg-white p-5"
      onSubmit={async (e) => {
        e.preventDefault()
        setSaving(true)
        setError('')
        try {
          const saved = await housekeepingApi.save(
            tenant.id,
            {
              property_id: property,
              assigned_to_id: assigned || null,
              due_at: holdToIso(due, tenant.timezone),
              status,
              ...checks,
              notes,
              cancel_reason: status === 'cancelled' ? reason : '',
            },
            task?.id,
          )
          client.setQueryData(['housekeeping-task', tenant.id, saved.id], saved)
          await client.invalidateQueries({ queryKey: ['housekeeping', tenant.id] })
          await client.invalidateQueries({ queryKey: ['operations', tenant.id] })
          navigate(`/limpieza/${saved.id}`)
        } catch (failure) {
          setError(failure instanceof Error ? failure.message : 'No se pudo guardar la tarea.')
        } finally {
          setSaving(false)
        }
      }}
    >
      {task ? (
        <p>
          Cabaña: {task.property_name}.{' '}
          {task.source === 'checkout'
            ? 'La tarea automática conserva esta cabaña.'
            : 'La tarea corresponde a esta cabaña.'}
        </p>
      ) : (
        <PropertyFilter tenant={tenant.id} value={property} onChange={setProperty} />
      )}
      <p className="text-sm text-muted-foreground">
        Para una tarea nueva selecciona una cabaña activa. Todos los integrantes activos pueden
        encargarse de una limpieza.
      </p>
      <label className="block">
        Vence el día y hora
        <input
          required
          type="datetime-local"
          className="mt-2 block w-full rounded-lg border p-3"
          value={due}
          onChange={(e) => setDue(e.target.value)}
        />
      </label>
      <div>
        <label htmlFor="task-assignee">Responsable</label>
        <select
          id="task-assignee"
          className="mt-2 w-full rounded-lg border bg-white p-3"
          value={assigned}
          onChange={(e) => setAssigned(e.target.value)}
        >
          <option value="">Sin asignar</option>
          {task?.assigned_to_id &&
            !assignees.data?.some((member) => member.id === task.assigned_to_id) && (
              <option value={task.assigned_to_id}>
                {task.assigned_name || 'Integrante no disponible'} · Reasignar
              </option>
            )}
          {assignees.data?.map((member) => (
            <option key={member.id} value={member.id}>
              {member.name || 'Integrante de la empresa'}
            </option>
          ))}
        </select>
      </div>
      {assignees.error && <p role="alert">{assignees.error.message}</p>}
      <fieldset>
        <legend className="font-semibold">Checklist de limpieza</legend>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {Object.entries(checklist).map(([key, label]) => (
            <label key={key} className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={checks[key as keyof typeof checklist]}
                onChange={(e) => setChecks({ ...checks, [key]: e.target.checked })}
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>
      {task && (
        <div>
          <label htmlFor="task-status">Estado</label>
          <select
            id="task-status"
            className="mt-2 w-full rounded-lg border bg-white p-3"
            value={status}
            onChange={(e) => setStatus(e.target.value as Task['status'])}
          >
            {Object.entries(taskLabels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>
      )}
      <label className="block">
        Notas de limpieza
        <textarea
          maxLength={1000}
          className="mt-2 w-full rounded-lg border p-3"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </label>
      {status === 'cancelled' && (
        <label className="block">
          Motivo de cancelación
          <input
            required
            maxLength={1000}
            className="mt-2 w-full rounded-lg border p-3"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
      )}
      {status === 'completed' && (
        <p>
          Al guardar se cerrará la tarea y se conservará el checklist. Revisa los cuatro puntos
          antes de confirmar.
        </p>
      )}
      {status === 'cancelled' && <p>Al guardar se cancelará la tarea conservando su historial.</p>}
      {error && (
        <p role="alert" className="text-red-800">
          {error}
        </p>
      )}
      <Button
        type="submit"
        disabled={
          saving ||
          !property ||
          (status === 'completed' && !Object.values(checks).every(Boolean)) ||
          (status === 'cancelled' && !reason.trim())
        }
      >
        {saving ? 'Guardando…' : 'Guardar tarea'}
      </Button>
    </form>
  )
}

export function HousekeepingCreate() {
  return (
    <section>
      <Link to="/limpieza" className="text-primary underline">
        Volver a limpieza
      </Link>
      <h1 className="mt-4 text-3xl font-bold">Nueva limpieza</h1>
      <TaskEditor />
    </section>
  )
}

export function HousekeepingDetail() {
  const { tenant } = useTenantContext()
  const { id } = useParams()
  const result = useQuery({
    queryKey: ['housekeeping-task', tenant.id, id],
    queryFn: () => housekeepingApi.get(tenant.id, id!),
  })
  if (result.isPending) return <p role="status">Cargando tarea…</p>
  if (result.error) return <p role="alert">{result.error.message}</p>
  const task = result.data!
  const closed = ['completed', 'cancelled'].includes(task.status)
  return (
    <section>
      <Link to="/limpieza" className="text-primary underline">
        Volver a limpieza
      </Link>
      <h1 className="mt-4 break-words text-3xl font-bold">Limpieza · {task.property_name}</h1>
      <p className="mt-3">
        {taskLabels[task.status]} · {task.source === 'checkout' ? 'Creada por check-out' : 'Manual'}
      </p>
      {task.reservation_id && (
        <Link
          to={`/reservas/${task.reservation_id}`}
          className="mt-3 inline-block text-primary underline"
        >
          Ver reserva de origen
        </Link>
      )}
      {closed ? (
        <div className="mt-5 rounded-xl border bg-white p-5">
          <p>Vencimiento: {dueLabel(task.due_at, tenant.timezone)}</p>
          <p>Responsable: {task.assigned_name || 'Sin asignar'}</p>
          {Object.entries(checklist).map(([key, label]) => (
            <p key={key}>
              {label}: {task[key as keyof typeof checklist] ? 'Revisado' : 'Pendiente'}
            </p>
          ))}
          <p className="mt-3 whitespace-pre-wrap break-words">{task.notes || 'Sin notas'}</p>
          {task.cancel_reason && (
            <p className="mt-3 whitespace-pre-wrap break-words">Motivo: {task.cancel_reason}</p>
          )}
          {task.completed_at && (
            <p className="mt-3">Completada: {dueLabel(task.completed_at, tenant.timezone)}</p>
          )}
          <p className="mt-3 text-sm text-muted-foreground">
            Historial conservado. Para corregirlo, crea una tarea nueva.
          </p>
        </div>
      ) : (
        <TaskEditor key={task.updated_at} task={task} />
      )}
    </section>
  )
}
