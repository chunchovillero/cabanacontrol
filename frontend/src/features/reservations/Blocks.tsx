import { useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { propertyApi } from '@/features/properties/api'
import { blockApi, blockLabels, type Block } from './api'
import { formatDate } from './dates'
import { inputClass } from './ReservationForm'
import { blockFormSchema } from './validation'

export function BlockList() {
  const { tenant, canEdit } = useTenantContext()
  const client = useQueryClient()
  const [page, setPage] = useState(1)
  const [active, setActive] = useState('true')
  const [confirmation, setConfirmation] = useState<Block | null>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const result = useQuery({
    queryKey: ['blocks', tenant.id, page, active],
    queryFn: () => blockApi.list(tenant.id, page, active),
  })
  async function release() {
    setSaving(true)
    setError('')
    try {
      await blockApi.save(tenant.id, { active: false }, confirmation!.id)
      await client.invalidateQueries({ queryKey: ['blocks', tenant.id] })
      await client.invalidateQueries({ queryKey: ['block', tenant.id, confirmation!.id] })
      await client.invalidateQueries({ queryKey: ['availability', tenant.id] })
      setConfirmation(null)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo liberar el bloqueo.')
    } finally {
      setSaving(false)
    }
  }
  return (
    <section>
      <Link to="/reservas" className="text-primary underline">
        Volver a reservas
      </Link>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-bold">Bloqueos de fechas</h1>
        {canEdit && (
          <Button asChild>
            <Link to="/reservas/bloqueos/nuevo">Nuevo bloqueo</Link>
          </Button>
        )}
      </div>
      <p className="mt-3 text-muted-foreground">
        Mantenimiento, uso del propietario u otras fechas fuera de venta.
      </p>
      <label className="mt-6 block text-sm font-medium">
        Estado del bloqueo
        <select
          className="ml-3 rounded-lg border bg-white p-3"
          value={active}
          onChange={(e) => {
            setActive(e.target.value)
            setPage(1)
          }}
        >
          <option value="true">Activos</option>
          <option value="false">Liberados</option>
          <option value="all">Todos</option>
        </select>
      </label>
      {result.isPending && (
        <p role="status" className="mt-6">
          Cargando bloqueos…
        </p>
      )}
      {result.error && (
        <p role="alert" className="mt-6">
          {result.error.message}
        </p>
      )}
      {result.data?.count === 0 && <p className="mt-8">No hay bloqueos para mostrar.</p>}
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {result.data?.results.map((item) => (
          <article key={item.id} className="rounded-xl border bg-white p-5">
            <h2 className="text-xl font-semibold">{item.property_name}</h2>
            <p className="mt-3">
              {formatDate(item.start_date)} → {formatDate(item.end_date)}
            </p>
            <p className="mt-2 text-sm">
              {blockLabels[item.reason]} · {item.active ? 'Activo' : 'Liberado'}
            </p>
            <p className="mt-3 whitespace-pre-wrap break-words text-sm text-muted-foreground">
              {item.notes}
            </p>
            {canEdit && (
              <div className="mt-4 flex flex-wrap gap-3">
                <Button variant="outline" asChild>
                  <Link to={`/reservas/bloqueos/${item.id}/editar`}>Editar bloqueo</Link>
                </Button>
                {item.active && (
                  <Button
                    variant="outline"
                    onClick={() => {
                      setConfirmation(item)
                      setError('')
                    }}
                  >
                    Liberar fechas
                  </Button>
                )}
              </div>
            )}
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
          <span>Página {page}</span>
          <Button variant="outline" disabled={!result.data.next} onClick={() => setPage(page + 1)}>
            Siguiente
          </Button>
        </div>
      )}
      {confirmation && (
        <div
          role="dialog"
          aria-label="Liberar bloqueo"
          className="mt-6 rounded-xl border bg-white p-6"
        >
          <p>
            Liberar las fechas de {confirmation.property_name}. Se conservará el historial del
            bloqueo.
          </p>
          {error && (
            <p role="alert" className="mt-3 text-red-800">
              {error}
            </p>
          )}
          <div className="mt-4 flex flex-wrap gap-3">
            <Button
              disabled={saving}
              onClick={() => {
                void release()
              }}
            >
              Confirmar liberación
            </Button>
            <Button disabled={saving} variant="outline" onClick={() => setConfirmation(null)}>
              Volver sin cambiar
            </Button>
          </div>
        </div>
      )}
    </section>
  )
}

function BlockEditor({ item }: { item?: Block }) {
  const { tenant } = useTenantContext()
  const navigate = useNavigate()
  const client = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [error, setError] = useState('')
  const props = useQuery({
    queryKey: ['properties', tenant.id, search, page],
    queryFn: () => propertyApi.list(tenant.id, search, 'true', page),
  })
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof blockFormSchema>>({
    resolver: zodResolver(blockFormSchema),
    defaultValues: {
      property_id: item?.property_id ?? '',
      start_date: item?.start_date ?? '',
      end_date: item?.end_date ?? '',
      reason: item?.reason ?? 'maintenance',
      notes: item?.notes ?? '',
    },
  })
  const submit = handleSubmit(async (values) => {
    setError('')
    try {
      await blockApi.save(tenant.id, { ...values, active: true }, item?.id)
      await client.invalidateQueries({ queryKey: ['blocks', tenant.id] })
      await client.invalidateQueries({ queryKey: ['block', tenant.id, item?.id] })
      await client.invalidateQueries({ queryKey: ['availability', tenant.id] })
      navigate('/reservas/bloqueos')
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo guardar el bloqueo.')
    }
  })
  return (
    <form
      noValidate
      className="mt-7 space-y-5 rounded-xl border bg-white p-5 sm:p-7"
      onSubmit={(e) => {
        void submit(e)
      }}
    >
      <label className="block text-sm font-medium">
        Buscar cabaña
        <input
          className={inputClass}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
          maxLength={150}
        />
      </label>
      <div>
        <label htmlFor="block-property" className="block text-sm font-medium">
          Cabaña
        </label>
        <select id="block-property" className={inputClass} {...register('property_id')}>
          <option value="">Seleccionar cabaña</option>
          {item && !props.data?.results.some((p) => p.id === item.property_id) && (
            <option value={item.property_id}>{item.property_name}</option>
          )}
          {props.data?.results.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>
      {props.error && <p role="alert">{props.error.message}</p>}
      <div className="flex flex-wrap gap-3">
        <Button
          type="button"
          variant="outline"
          disabled={!props.data?.previous}
          onClick={() => setPage(page - 1)}
        >
          Cabañas anteriores
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={!props.data?.next}
          onClick={() => setPage(page + 1)}
        >
          Más cabañas
        </Button>
      </div>
      <div className="grid gap-5 sm:grid-cols-2">
        <label className="text-sm font-medium">
          Inicio
          <input type="date" className={inputClass} {...register('start_date')} />
        </label>
        <label className="text-sm font-medium">
          Fin (exclusivo)
          <input type="date" className={inputClass} {...register('end_date')} />
        </label>
      </div>
      <div>
        <label htmlFor="block-reason" className="block text-sm font-medium">
          Motivo
        </label>
        <select id="block-reason" className={inputClass} {...register('reason')}>
          {Object.entries(blockLabels).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <label className="block text-sm font-medium">
        Notas del bloqueo (opcional)
        <textarea className={inputClass} maxLength={2000} rows={3} {...register('notes')} />
      </label>
      {item && !item.active && (
        <p>Guardar reactivará este bloqueo y comprobará la disponibilidad.</p>
      )}
      {Object.entries(errors).map(([key, value]) => (
        <p role="alert" key={key} className="text-red-800">
          {value?.message}
        </p>
      ))}
      {error && (
        <p role="alert" className="text-red-800">
          {error}
        </p>
      )}
      <div className="flex flex-wrap gap-4">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Guardando…' : 'Guardar bloqueo'}
        </Button>
        <Button variant="outline" asChild>
          <Link to="/reservas/bloqueos">Volver</Link>
        </Button>
      </div>
    </form>
  )
}

export function BlockForm() {
  const { id } = useParams()
  const { tenant, canEdit } = useTenantContext()
  const result = useQuery({
    queryKey: ['block', tenant.id, id],
    queryFn: () => blockApi.get(tenant.id, id!),
    enabled: Boolean(id && canEdit),
  })
  if (!canEdit) return <Navigate to="/reservas/bloqueos" replace />
  if (id && result.isPending) return <p role="status">Cargando bloqueo…</p>
  if (id && result.error) return <p role="alert">{result.error.message}</p>
  return (
    <section>
      <h1 className="text-3xl font-bold">{id ? 'Editar bloqueo' : 'Nuevo bloqueo'}</h1>
      <BlockEditor key={id ?? 'new'} item={result.data} />
    </section>
  )
}
