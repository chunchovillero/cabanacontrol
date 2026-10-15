import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import { z } from 'zod'
import { request, write } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/AuthProvider'

const attemptSchema = z.object({
  id: z.string(),
  kind: z.string(),
  code: z.string(),
  amount: z.string(),
  state: z.string(),
  expires_at: z.string(),
  quoted_at: z.string(),
  contract_revision: z.number(),
})
const stateSchema = z.object({
  enabled: z.boolean(),
  terms_version: z.string(),
  prices: z.array(
    z.object({
      code: z.string(),
      name: z.string(),
      amount: z.string(),
      currency: z.string(),
      version: z.number(),
    }),
  ),
  contract: z
    .object({
      code: z.string(),
      next_code: z.string().nullable(),
      revision: z.number(),
      period_start: z.string(),
      period_end: z.string(),
      cancel_at_end: z.boolean(),
      finalized: z.boolean(),
    })
    .nullable(),
  attempts: z.array(attemptSchema),
})
const labels: Record<string, string> = {
  quoted: 'Cotizado',
  pending: 'Pendiente',
  uncertain: 'Incierto: requiere conciliación',
  approved: 'Aprobado (simulado)',
  rejected: 'Rechazado',
  obsolete: 'Obsoleto: revisión manual',
  expired: 'Vencido',
}
const money = (value: string) =>
  new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    maximumFractionDigits: 0,
  }).format(Number(value))

export function SimulationPage() {
  const { session } = useAuth()
  if (!session) return <Navigate to="/ingresar" replace />
  if (session.active_tenant?.role !== 'owner')
    return <p role="alert">Solo el propietario puede gestionar la contratación simulada.</p>
  return (
    <SimulationContent
      key={session.active_tenant.id}
      tenantId={session.active_tenant.id}
      timezone={session.active_tenant.timezone}
    />
  )
}

