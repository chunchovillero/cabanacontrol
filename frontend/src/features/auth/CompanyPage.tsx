import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, Navigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { api, type Session } from '@/lib/api'
import { useAuth } from './AuthProvider'

const roleLabel = {
  owner: 'Propietario',
  manager: 'Administrador',
  staff: 'Colaborador',
}

export function CompanyPage() {
  const { session } = useAuth()
  const queryClient = useQueryClient()
  const [pending, setPending] = useState<string | null>(null)
  const [error, setError] = useState('')
  const tenants = useQuery({
    queryKey: ['tenants', session?.id],
    queryFn: api.tenants,
    enabled: !!session,
    retry: false,
  })
  if (!session) return <Navigate to="/ingresar" replace />
  const select = async (id: string) => {
    setPending(id)
    setError('')
    try {
      const selected = await api.selectTenant(id)
      queryClient.removeQueries({
        predicate: (query) => query.queryKey[0] !== 'session' && query.queryKey[0] !== 'tenants',
      })
      queryClient.setQueryData<Session>(['session'], {
        ...session,
        active_tenant: selected,
      })
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo seleccionar la empresa.')
      void queryClient.invalidateQueries({ queryKey: ['session'] })
      void queryClient.invalidateQueries({ queryKey: ['tenants'] })
    } finally {
      setPending(null)
    }
  }
  return (
    <div className="mx-auto max-w-4xl">
      <p className="text-sm font-medium text-primary">
        Hola{session.name ? `, ${session.name}` : ''}
      </p>
      <h1 className="mt-3 text-3xl font-bold tracking-tight">Tus empresas</h1>
      <p className="mt-3 text-muted-foreground">
        Selecciona la empresa con la que quieres trabajar.
      </p>
      {tenants.isPending && (
        <p role="status" className="mt-6">
          Cargando empresas…
        </p>
      )}
      {tenants.error && (
        <div role="alert" className="mt-6">
          <p>{tenants.error.message}</p>
          <Button
            className="mt-3"
            onClick={() => {
              void tenants.refetch()
            }}
          >
            Reintentar
          </Button>
        </div>
      )}
      {error && (
        <p role="alert" className="mt-5 text-red-800">
          {error}
        </p>
      )}
      {tenants.data?.length === 0 && (
        <p className="mt-8 rounded-xl border border-border bg-white p-6">
          Tu cuenta todavía no tiene empresas asignadas. Contacta al administrador.
        </p>
      )}
      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        {tenants.data?.map((tenant) => (
          <article key={tenant.id} className="rounded-xl border border-border bg-white p-6">
            <h2 className="text-xl font-semibold">{tenant.name}</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              {roleLabel[tenant.role]} · {tenant.currency}
            </p>
            <Button
              className="mt-5"
              variant={session.active_tenant?.id === tenant.id ? 'outline' : 'default'}
              disabled={pending !== null || session.active_tenant?.id === tenant.id}
              onClick={() => {
                void select(tenant.id)
              }}
            >
              {pending === tenant.id
                ? 'Seleccionando…'
                : session.active_tenant?.id === tenant.id
                  ? 'Empresa activa'
                  : `Seleccionar ${tenant.name}`}
            </Button>
          </article>
        ))}
      </div>
      {session.active_tenant && (
        <section
          aria-label="Empresa activa"
          className="mt-8 rounded-xl bg-primary p-6 text-primary-foreground"
        >
          <h2 className="text-xl font-semibold">{session.active_tenant.name}</h2>
          <p className="mt-2">Empresa activa · {roleLabel[session.active_tenant.role]}</p>
          <p className="mt-3 text-sm">Administra los alojamientos de esta empresa.</p>
          <Button asChild variant="outline" className="mt-4 text-foreground">
            <Link to="/cabanas">Ver cabañas</Link>
          </Button>
        </section>
      )}
    </div>
  )
}
