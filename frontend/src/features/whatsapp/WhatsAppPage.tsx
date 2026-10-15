import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { whatsappApi, statusLabels, type Conversation } from './api'
import { TemplatesSetup } from './TemplatesSetup'

const field = 'mt-2 w-full rounded-lg border bg-white p-3'
const failureMessage = (error: unknown) =>
  error instanceof Error ? error.message : 'No se pudo completar. Continúa manualmente.'

function Setup() {
  const { tenant } = useTenantContext()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const result = useQuery({
    queryKey: ['wa-connection', tenant.id],
    queryFn: () => whatsappApi.connection(tenant.id),
  })
  async function save(form: HTMLFormElement) {
    const data = new FormData(form)
    setBusy(true)
    setError('')
    try {
      const token = String(data.get('access_token') ?? '')
      await whatsappApi.configure(tenant.id, {
        business_id: String(data.get('business_id')),
        phone_number_id: String(data.get('phone_number_id')),
        display_phone: String(data.get('display_phone')),
        enabled: data.get('enabled') === 'on',
        ...(token ? { access_token: token } : {}),
        ...(result.data ? { revision: result.data.revision } : {}),
      })
      form.reset()
      await result.refetch()
    } catch (failure) {
      setError(failureMessage(failure))
    } finally {
      setBusy(false)
    }
  }
  if (result.isPending) return <p role="status">Cargando configuración…</p>
  return (
    <details className="rounded-xl border p-5">
      <summary>Configuración administrativa</summary>
      <p className="my-3 text-sm">
        La conexión real requiere configuración privada del servidor y autorización de activación.
        Los tokens se cifran y no se muestran después de guardarlos.
      </p>
      {result.error && <p role="alert">{result.error.message}</p>}
      <form
        key={result.data?.revision ?? 'new'}
        className="space-y-3"
        onSubmit={(event) => {
          event.preventDefault()
          void save(event.currentTarget)
        }}
      >
        <label className="block">
          ID de cuenta de WhatsApp
          <input
            name="business_id"
            required
            className={field}
            defaultValue={result.data?.business_id}
            readOnly={!!result.data}
          />
        </label>
        <label className="block">
          ID de número de WhatsApp
          <input
            name="phone_number_id"
            required
            className={field}
            defaultValue={result.data?.phone_number_id}
            readOnly={!!result.data}
          />
        </label>
        <label className="block">
          Teléfono de empresa internacional
          <input
            name="display_phone"
            required
            className={field}
            defaultValue={result.data?.display_phone}
          />
        </label>
        <label className="block">
          Token nuevo (opcional)
          <input
            name="access_token"
            type="password"
            autoComplete="new-password"
            maxLength={2048}
            className={field}
          />
        </label>
        <p>
          {result.data?.token_configured
            ? 'Credencial configurada.'
            : 'Sin credencial configurada.'}
        </p>
        <label className="flex gap-3">
          <input type="checkbox" name="enabled" defaultChecked={result.data?.enabled} />
          Conexión habilitada
        </label>
        <Button disabled={busy}>{busy ? 'Guardando…' : 'Guardar conexión'}</Button>
      </form>
      {error && <p role="alert">{error}</p>}
    </details>
  )
}

