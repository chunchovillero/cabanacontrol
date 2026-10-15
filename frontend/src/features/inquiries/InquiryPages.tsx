import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { PrivacyNotice } from '@/features/assistant/AssistantPage'
import { VoiceRecorder } from '@/features/assistant/VoiceRecorder'
import { assistantApi } from '@/features/assistant/api'
import { ReservationEditor } from '@/features/reservations/ReservationForm'
import { inquiryApi, inquiryStatusLabels, type Inquiry } from './api'

const field = 'mt-2 w-full rounded-lg border bg-white p-3'
const channelLabels = {
  whatsapp_manual: 'WhatsApp manual',
  whatsapp_api: 'WhatsApp oficial',
  phone: 'Teléfono',
  other: 'Otro',
}

export function InquiryList() {
  const { tenant } = useTenantContext()
  const [archived, setArchived] = useState(false)
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const result = useQuery({
    queryKey: ['inquiries', tenant.id, archived, page, status],
    queryFn: () => inquiryApi.list(tenant.id, archived, page, status),
  })
  const stats = useQuery({
    queryKey: ['inquiry-stats', tenant.id, from, to],
    queryFn: () => inquiryApi.stats(tenant.id, from, to),
    enabled: (!from && !to) || (!!from && !!to && to > from),
  })
  return (
    <section className="space-y-5">
      <h1 className="text-3xl font-bold">Consultas</h1>
      <p>
        Registro manual de WhatsApp y llamadas. Conservación operativa de 90 días; las vencidas
        pasan al archivo sin eliminarse.
      </p>
      <Button asChild>
        <Link to="/consultas/nueva">Nueva consulta</Link>
      </Button>
      <div className="flex flex-wrap gap-5">
        <label className="flex gap-2">
          <input
            type="checkbox"
            checked={archived}
            onChange={(event) => {
              setArchived(event.target.checked)
              setPage(1)
            }}
          />
          Ver archivo
        </label>
        <label>
          Estado
          <select
            className={field}
            value={status}
            onChange={(event) => {
              setStatus(event.target.value)
              setPage(1)
            }}
          >
            <option value="">Todos</option>
            {Object.entries(inquiryStatusLabels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <details>
        <summary>Estadísticas por canal y estado</summary>
        <div className="my-3 grid gap-4 sm:grid-cols-2">
          <label>
            Creación desde
            <input
              type="date"
              className={field}
              value={from}
              onChange={(event) => setFrom(event.target.value)}
            />
          </label>
          <label>
            Creación hasta (fin exclusivo)
            <input
              type="date"
              className={field}
              value={to}
              onChange={(event) => setTo(event.target.value)}
            />
          </label>
        </div>
        <ul>
          {stats.data?.counts.map((row) => (
            <li key={`${row.channel}-${row.status}`}>
              {channelLabels[row.channel as keyof typeof channelLabels]} ·{' '}
              {inquiryStatusLabels[row.status as keyof typeof inquiryStatusLabels]}: {row.count}
            </li>
          ))}
        </ul>
      </details>
      {((from && !to) || (!from && to) || (from && to <= from)) && (
        <p role="alert">Completa un periodo válido para las estadísticas.</p>
      )}
      {stats.error && <p role="alert">{stats.error.message}</p>}
      {result.isPending && <p role="status">Cargando consultas…</p>}
      {result.error && <p role="alert">{result.error.message}</p>}
      {result.data?.results.length === 0 && <p>No hay consultas en esta vista.</p>}
      <div className="grid gap-4 sm:grid-cols-2">
        {result.data?.results.map((item) => (
          <article className="rounded-xl border bg-white p-5" key={item.id}>
            <Link className="font-medium text-primary underline" to={`/consultas/${item.id}`}>
              Consulta {item.id.slice(0, 8)}
            </Link>
            <p>
              {channelLabels[item.channel]} · {inquiryStatusLabels[item.status]}
            </p>
            <p className="mt-2 break-words">{item.original_text.slice(0, 140)}</p>
            {item.expiry_warning && (
              <p className="mt-2 text-amber-800">
                {item.expired ? 'Archivada por vencimiento' : 'Vence dentro de 7 días'}
              </p>
            )}
          </article>
        ))}
      </div>
      <div className="flex gap-3">
        <Button
          variant="outline"
          disabled={!result.data?.previous}
          onClick={() => setPage(page - 1)}
        >
          Anteriores
        </Button>
        <Button variant="outline" disabled={!result.data?.next} onClick={() => setPage(page + 1)}>
          Siguientes
        </Button>
      </div>
    </section>
  )
}

function InquiryEditor({ item }: { item?: Inquiry }) {
  const { tenant } = useTenantContext()
  const navigate = useNavigate()
  const client = useQueryClient()
  const [original, setOriginal] = useState(item?.original_text ?? '')
  const [review, setReview] = useState(item?.review_text ?? '')
  const [response, setResponse] = useState(item?.response_text ?? '')
  const [channel, setChannel] = useState<Inquiry['channel']>(item?.channel ?? 'whatsapp_manual')
  const [status, setStatus] = useState(item?.status ?? 'new')
  const [reviewed, setReviewed] = useState(false)
  const [assignee, setAssignee] = useState(item?.assignee_id ?? '')
  const [assigneePage, setAssigneePage] = useState(1)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const capabilities = useQuery({
    queryKey: ['assistant-capabilities', tenant.id],
    queryFn: () => assistantApi.capabilities(tenant.id),
  })
  const locked = item?.expired || item?.status === 'converted'
  const assignees = useQuery({
    queryKey: ['inquiry-assignees', tenant.id, assigneePage],
    queryFn: () => inquiryApi.assignees(tenant.id, assigneePage),
  })
  async function save() {
    setBusy(true)
    setError('')
    try {
      const saved = await inquiryApi.save(
        tenant.id,
        {
          channel,
          original_text: original,
          review_text: review,
          response_text: response,
          status,
          assignee_id: assignee || null,
          ...(item ? { revision: item.revision } : {}),
        },
        item?.id,
      )
      await client.invalidateQueries({ queryKey: ['inquiries', tenant.id] })
      await client.invalidateQueries({ queryKey: ['inquiry-stats', tenant.id] })
      client.setQueryData(['inquiry', tenant.id, saved.id], saved)
      navigate(`/consultas/${saved.id}`)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo guardar.')
    } finally {
      setBusy(false)
    }
  }
  async function analyze() {
    if (!item || !reviewed) return
    setBusy(true)
    setError('')
    try {
      const saved = await inquiryApi.analyze(tenant.id, item.id, item.revision, review)
      client.setQueryData(['inquiry', tenant.id, saved.id], saved)
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : 'No se pudo analizar. Puedes continuar manualmente.',
      )
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="space-y-6">
      {locked && (
        <p className="rounded border p-4">
          Consulta de solo lectura: {item?.expired ? 'vencida' : 'convertida'}. Puedes crear una
          nueva consulta manualmente.
        </p>
      )}
      <form
        className="space-y-4 rounded-xl border bg-white p-5"
        onSubmit={(event) => {
          event.preventDefault()
          void save()
        }}
      >
        <fieldset disabled={locked || busy} className="space-y-4">
          <label className="block">
            Canal
            <select
              className={field}
              value={channel}
              onChange={(event) => setChannel(event.target.value as Inquiry['channel'])}
            >
              {Object.entries(channelLabels)
                .filter(([key]) => key !== 'whatsapp_api' || item?.channel === 'whatsapp_api')
                .map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
            </select>
          </label>
          <label className="block">
            Texto original (se guarda en esta empresa)
            <textarea
              required
              maxLength={4000}
              rows={4}
              className={field}
              value={original}
              onChange={(event) => setOriginal(event.target.value)}
            />
          </label>
          <PrivacyNotice />
          <label className="block">
            Texto revisado para enviar a IA
            <textarea
              maxLength={4000}
              rows={4}
              className={field}
              value={review}
              onChange={(event) => {
                setReview(event.target.value)
                setReviewed(false)
              }}
            />
          </label>
          {capabilities.data?.voice_enabled && (
            <VoiceRecorder
              tenant={tenant.id}
              onText={(text) => {
                setReview(text)
                setReviewed(false)
              }}
            />
          )}
          <label className="block">
            Respuesta editable para copiar manualmente
            <textarea
              maxLength={4000}
              rows={4}
              className={field}
              value={response}
              onChange={(event) => setResponse(event.target.value)}
            />
          </label>
          <label className="block">
            Estado
            <select
              className={field}
              value={status}
              onChange={(event) => setStatus(event.target.value as Inquiry['status'])}
            >
              {Object.entries(inquiryStatusLabels)
                .filter(([key]) => key !== 'converted')
                .map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
            </select>
          </label>
          <label className="block">
            Responsable
            <select
              className={field}
              value={assignee}
              onChange={(event) => setAssignee(event.target.value)}
            >
              <option value="">Sin asignar</option>
              {assignee && !assignees.data?.results.some((row) => row.id === assignee) && (
                <option value={assignee}>Responsable seleccionado</option>
              )}
              {assignees.data?.results.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name || 'Colaborador'} · {row.role}
                </option>
              ))}
            </select>
          </label>
          <div className="flex gap-3">
            <Button
              type="button"
              variant="outline"
              disabled={!assignees.data?.previous}
              onClick={() => setAssigneePage(assigneePage - 1)}
            >
              Responsables anteriores
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={!assignees.data?.next}
              onClick={() => setAssigneePage(assigneePage + 1)}
            >
              Más responsables
            </Button>
          </div>
          {assignees.error && <p role="alert">{assignees.error.message}</p>}
          <Button disabled={busy}>Guardar consulta</Button>
          {item && (
            <div className="space-y-3">
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={reviewed}
                  onChange={(event) => setReviewed(event.target.checked)}
                />
                Revisé el texto y autorizo enviarlo a OpenAI.
              </label>
              <Button
                type="button"
                variant="outline"
                disabled={
                  busy ||
                  !reviewed ||
                  !review.trim() ||
                  !capabilities.data?.enabled ||
                  !capabilities.data.ready
                }
                onClick={() => {
                  void analyze()
                }}
              >
                Analizar texto revisado
              </Button>
            </div>
          )}
        </fieldset>
      </form>
      {error && <p role="alert">{error}</p>}
      {item?.converted_reservation_id && (
        <Link className="text-primary underline" to={`/reservas/${item.converted_reservation_id}`}>
          Ver borrador creado
        </Link>
      )}
      {item && Object.keys(item.extraction).length > 0 && (
        <details className="rounded-xl border p-4">
          <summary>Campos propuestos por IA: requieren revisión</summary>
          {Object.values(item.extraction).map((value, index) => {
            if (!value || typeof value !== 'object') return null
            const fields = value as Record<string, unknown>
            return (
              <p key={index}>
                Entrada: {typeof fields.check_in === 'string' ? fields.check_in : 'por indicar'} ·
                Salida: {typeof fields.check_out === 'string' ? fields.check_out : 'por indicar'} ·
                Personas: {typeof fields.guests === 'number' ? fields.guests : 'por indicar'} ·
                Precio por confirmar
              </p>
            )
          })}
        </details>
      )}
      {item && !locked && (
        <div>
          <h2 className="text-2xl font-bold">Convertir con revisión humana</h2>
          <p className="mt-3">
            Selecciona un huésped existente y completa el precio manual. La IA no crea ni confirma
            reservas.
          </p>
          <ReservationEditor inquiry={item} />
        </div>
      )}
    </div>
  )
}

export function InquiryDetail() {
  const { id } = useParams()
  const { tenant } = useTenantContext()
  const result = useQuery({
    queryKey: ['inquiry', tenant.id, id],
    queryFn: () => inquiryApi.get(tenant.id, id!),
    enabled: !!id,
  })
  if (id && result.isPending) return <p role="status">Cargando consulta…</p>
  if (id && result.error) return <p role="alert">{result.error.message}</p>
  return (
    <section className="space-y-5">
      <Link className="text-primary underline" to="/consultas">
        Volver a consultas
      </Link>
      <h1 className="text-3xl font-bold">{id ? 'Ficha de consulta' : 'Nueva consulta'}</h1>
      <InquiryEditor key={`${id ?? 'new'}-${result.data?.revision ?? 0}`} item={result.data} />
    </section>
  )
}
