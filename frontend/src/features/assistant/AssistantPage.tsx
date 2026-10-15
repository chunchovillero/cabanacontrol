import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { assistantApi, type Answer } from './api'
import { formatMoney } from '@/features/properties/api'
import { formatDate } from '@/features/reservations/dates'

export function PrivacyNotice() {
  return (
    <p className="rounded-lg bg-muted p-4 text-sm">
      OpenAI recibirá el texto que revises. Retira nombres, RUT, contactos, notas privadas y
      secretos. Las máscaras son una ayuda y requieren revisión humana. No se promete retención cero
      del proveedor.
    </p>
  )
}

export function AnswerCards({ answer }: { answer: Answer }) {
  const { tenant } = useTenantContext()
  const [prepared, setPrepared] = useState('')
  const [prepareError, setPrepareError] = useState('')
  const [preparing, setPreparing] = useState(false)
  async function prepare(id: string, data: Answer['results'][number]['data']) {
    if (!data.check_in || !data.check_out || !data.guests) return
    setPreparing(true)
    setPrepareError('')
    try {
      const response = await assistantApi.prepare(tenant.id, {
        property_id: id,
        check_in: data.check_in,
        check_out: data.check_out,
        guests: data.guests,
      })
      setPrepared(response.results[0]?.data.message ?? '')
    } catch (failure) {
      setPrepareError(failure instanceof Error ? failure.message : 'No se pudo preparar.')
    } finally {
      setPreparing(false)
    }
  }
  return (
    <div className="space-y-4">
      {answer.results.map((result, index) => (
        <article key={index} className="rounded-xl border bg-white p-5">
          {result.data.verified_at && (
            <p className="mb-2 text-xs text-muted-foreground">
              Verificado:{' '}
              {new Date(result.data.verified_at).toLocaleString('es-CL', {
                timeZone: tenant.timezone,
              })}
            </p>
          )}
          {result.data.messages?.map((message) => (
            <p key={message}>{message}</p>
          ))}
          {result.data.date && <p>Fecha: {formatDate(result.data.date)}</p>}
          {result.data.check_in && (
            <p>
              {formatDate(result.data.check_in)} →{' '}
              {result.data.check_out && formatDate(result.data.check_out)}
            </p>
          )}
          {result.data.start_date && (
            <p>
              {result.data.start_date} → {result.data.end_date} (fin exclusivo)
            </p>
          )}
          {result.data.price_notice && <p>{result.data.price_notice}</p>}
          {result.data.message && (
            <textarea
              aria-label="Respuesta preparada editable"
              className="mt-2 w-full rounded border p-3"
              defaultValue={result.data.message}
              rows={4}
            />
          )}
          {result.data.total !== undefined && (
            <p>
              {result.data.total} resultados · Página {result.data.page}
            </p>
          )}
          <ul className="mt-3 space-y-2">
            {result.data.items?.map((item, i) => (
              <li key={item.id ?? i}>
                {item.name ?? item.property} {item.guest}
                {item.capacity !== undefined && ` · ${item.capacity} personas`}
                {item.amount && item.currency && ` · ${formatMoney(item.amount, item.currency)}`}
                {item.url && (
                  <Link className="ml-3 text-primary underline" to={item.url}>
                    Ver ficha
                  </Link>
                )}
                {result.tool === 'search_available_properties' && item.id && (
                  <Button
                    type="button"
                    variant="outline"
                    disabled={preparing}
                    onClick={() => {
                      void prepare(item.id!, result.data)
                    }}
                  >
                    Preparar respuesta para esta cabaña
                  </Button>
                )}
              </li>
            ))}
          </ul>
          {result.data.has_more && (
            <p className="mt-3">Hay más resultados. Solicita la siguiente página.</p>
          )}
          {result.data.total === 0 && <p>No hay resultados para los filtros indicados.</p>}
        </article>
      ))}
      {prepared && (
        <label className="block">
          Respuesta para WhatsApp editable
          <textarea
            className="mt-2 w-full rounded border p-3"
            rows={4}
            value={prepared}
            onChange={(event) => setPrepared(event.target.value)}
          />
        </label>
      )}
      {prepareError && <p role="alert">{prepareError}</p>}
    </div>
  )
}