export function WhatsAppPage() {
  const { tenant } = useTenantContext()
  const [page, setPage] = useState(1)
  const [archived, setArchived] = useState(false)
  const result = useQuery({
    queryKey: ['wa-conversations', tenant.id, page, archived],
    queryFn: () => whatsappApi.conversations(tenant.id, archived, page),
    refetchInterval: 10000,
  })
  const caps = useQuery({
    queryKey: ['wa-capabilities', tenant.id],
    queryFn: () => whatsappApi.capabilities(tenant.id),
    refetchInterval: 10000,
  })
  return (
    <section className="space-y-5">
      <h1 className="text-3xl font-bold">WhatsApp oficial</h1>
      {caps.data?.simulated && (
        <p className="rounded bg-muted p-4 font-medium">
          WhatsApp simulado · Datos ficticios · Sin envíos reales
        </p>
      )}
      {caps.data && !caps.data.ready && (
        <p>Integración sin activar. Continúa con las consultas manuales.</p>
      )}
      <p>
        Las respuestas requieren revisión y envío explícito. Recibir mensajes no confirma reservas
        ni activa la IA.
      </p>
      <Link className="text-primary underline" to="/consultas">
        Bandeja de consultas
      </Link>
      {tenant.role !== 'staff' && <Setup />}
      {tenant.role !== 'staff' && <TemplatesSetup tenant={tenant.id} />}
      <label className="flex gap-3">
        <input
          type="checkbox"
          checked={archived}
          onChange={(event) => {
            setArchived(event.target.checked)
            setPage(1)
          }}
        />
        Ver archivo de conversaciones
      </label>
      {result.isPending && <p role="status">Cargando conversaciones…</p>}
      {result.error && <p role="alert">{result.error.message}</p>}
      {caps.error && <p role="alert">{caps.error.message}</p>}
      {result.data?.results.length === 0 && <p>No hay conversaciones en esta vista.</p>}
      <div className="grid gap-4 sm:grid-cols-2">
        {result.data?.results.map((item) => (
          <article className="rounded-xl border bg-white p-5" key={item.id}>
            <Link className="font-medium text-primary underline" to={`/whatsapp/${item.id}`}>
              +{item.contact_phone}
            </Link>
            <p>
              {item.consent_granted ? 'Permiso registrado' : 'Sin permiso vigente de envío'}
              {item.expired ? ' · Archivada' : ''}
            </p>
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

function Composer({ conversation, enabled }: { conversation: Conversation; enabled: boolean }) {
  const { tenant } = useTenantContext()
  const client = useQueryClient()
  const [text, setText] = useState('')
  const [template, setTemplate] = useState('')
  const [templatePage, setTemplatePage] = useState(1)
  const [reviewed, setReviewed] = useState(false)
  const [reviewedRevision, setReviewedRevision] = useState<number | null>(null)
  const [source, setSource] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [requestId, setRequestId] = useState(() => crypto.randomUUID())
  const templates = useQuery({
    queryKey: ['wa-templates', tenant.id, templatePage],
    queryFn: () => whatsappApi.templates(tenant.id, templatePage),
  })
  async function refresh() {
    await client.invalidateQueries({ queryKey: ['wa-conversation', tenant.id, conversation.id] })
    await client.invalidateQueries({ queryKey: ['wa-messages', tenant.id, conversation.id] })
    await client.invalidateQueries({ queryKey: ['wa-jobs', tenant.id] })
  }
  async function grant(granted: boolean) {
    setBusy(true)
    setError('')
    try {
      await whatsappApi.consent(tenant.id, {
        conversation_id: conversation.id,
        revision: conversation.revision,
        granted,
        source,
      })
      await refresh()
    } catch (failure) {
      setError(failureMessage(failure))
    } finally {
      setBusy(false)
    }
  }
  async function prepare() {
    setBusy(true)
    setError('')
    try {
      const result = await whatsappApi.prepare(tenant.id, conversation.id)
      setText(result.text)
      setReviewed(false)
      setRequestId(crypto.randomUUID())
    } catch (failure) {
      setError(failureMessage(failure))
    } finally {
      setBusy(false)
    }
  }
  async function send() {
    if (!reviewed || !text.trim()) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const job = await whatsappApi.send(tenant.id, {
        conversation_id: conversation.id,
        text,
        revision: conversation.revision,
        request_id: requestId,
        reviewed,
        template_id: template || null,
      })
      setNotice(
        `Respuesta registrada: ${statusLabels[job.state] ?? job.state}. El estado de entrega se actualiza por separado.`,
      )
      setText('')
      setReviewed(false)
      setRequestId(crypto.randomUUID())
      await refresh()
    } catch (failure) {
      setError(failureMessage(failure))
    } finally {
      setBusy(false)
    }
  }
  const open =
    !!conversation.last_inbound_at &&
    Date.now() - new Date(conversation.last_inbound_at).getTime() < 24 * 3600000
  return (
    <fieldset disabled={busy} className="space-y-4 rounded-xl border bg-white p-5">
      <p>
        Destinatario: +{conversation.contact_phone}.{' '}
        {open
          ? 'Ventana de atención abierta (el servidor vuelve a comprobarla).'
          : 'Fuera de la ventana: selecciona una plantilla verificada.'}
      </p>
      <p>
        No incluyas RUT, saldos, notas privadas ni secretos. Un resultado incierto exige revisión;
        no se reenvía automáticamente.
      </p>
      <label className="block">
        Origen del permiso o motivo de baja
        <input
          className={field}
          maxLength={150}
          value={source}
          onChange={(event) => setSource(event.target.value)}
        />
      </label>
      <div className="flex flex-wrap gap-3">
        <Button
          type="button"
          variant="outline"
          disabled={busy || !source.trim()}
          onClick={() => {
            void grant(true)
          }}
        >
          Registrar permiso
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={busy || !source.trim()}
          onClick={() => {
            void grant(false)
          }}
        >
          Registrar baja
        </Button>
      </div>
      <label className="block">
        Plantilla aprobada (opcional)
        <select
          className={field}
          value={template}
          onChange={(event) => {
            setTemplate(event.target.value)
            setText(
              templates.data?.results.find((item) => item.id === event.target.value)?.body ?? '',
            )
            setReviewed(false)
            setRequestId(crypto.randomUUID())
          }}
        >
          <option value="">Texto de atención</option>
          {template && !templates.data?.results.some((item) => item.id === template) && (
            <option value={template}>Plantilla seleccionada</option>
          )}
          {templates.data?.results
            .filter((item) => item.approved && item.enabled)
            .map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} · {item.language}
              </option>
            ))}
        </select>
      </label>
      <div className="flex gap-3">
        <Button
          type="button"
          variant="outline"
          disabled={!templates.data?.previous}
          onClick={() => setTemplatePage(templatePage - 1)}
        >
          Plantillas anteriores
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={!templates.data?.next}
          onClick={() => setTemplatePage(templatePage + 1)}
        >
          Más plantillas
        </Button>
      </div>
      {templates.error && <p role="alert">{templates.error.message}</p>}
      <Button
        type="button"
        variant="outline"
        disabled={busy || !!template}
        onClick={() => {
          void prepare()
        }}
      >
        Preparar respuesta manual
      </Button>
      <label className="block">
        Respuesta para revisar
        <textarea
          className={field}
          rows={5}
          maxLength={4000}
          value={text}
          readOnly={!!template}
          onChange={(event) => {
            setText(event.target.value)
            setReviewed(false)
            setRequestId(crypto.randomUUID())
          }}
        />
      </label>
      <label className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={reviewed && reviewedRevision === conversation.revision}
          onChange={(event) => {
            setReviewed(event.target.checked)
            setReviewedRevision(conversation.revision)
          }}
        />
        Revisé destinatario, contenido y permiso. Autorizar esta respuesta.
      </label>
      <Button
        disabled={
          busy ||
          !enabled ||
          !reviewed ||
          reviewedRevision !== conversation.revision ||
          !text.trim() ||
          !conversation.consent_granted ||
          (!open && !template)
        }
        onClick={() => {
          void send()
        }}
      >
        {busy ? 'Procesando…' : 'Autorizar envío de respuesta'}
      </Button>
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
    </fieldset>
  )
}

export function WhatsAppConversation() {
  const { tenant } = useTenantContext()
  const client = useQueryClient()
  const { id } = useParams()
  const [page, setPage] = useState(1)
  const [archived, setArchived] = useState(false)
  const caps = useQuery({
    queryKey: ['wa-capabilities', tenant.id],
    queryFn: () => whatsappApi.capabilities(tenant.id),
    refetchInterval: 10000,
  })
  const conversation = useQuery({
    queryKey: ['wa-conversation', tenant.id, id],
    queryFn: () => whatsappApi.conversation(tenant.id, id!),
    refetchInterval: 10000,
  })
  const messages = useQuery({
    queryKey: ['wa-messages', tenant.id, id, page, archived],
    queryFn: async () => {
      const result = await whatsappApi.messages(tenant.id, id!, page, archived)
      if (result.conversation) {
        const snapshot = result.conversation
        client.setQueryData<Conversation>(['wa-conversation', tenant.id, id], (current) =>
          current && current.revision > snapshot.revision ? current : snapshot,
        )
      }
      return result
    },
    refetchInterval: 5000,
  })
  if (conversation.isPending) return <p role="status">Cargando conversación…</p>
  if (conversation.error) return <p role="alert">{conversation.error.message}</p>
  return (
    <section className="space-y-5">
      <Link className="text-primary underline" to="/whatsapp">
        Volver a WhatsApp
      </Link>
      <h1 className="text-3xl font-bold">Conversación +{conversation.data.contact_phone}</h1>
      {caps.data?.simulated && (
        <p className="rounded bg-muted p-4 font-medium">
          WhatsApp simulado · Datos ficticios · Sin envíos reales
        </p>
      )}
      {caps.data && (!caps.data.ready || !caps.data.enabled) && (
        <p>Conexión desactivada o sin configurar. Puedes continuar manualmente.</p>
      )}
      <label className="flex gap-3">
        <input
          type="checkbox"
          checked={archived}
          onChange={(event) => {
            setArchived(event.target.checked)
            setPage(1)
          }}
        />
        Ver mensajes archivados
      </label>
      {messages.error && <p role="alert">{messages.error.message}</p>}
      {messages.data?.results.map((message) => (
        <article key={message.id} className="rounded-xl border bg-white p-5">
          <p className="text-sm text-muted-foreground">
            {message.direction === 'inbound' ? 'Cliente' : 'Equipo'} ·{' '}
            {statusLabels[message.status] ?? message.status}
          </p>
          <p className="mt-3 whitespace-pre-wrap break-words">{message.text}</p>
          {message.inquiry_id && (
            <Link
              className="mt-3 inline-block text-primary underline"
              to={`/consultas/${message.inquiry_id}`}
            >
              Revisar consulta y preparar borrador de reserva
            </Link>
          )}
        </article>
      ))}
      <div className="flex gap-3">
        <Button
          variant="outline"
          disabled={!messages.data?.previous}
          onClick={() => setPage(page - 1)}
        >
          Mensajes anteriores
        </Button>
        <Button variant="outline" disabled={!messages.data?.next} onClick={() => setPage(page + 1)}>
          Más mensajes
        </Button>
      </div>
      {conversation.data.expired ? (
        <p>Conversación archivada. No admite nuevos envíos.</p>
      ) : (
        <Composer
          key={conversation.data.id}
          conversation={conversation.data}
          enabled={!!caps.data?.ready && caps.data.enabled}
        />
      )}
    </section>
  )
}
