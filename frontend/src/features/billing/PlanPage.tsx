import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { request } from '@/lib/api'
import { referenceMonthlyPrice } from '@/lib/planPresentation'
import { useAuth } from '@/features/auth/AuthProvider'

const planSchema = z.object({
  code: z.string(),
  version: z.number(),
  name: z.string(),
  property_limit: z.number(),
  member_limit: z.number(),
})
const responseSchema = z.object({
  subscription: z.object({
    status: z.enum(['unassigned', 'manual', 'trial', 'expired']),
    enforced: z.boolean(),
    plan: planSchema.nullable(),
    usage: z.object({ properties: z.number(), members: z.number() }),
    trial_ends_at: z.string().nullable(),
    over_capacity: z.boolean(),
  }),
  catalog: z.array(planSchema),
})

export function PlanPage() {
  const { session } = useAuth()
  const tenant = session?.active_tenant
  if (tenant?.role !== 'owner')
    return <p role="alert">Solo el propietario puede consultar el plan de esta empresa.</p>
  return <PlanContent key={tenant.id} tenantId={tenant.id} timezone={tenant.timezone} />
}

function PlanContent({ tenantId, timezone }: { tenantId: string; timezone: string }) {
  const query = useQuery({
    queryKey: ['billing-plan', tenantId],
    queryFn: async () =>
      responseSchema.parse(
        await request('/api/v1/billing/plan/', { headers: { 'X-Tenant-Context': tenantId } }),
      ),
    retry: false,
    refetchInterval: 60000,
  })
  if (query.isPending) return <p role="status">Cargando plan y uso…</p>
  if (query.isError)
    return (
      <div role="alert">
        No pudimos cargar el plan. <Button onClick={() => void query.refetch()}>Reintentar</Button>
      </div>
    )
  const { subscription: sub, catalog } = query.data
  const labels = {
    unassigned: 'Sin asignación comercial',
    manual: 'Asignación manual',
    trial: 'Prueba gratuita',
    expired: 'Prueba vencida',
  }
  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-3xl font-bold">Plan y uso</h1>
      <Link to="/contratacion-simulada" className="mt-4 inline-block text-primary underline">
        Revisar contratación simulada
      </Link>
      <p className="mt-3 text-muted-foreground">
        Gestión comercial local. Precios de referencia para simulación; la contratación está en
        preparación y esta pantalla no realiza cobros.
      </p>
      <section className="mt-6 rounded-2xl border border-border bg-white p-6">
        <h2 className="text-xl font-bold">{sub.plan?.name || 'Empresa sin plan asignado'}</h2>
        <p className="mt-3">Estado: {labels[sub.status]}</p>
        <p className="mt-2">
          Límites: {sub.enforced ? 'Habilitados' : 'Pendientes de habilitación manual'}
        </p>
        <dl className="mt-5 grid gap-4 sm:grid-cols-2">
          <div>
            <dt>Cabañas activas</dt>
            <dd className="text-2xl font-bold">
              {sub.usage.properties} / {sub.plan?.property_limit ?? 'Sin asignar'}
            </dd>
          </div>
          <div>
            <dt>Usuarios activos</dt>
            <dd className="text-2xl font-bold">
              {sub.usage.members} / {sub.plan?.member_limit ?? 'Sin asignar'}
            </dd>
          </div>
        </dl>
        <p className="mt-3 text-sm text-muted-foreground">
          El propietario ocupa una plaza. Las invitaciones pendientes no reservan plazas.
        </p>
        {sub.trial_ends_at && sub.plan?.code === 'trial' && (
          <p className="mt-3">
            Fin de prueba:{' '}
            {new Intl.DateTimeFormat('es-CL', {
              dateStyle: 'medium',
              timeStyle: 'short',
              timeZone: timezone,
            }).format(new Date(sub.trial_ends_at))}{' '}
            ({timezone}).
          </p>
        )}
        {sub.status === 'expired' && (
          <p role="alert" className="mt-4">
            Tu prueba terminó. Se conserva la capacidad de 1 cabaña y 1 usuario hasta revisión
            manual, sin suspensión automática ni cobros.
          </p>
        )}
        {sub.over_capacity && (
          <p role="alert" className="mt-4">
            El uso supera la capacidad asignada. Si los límites están habilitados, no podrás
            aumentar el recurso excedido; puedes seguir trabajando con los datos existentes.
          </p>
        )}
        {sub.status === 'unassigned' && (
          <p className="mt-4">
            El administrador debe revisar el uso y asignar un plan antes de habilitar sus límites.
          </p>
        )}
      </section>
      <h2 className="mt-8 text-xl font-bold">Planes por capacidad</h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        {catalog.map((plan) => (
          <section key={plan.code} className="rounded-xl border border-border bg-white p-5">
            <h3 className="font-bold">{plan.name}</h3>
            <p className="mt-3">{plan.property_limit} cabañas activas</p>
            <p>{plan.member_limit} usuarios activos</p>
            <p className="mt-3 text-sm text-muted-foreground">{referenceMonthlyPrice(plan.code)}</p>
          </section>
        ))}
      </div>
      <p className="mt-5 text-sm text-muted-foreground">
        Las mensualidades del SaaS son independientes de los abonos de huéspedes. IA y WhatsApp
        mantienen sus propias autorizaciones y cuotas.
      </p>
    </div>
  )
}