export function AssistantPage() {
  const { tenant } = useTenantContext()
  const [text, setText] = useState('')
  const [reviewed, setReviewed] = useState(false)
  const [answers, setAnswers] = useState<Answer[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const capabilities = useQuery({
    queryKey: ['assistant-capabilities', tenant.id],
    queryFn: () => assistantApi.capabilities(tenant.id),
    retry: false,
  })
  async function send() {
    setBusy(true)
    setError('')
    try {
      const answer = await assistantApi.message(tenant.id, text, answers.at(-1)?.context ?? '')
      setAnswers((previous) => [...previous.slice(-9), answer])
      setText('')
      setReviewed(false)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo analizar.')
    } finally {
      setBusy(false)
    }
  }
  async function toggle() {
    setError('')
    try {
      await assistantApi.configure(tenant.id, { enabled: !capabilities.data?.enabled })
      await capabilities.refetch()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo configurar.')
    }
  }
  async function saveLimits(form: HTMLFormElement) {
    const data = new FormData(form)
    setError('')
    try {
      await assistantApi.configure(tenant.id, {
        daily_requests: Number(data.get('daily_requests')),
        daily_tokens: Number(data.get('daily_tokens')),
        daily_audio_seconds: Number(data.get('daily_audio_seconds')),
        daily_budget_usd: String(data.get('daily_budget_usd')),
      })
      await capabilities.refetch()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudieron guardar los límites.')
    }
  }
  return (
    <section className="space-y-5">
      <h1 className="text-3xl font-bold">Asistente</h1>
      <p>
        Consulta disponibilidad, llegadas, cobros y saldos actuales. Los precios requieren
        confirmación humana.
      </p>
      <PrivacyNotice />
      {capabilities.isPending && <p role="status">Comprobando configuración…</p>}
      {capabilities.error && <p role="alert">{capabilities.error.message}</p>}
      {capabilities.data && (
        <div className="rounded-xl border p-4">
          {capabilities.data.simulated && (
            <p className="font-semibold">
              Proveedor simulado · Datos ficticios · Sin llamadas a OpenAI
            </p>
          )}
          <p>
            {capabilities.data.ready
              ? 'Proveedor configurado.'
              : 'Proveedor sin configurar: usa las herramientas manuales.'}{' '}
            {capabilities.data.enabled
              ? 'IA habilitada para esta empresa.'
              : 'IA desactivada para esta empresa.'}
          </p>
          <p>
            Límite diario: {capabilities.data.settings.daily_requests} consultas; presupuesto
            estimado USD {capabilities.data.settings.daily_budget_usd}.
          </p>
          {tenant.role !== 'staff' && (
            <Button
              variant="outline"
              onClick={() => {
                void toggle()
              }}
            >
              {capabilities.data.enabled ? 'Desactivar IA' : 'Habilitar IA para esta empresa'}
            </Button>
          )}
          {tenant.role !== 'staff' && (
            <Button
              variant="outline"
              onClick={() => {
                void assistantApi
                  .configure(tenant.id, {
                    voice_enabled: !capabilities.data?.settings.voice_enabled,
                  })
                  .then(() => capabilities.refetch())
                  .catch((failure) =>
                    setError(
                      failure instanceof Error ? failure.message : 'No se pudo configurar voz.',
                    ),
                  )
              }}
            >
              {capabilities.data.settings.voice_enabled
                ? 'Desactivar dictado'
                : 'Habilitar dictado'}
            </Button>
          )}
        </div>
      )}
      <div className="flex flex-wrap gap-4 text-primary underline">
        <Link to="/reservas/disponibilidad">Buscar disponibilidad</Link>
        <Link to="/consultas">Bandeja de consultas</Link>
        <Link to="/reportes">Reportes</Link>
      </div>
      {answers.map((answer, index) => (
        <AnswerCards key={index} answer={answer} />
      ))}
      <form
        onSubmit={(event) => {
          event.preventDefault()
          void send()
        }}
        className="space-y-4 rounded-xl border bg-white p-5"
      >
        <label className="block">
          Texto revisado para analizar
          <textarea
            maxLength={4000}
            rows={4}
            className="mt-2 w-full rounded border p-3"
            value={text}
            onChange={(event) => {
              setText(event.target.value)
              setReviewed(false)
            }}
          />
        </label>
        <label className="flex items-start gap-3">
          <input
            type="checkbox"
            checked={reviewed}
            onChange={(event) => setReviewed(event.target.checked)}
          />
          Revisé el texto y autorizaré su envío a OpenAI.
        </label>
        <Button
          disabled={
            busy ||
            !reviewed ||
            !text.trim() ||
            !capabilities.data?.ready ||
            !capabilities.data.enabled
          }
        >
          {busy ? 'Analizando…' : 'Consultar asistente'}
        </Button>
        <Button type="button" variant="outline" onClick={() => setAnswers([])}>
          Limpiar conversación
        </Button>
      </form>
      {tenant.role !== 'staff' && capabilities.data && (
        <details className="mt-4">
          <summary>Límites y presupuesto de esta empresa</summary>
          <form
            className="mt-4 grid gap-4 sm:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault()
              void saveLimits(event.currentTarget)
            }}
          >
            <label>
              Consultas por día
              <input
                className="mt-2 w-full rounded border p-3"
                type="number"
                name="daily_requests"
                min="1"
                max="1000"
                required
                defaultValue={capabilities.data.settings.daily_requests}
              />
            </label>
            <label>
              Tokens por día
              <input
                className="mt-2 w-full rounded border p-3"
                type="number"
                name="daily_tokens"
                min="1200"
                max="10000000"
                required
                defaultValue={capabilities.data.settings.daily_tokens}
              />
            </label>
            <label>
              Segundos de dictado por día
              <input
                className="mt-2 w-full rounded border p-3"
                type="number"
                name="daily_audio_seconds"
                min="1"
                max="36000"
                required
                defaultValue={capabilities.data.settings.daily_audio_seconds}
              />
            </label>
            <label>
              Presupuesto estimado diario (USD)
              <input
                className="mt-2 w-full rounded border p-3"
                name="daily_budget_usd"
                inputMode="decimal"
                required
                defaultValue={capabilities.data.settings.daily_budget_usd}
              />
            </label>
            <p className="text-sm sm:col-span-2">
              Se reserva cuota antes de consultar. Los fallos con consumo incierto conservan la
              reserva. Este cálculo no sustituye la factura ni los límites de la cuenta OpenAI.
            </p>
            <Button>Guardar límites</Button>
          </form>
        </details>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  )
}
