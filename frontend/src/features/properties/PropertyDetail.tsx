import { lazy, Suspense, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { propertyApi, formatMoney } from './api'
import { usePropertyContext } from './PropertyAccess'
import { PhotoManager } from './PhotoManager'
import { PropertyOverview } from './PropertyOverview'
const PropertyCalendar = lazy(() =>
  import('@/features/calendar/CalendarPage').then((module) => ({ default: module.CalendarPage })),
)

export function PropertyDetail() {
  const { tenant, canEdit } = usePropertyContext()
  const { id = '' } = useParams()
  const client = useQueryClient()
  const [confirm, setConfirm] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const query = useQuery({
    queryKey: ['property', tenant.id, id],
    queryFn: () => propertyApi.get(tenant.id, id),
    retry: false,
  })
  if (query.isPending) return <p role="status">Cargando cabaña…</p>
  if (query.error || !query.data)
    return (
      <section role="alert">
        <p>{query.error?.message ?? 'Cabaña no disponible.'}</p>
        <Link to="/cabanas" className="mt-4 inline-block text-primary underline">
          Volver a cabañas
        </Link>
      </section>
    )
  const property = query.data
  const toggle = async () => {
    setPending(true)
    setError('')
    try {
      const saved = await propertyApi.update(tenant.id, id, { active: !property.active })
      client.setQueryData(['property', tenant.id, id], saved)
      await client.invalidateQueries({ queryKey: ['properties', tenant.id] })
      setConfirm(false)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo cambiar el estado.')
    } finally {
      setPending(false)
    }
  }
  return (
    <section>
      <Link to="/cabanas" className="text-sm text-primary underline">
        Volver a cabañas
      </Link>
      <div className="mt-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">
            {property.code} · {property.active ? 'Activa' : 'Inactiva'}
          </p>
          <h1 className="mt-2 text-3xl font-bold">{property.name}</h1>
        </div>
        {canEdit && (
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline">
              <Link to={`/cabanas/${id}/editar`}>Editar cabaña</Link>
            </Button>
            <Button variant="outline" onClick={() => setConfirm(true)}>
              {property.active ? 'Desactivar cabaña' : 'Reactivar cabaña'}
            </Button>
          </div>
        )}
      </div>
      {confirm && (
        <section
          role="alertdialog"
          aria-modal="false"
          aria-labelledby="state-confirm-title"
          className="mt-6 rounded-xl border border-border bg-white p-6"
        >
          <h2 id="state-confirm-title" className="font-semibold">
            {property.active ? '¿Desactivar esta cabaña?' : '¿Reactivar esta cabaña?'}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Se conservarán sus datos, fotografías y trazabilidad.
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
            <Button variant="outline" disabled={pending} onClick={() => setConfirm(false)}>
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
      <div className="mt-8 min-w-0">
        <Suspense fallback={<p role="status">Cargando calendario…</p>}>
          <PropertyCalendar key={id} propertyId={id} />
        </Suspense>
      </div>
      <PropertyOverview
        tenantId={tenant.id}
        propertyId={id}
        timezone={tenant.timezone}
        active={property.active}
      />
      <h2 className="mt-10 text-xl font-semibold">Información de la cabaña</h2>
      <dl className="mt-4 grid gap-6 rounded-xl border border-border bg-white p-6 sm:grid-cols-3">
        <div>
          <dt className="text-sm text-muted-foreground">Capacidad máxima</dt>
          <dd className="mt-2 text-xl font-semibold">{property.capacity} personas</dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">Tarifa base ({property.currency})</dt>
          <dd className="mt-2 text-xl font-semibold">
            {formatMoney(property.base_rate, property.currency)}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">Entrada / salida</dt>
          <dd className="mt-2 text-xl font-semibold">
            {property.check_in_time.slice(0, 5)} / {property.check_out_time.slice(0, 5)}
          </dd>
          <p className="mt-2 text-xs text-muted-foreground">{tenant.timezone}</p>
        </div>
      </dl>
      {(property.description || property.address) && (
        <div className="mt-6 rounded-xl border border-border bg-white p-6">
          {property.description && <p className="whitespace-pre-wrap">{property.description}</p>}
          {property.address && (
            <p className="mt-4 text-sm text-muted-foreground">{property.address}</p>
          )}
        </div>
      )}
      <PhotoManager property={property} />
    </section>
  )
}