function SimulationContent({ tenantId, timezone }: { tenantId: string; timezone: string }) {
  const client = useQueryClient()
  const [selected, setSelected] = useState('initial')
  const [consent, setConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [quoted, setQuoted] = useState<z.infer<typeof attemptSchema> | null>(null)
  const [key, setKey] = useState('')
  const queryKey = ['billing-simulation', tenantId]
  const query = useQuery({
    queryKey,
    queryFn: async () =>
      stateSchema.parse(
        await request('/api/v1/billing/simulation/', { headers: { 'X-Tenant-Context': tenantId } }),
      ),
    retry: false,
    refetchInterval: 30000,
  })
  const date = (value: string) =>
    new Intl.DateTimeFormat('es-CL', {
      dateStyle: 'medium',
      timeStyle: 'short',
      timeZone: timezone,
    }).format(new Date(value))
  async function act(path: string, data: unknown, callback?: (result: unknown) => void) {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await write(`/api/v1/billing/simulation/${path}`, data, 'POST', {
        'X-Tenant-Context': tenantId,
      })
      callback?.(result)
      await Promise.all([
        client.invalidateQueries({ queryKey }),
        client.invalidateQueries({ queryKey: ['billing-plan', tenantId] }),
      ])
      setNotice('Operación simulada registrada. No se ha movido dinero real.')
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo completar la simulación.')
      void client.invalidateQueries({ queryKey })
    } finally {
      setBusy(false)
    }
  }
  if (query.isPending) return <p role="status">Cargando contratación simulada…</p>
  if (query.isError)
    return (
      <div role="alert">
        No se pudo cargar la contratación.{' '}
        <Button onClick={() => void query.refetch()}>Reintentar</Button>
      </div>
    )
  const state = query.data
  const contract = state.contract
  const price = state.prices.find((item) => item.code === selected)
  const renewalPrice = state.prices.find(
    (item) => item.code === (contract?.next_code || contract?.code),
  )
  const planName = (code: string) =>
    state.prices.find((item) => item.code === code)?.name || 'Plan no disponible'
  const intent = (operation: string) =>
    act(
      'intents/',
      {
        operation,
        expected_revision: contract!.revision,
        ...(operation === 'resume' || operation === 'downgrade'
          ? {
              terms: state.terms_version,
              consent,
              code: operation === 'downgrade' ? selected : contract!.next_code || contract!.code,
            }
          : {}),
      },
      () => {
        setQuoted(null)
        setConsent(false)
      },
    )
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-3xl font-bold">Contratación simulada</h1>
      <p className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-amber-950">
        SIMULACIÓN LOCAL · Sin tarjetas, sin conexión a Mercado Pago y sin cobros reales. Todos los
        importes y resultados de esta pantalla son de prueba.
      </p>
      {!state.enabled ? (
        <p>
          La simulación no está habilitada para esta empresa. Un administrador debe preparar
          expresamente una empresa ficticia y revisar su plan y límites.
        </p>
      ) : (
        <>
          {contract && (
            <section className="rounded-xl border border-border bg-white p-5">
              <h2 className="text-xl font-bold">
                Contrato simulado{' '}
                {contract.finalized
                  ? 'finalizado'
                  : Date.parse(contract.period_end) <= Date.now()
                    ? 'vencido: revisión manual'
                    : 'vigente'}
              </h2>
              <p className="mt-3">
                Plan: {planName(contract.code)} · Periodo: {date(contract.period_start)} a{' '}
                {date(contract.period_end)} ({timezone}).
              </p>
              <p className="mt-2">
                Renovación:{' '}
                {contract.cancel_at_end || contract.finalized
                  ? 'Desactivada'
                  : 'Automática consentida (simulada)'}
              </p>
              <p className="mt-2">
                Importe de próxima renovación:{' '}
                {renewalPrice ? money(renewalPrice.amount) : 'No disponible'} CLP/mes, sin cargos
                reales.
              </p>
              {contract.next_code && (
                <p className="mt-2">
                  Bajada programada: {planName(contract.next_code)}, al aprobar la próxima
                  renovación.
                </p>
              )}
              <p className="mt-3 text-sm text-muted-foreground">
                Vencimientos e impagos conservan datos y operación para revisión manual. Las
                renovaciones de prueba se procesan con el comando administrativo, sin cobros
                externos.
              </p>
            </section>
          )}
          <section className="space-y-4 rounded-xl border border-border bg-white p-5">
            <h2 className="text-xl font-bold">Revisar plan e importe</h2>
            <label className="block" htmlFor="simulation-plan">
              Plan de prueba
            </label>
            <select
              id="simulation-plan"
              value={selected}
              disabled={busy}
              onChange={(event) => {
                setSelected(event.target.value)
                setQuoted(null)
                setConsent(false)
              }}
              className="w-full rounded-lg border border-border p-3"
            >
              {state.prices.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.name} · {money(item.amount)} CLP/mes
                </option>
              ))}
            </select>
            <p>
              Precio mensual total: {price ? money(price.amount) : 'No disponible'} CLP. Renovación
              mensual automática solo tras confirmación.
            </p>
            <p className="text-sm text-muted-foreground">
              Las subidas usan diferencia de precio por tiempo restante y conservan renovación. Las
              bajadas se aplican al renovar. Desde trial o sin periodo contratado, se inicia un mes
              completo.
            </p>
            <Button
              disabled={busy}
              onClick={() =>
                void act(
                  'quotes/',
                  { code: selected, expected_revision: contract?.revision ?? 0 },
                  (result) => {
                    setQuoted(attemptSchema.parse(result))
                    setKey(crypto.randomUUID())
                    setConsent(false)
                  },
                )
              }
            >
              Obtener cotización simulada
            </Button>
            {quoted && (
              <div className="rounded-lg bg-muted p-4">
                <h3 className="font-semibold">Cotización: {money(quoted.amount)} CLP</h3>
                <p className="mt-2 text-sm">
                  {quoted.kind === 'upgrade'
                    ? 'Diferencia proporcional por subida'
                    : 'Mes completo'}{' '}
                  · Vence {date(quoted.expires_at)}.
                </p>
                <p className="mt-2 text-sm">
                  Al renovar: {price ? money(price.amount) : 'No disponible'} CLP/mes. Condiciones{' '}
                  {state.terms_version}.
                </p>
                <p className="mt-2 text-sm">
                  Cada mes conserva el anclaje UTC original; el día se ajusta al fin de mes si no
                  existe. Las fechas se muestran en {timezone}.
                </p>
              </div>
            )}
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={consent}
                disabled={busy}
                onChange={(event) => setConsent(event.target.checked)}
                className="mt-1"
              />
              <span>
                Acepto expresamente el importe revisado, las condiciones {state.terms_version} y la
                renovación mensual simulada. Entiendo que cancelar detiene la próxima renovación al
                final del periodo, sin reembolsos automáticos.
              </span>
            </label>
            {quoted && (
              <Button
                disabled={busy || !consent}
                onClick={() =>
                  void act(
                    `attempts/${quoted.id}/accept/`,
                    { key, terms: state.terms_version, consent },
                    () => setQuoted(null),
                  )
                }
              >
                Confirmar contratación simulada
              </Button>
            )}
            {contract && !contract.finalized && (
              <div className="flex flex-wrap gap-3">
                <Button
                  disabled={busy || !consent || contract.cancel_at_end}
                  variant="outline"
                  onClick={() => void intent('downgrade')}
                >
                  Programar bajada al plan seleccionado
                </Button>
                <Button
                  disabled={busy}
                  variant="outline"
                  onClick={() => void intent('clear_change')}
                >
                  Retirar cambio programado
                </Button>
                {contract.cancel_at_end ? (
                  <Button
                    disabled={busy || !consent}
                    variant="outline"
                    onClick={() => void intent('resume')}
                  >
                    Reactivar renovación con consentimiento
                  </Button>
                ) : (
                  <Button disabled={busy} variant="outline" onClick={() => void intent('cancel')}>
                    Cancelar al final del periodo
                  </Button>
                )}
              </div>
            )}
          </section>
          <section>
            <h2 className="text-xl font-bold">Intentos de simulación recientes</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Un resultado pendiente o incierto requiere conciliación antes de abrir otro intento.
              Aprobar aquí simula un resultado interno; no acredita un pago real.
            </p>
            <div className="mt-4 space-y-3">
              {state.attempts.map((attempt) => (
                <article key={attempt.id} className="rounded-xl border border-border bg-white p-4">
                  <p className="font-semibold">
                    {planName(attempt.code)} · {money(attempt.amount)} CLP ·{' '}
                    {labels[attempt.state] ?? attempt.state}
                  </p>
                  <p className="mt-1 break-all text-xs text-muted-foreground">
                    Referencia ficticia: {attempt.id}
                  </p>
                  {['pending', 'uncertain'].includes(attempt.state) && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {(
                        [
                          ['approved', 'Aprobado'],
                          ['rejected', 'Rechazado'],
                          ['pending', 'Pendiente'],
                          ['uncertain', 'Incierto'],
                        ] as const
                      ).map(([value, label]) => (
                        <Button
                          key={value}
                          disabled={busy}
                          variant="outline"
                          onClick={() =>
                            void act(`attempts/${attempt.id}/result/`, {
                              event_id: crypto.randomUUID(),
                              result: value,
                            })
                          }
                        >
                          Simular {label.toLowerCase()}
                        </Button>
                      ))}
                    </div>
                  )}
                </article>
              ))}
            </div>
          </section>
        </>
      )}
      {error && (
        <p role="alert" className="text-red-800">
          {error}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
    </div>
  )
}
