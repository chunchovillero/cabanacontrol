import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { documentLabels, guestApi } from './api'

export function GuestList() {
  const { tenant, canEdit } = useTenantContext()
  const [input, setInput] = useState('')
  const [query, setQuery] = useState('')
  const [active, setActive] = useState('true')
  const [page, setPage] = useState(1)
  const result = useQuery({
    queryKey: ['guests', tenant.id, query, active, page],
    queryFn: () => guestApi.search(tenant.id, query, active, page),
    retry: false,
  })
  return (
    <section>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-primary">{tenant.name}</p>
          <h1 className="mt-2 text-3xl font-bold">Huéspedes</h1>
          <p className="mt-3 text-muted-foreground">
            Busca una ficha existente antes de registrar un nuevo huésped.
          </p>
        </div>
        {canEdit && (
          <Button asChild>
            <Link to="/huespedes/nuevo">Nuevo huésped</Link>
          </Button>
        )}
      </div>
      <form
        className="mt-8 flex flex-wrap items-end gap-3 rounded-xl border border-border bg-white p-4"
        onSubmit={(event) => {
          event.preventDefault()
          setQuery(input.trim())
          setPage(1)
        }}
      >
        <div className="min-w-0 flex-1">
          <label htmlFor="guest-search" className="text-sm font-medium">
            Buscar por nombre o documento completo
          </label>
          <input
            id="guest-search"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            autoComplete="off"
            maxLength={150}
            className="mt-2 w-full rounded-lg border border-border px-3 py-2"
          />
        </div>
        <div>
          <label htmlFor="guest-status" className="block text-sm font-medium">
            Estado
          </label>
          <select
            id="guest-status"
            value={active}
            onChange={(event) => {
              setActive(event.target.value)
              setPage(1)
            }}
            className="mt-2 rounded-lg border border-border px-3 py-2"
          >
            <option value="true">Activos</option>
            <option value="false">Inactivos</option>
            <option value="all">Todos</option>
          </select>
        </div>
        <Button type="submit" variant="outline">
          Buscar
        </Button>
      </form>
      {result.isPending && (
        <p role="status" className="mt-8">
          Cargando huéspedes…
        </p>
      )}
      {result.error && (
        <div role="alert" className="mt-8">
          <p>{result.error.message}</p>
          <Button
            className="mt-3"
            onClick={() => {
              void result.refetch()
            }}
          >
            Reintentar
          </Button>
        </div>
      )}
      {result.data?.count === 0 && (
        <div className="mt-8 rounded-xl border border-dashed border-border bg-white p-10 text-center">
          <h2 className="text-lg font-semibold">No hay huéspedes para mostrar</h2>
          <p className="mt-2 text-muted-foreground">
            {query
              ? 'Prueba otra búsqueda.'
              : canEdit
                ? 'Registra tu primer huésped para comenzar.'
                : 'Las fichas aparecerán cuando sean registradas.'}
          </p>
        </div>
      )}
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {result.data?.results.map((guest) => (
          <article
            key={guest.id}
            className="rounded-xl border border-border bg-white p-5 shadow-sm"
          >
            <span className="rounded-full bg-muted px-2 py-1 text-xs">
              {guest.active ? 'Activo' : 'Inactivo'}
            </span>
            <h2 className="mt-4 break-words text-xl font-semibold">
              <Link to={`/huespedes/${guest.id}`} className="hover:underline">
                {guest.first_name} {guest.last_name}
              </Link>
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">
              {documentLabels[guest.document_type]} · {guest.document_masked}
            </p>
            <Button asChild variant="outline" className="mt-5 w-full">
              <Link to={`/huespedes/${guest.id}`}>Ver ficha</Link>
            </Button>
          </article>
        ))}
      </div>
      {result.data && result.data.count > 0 && (
        <nav
          aria-label="Paginación de huéspedes"
          className="mt-8 flex flex-wrap items-center justify-between gap-4"
        >
          <span className="text-sm text-muted-foreground">
            {result.data.count} huéspedes · Página {result.data.page}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              disabled={!result.data.has_previous}
              onClick={() => setPage((value) => value - 1)}
            >
              Anterior
            </Button>
            <Button
              variant="outline"
              disabled={!result.data.has_next}
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
