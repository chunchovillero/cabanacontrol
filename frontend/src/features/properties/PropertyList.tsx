import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { publicUrl } from '@/lib/api'
import { propertyApi, formatMoney } from './api'
import { usePropertyContext } from './PropertyAccess'

export function PropertyList() {
  const { tenant, canEdit } = usePropertyContext()
  const [draftSearch, setDraftSearch] = useState('')
  const [search, setSearch] = useState('')
  const [active, setActive] = useState('true')
  const [page, setPage] = useState(1)
  const query = useQuery({
    queryKey: ['properties', tenant.id, search, active, page],
    queryFn: () => propertyApi.list(tenant.id, search, active, page),
    retry: false,
  })
  return (
    <section>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-primary">{tenant.name}</p>
          <h1 className="mt-2 text-3xl font-bold">Cabañas</h1>
          <p className="mt-3 text-muted-foreground">
            Administra tus alojamientos, capacidad y tarifa base.
          </p>
        </div>
        {canEdit && (
          <Button asChild>
            <Link to="/cabanas/nueva">Nueva cabaña</Link>
          </Button>
        )}
      </div>
      <form
        className="mt-8 flex flex-wrap items-end gap-3 rounded-xl border border-border bg-white p-4"
        onSubmit={(event) => {
          event.preventDefault()
          setSearch(draftSearch.trim())
          setPage(1)
        }}
      >
        <div className="min-w-0 flex-1">
          <label htmlFor="property-search" className="text-sm font-medium">
            Buscar por nombre o código
          </label>
          <input
            id="property-search"
            value={draftSearch}
            onChange={(event) => setDraftSearch(event.target.value)}
            className="mt-2 w-full rounded-lg border border-border px-3 py-2"
          />
        </div>
        <div>
          <label htmlFor="property-status" className="block text-sm font-medium">
            Estado
          </label>
          <select
            id="property-status"
            value={active}
            onChange={(event) => {
              setActive(event.target.value)
              setPage(1)
            }}
            className="mt-2 rounded-lg border border-border px-3 py-2"
          >
            <option value="true">Activas</option>
            <option value="false">Inactivas</option>
            <option value="all">Todas</option>
          </select>
        </div>
        <Button type="submit" variant="outline">
          Buscar
        </Button>
      </form>
      {query.isPending && (
        <p role="status" className="mt-8">
          Cargando cabañas…
        </p>
      )}
      {query.error && (
        <div role="alert" className="mt-8">
          <p>{query.error.message}</p>
          <Button
            className="mt-3"
            onClick={() => {
              void query.refetch()
            }}
          >
            Reintentar
          </Button>
        </div>
      )}
      {query.data?.count === 0 && (
        <div className="mt-8 rounded-xl border border-dashed border-border bg-white p-10 text-center">
          <h2 className="text-lg font-semibold">No hay cabañas para mostrar</h2>
          <p className="mt-2 text-muted-foreground">
            {search
              ? 'Prueba otra búsqueda.'
              : canEdit
                ? 'Registra tu primera cabaña para comenzar.'
                : 'Los alojamientos aparecerán cuando sean registrados.'}
          </p>
        </div>
      )}
      <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {query.data?.results.map((property) => (
          <article
            key={property.id}
            className="overflow-hidden rounded-xl border border-border bg-white shadow-sm"
          >
            {property.photos[0] ? (
              <img
                src={publicUrl(property.photos[0].url)}
                alt={property.photos[0].alt}
                className="h-44 w-full object-cover"
                loading="lazy"
              />
            ) : (
              <div className="flex h-32 items-center justify-center bg-muted text-sm text-muted-foreground">
                Sin fotografías
              </div>
            )}
            <div className="p-5">
              <div className="flex justify-between gap-3">
                <span className="text-xs font-semibold text-muted-foreground">{property.code}</span>
                <span className="rounded-full bg-muted px-2 py-1 text-xs">
                  {property.active ? 'Activa' : 'Inactiva'}
                </span>
              </div>
              <h2 className="mt-3 text-xl font-semibold">
                <Link to={`/cabanas/${property.id}`} className="hover:underline">
                  {property.name}
                </Link>
              </h2>
              <p className="mt-3 text-sm text-muted-foreground">
                Capacidad: {property.capacity} personas
              </p>
              <p className="mt-2 font-semibold">
                {formatMoney(property.base_rate, property.currency)}{' '}
                <span className="text-xs font-normal text-muted-foreground">tarifa base</span>
              </p>
              <Button asChild variant="outline" className="mt-5 w-full">
                <Link to={`/cabanas/${property.id}`}>Ver cabaña</Link>
              </Button>
            </div>
          </article>
        ))}
      </div>
      {query.data && query.data.count > 0 && (
        <nav
          aria-label="Paginación de cabañas"
          className="mt-8 flex flex-wrap items-center justify-between gap-4"
        >
          <span className="text-sm text-muted-foreground">
            {query.data.count} cabañas · Página {page}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              disabled={!query.data.previous}
              onClick={() => setPage((value) => value - 1)}
            >
              Anterior
            </Button>
            <Button
              variant="outline"
              disabled={!query.data.next}
              onClick={() => setPage((value) => value + 1)}
            >
              Siguiente
            </Button>
          </div>
        </nav>
      )}
    </section>
  )
}
