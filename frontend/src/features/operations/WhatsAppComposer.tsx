import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { request } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'

export function whatsappLink(phone: string, message: string) {
  const normalized = phone.trim().replace(/[ ()-]/g, '')
  if (!/^\+[1-9][0-9]{6,14}$/.test(normalized) || message.length > 2000) return null
  const url = new URL(`https://wa.me/${normalized.slice(1)}`)
  if (message.trim()) url.searchParams.set('text', message.trim())
  return url.toString()
}

function Composer({ initial }: { initial: { phone: string; message: string } }) {
  const [phone, setPhone] = useState(initial.phone)
  const [message, setMessage] = useState(initial.message)
  const [copyStatus, setCopyStatus] = useState('')
  const link = whatsappLink(phone, message)
  return (
    <div className="mt-4 space-y-4 rounded-xl border bg-white p-5">
      <p className="text-sm text-muted-foreground">
        Revisa el destinatario y el texto. Abrir WhatsApp entrega estos datos a WhatsApp; el mensaje
        queda preparado y tú decides enviarlo.
      </p>
      <label className="block">
        Teléfono internacional de WhatsApp
        <input
          className="mt-2 w-full rounded-lg border p-3"
          type="tel"
          maxLength={30}
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <span className="mt-2 block text-sm">
          Incluye + y código de país. No se guarda este ajuste en la ficha del huésped.
        </span>
      </label>
      <label className="block">
        Mensaje para revisar
        <textarea
          className="mt-2 w-full rounded-lg border p-3"
          maxLength={2000}
          rows={5}
          value={message}
          onChange={(e) => {
            setMessage(e.target.value)
            setCopyStatus('')
          }}
        />
      </label>
      {!link && (
        <p className="text-sm">Indica un teléfono internacional válido antes de abrir WhatsApp.</p>
      )}
      <div className="flex flex-wrap gap-3">
        {link ? (
          <Button asChild>
            <a href={link} target="_blank" rel="noopener noreferrer">
              Abrir WhatsApp
            </a>
          </Button>
        ) : (
          <Button disabled>Abrir WhatsApp</Button>
        )}
        <Button
          type="button"
          variant="outline"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(message)
              setCopyStatus('Mensaje copiado.')
            } catch {
              setCopyStatus('No se pudo copiar. Selecciona el texto y cópialo manualmente.')
            }
          }}
        >
          Copiar mensaje
        </Button>
      </div>
      {copyStatus && <p role="status">{copyStatus}</p>}
    </div>
  )
}

export function WhatsAppComposer({ reservationId }: { reservationId: string }) {
  const { tenant } = useTenantContext()
  const [open, setOpen] = useState(false)
  const draft = useQuery({
    queryKey: ['whatsapp-draft', tenant.id, reservationId],
    queryFn: async () =>
      z.object({ phone: z.string(), message: z.string() }).parse(
        await request(`/api/v1/reservations/${reservationId}/whatsapp-draft/`, {
          headers: { 'X-Tenant-Context': tenant.id },
        }),
      ),
    enabled: open,
    staleTime: 0,
  })
  return (
    <section className="mt-8">
      <h2 className="text-xl font-semibold">Contacto manual</h2>
      <Button className="mt-3" variant="outline" onClick={() => setOpen(!open)}>
        {open ? 'Cerrar borrador' : 'Preparar WhatsApp'}
      </Button>
      {open && draft.isPending && (
        <p role="status" className="mt-3">
          Preparando mensaje…
        </p>
      )}
      {open && draft.error && (
        <p role="alert" className="mt-3">
          {draft.error.message}
        </p>
      )}
      {open && draft.data && <Composer key={draft.data.message} initial={draft.data} />}
    </section>
  )
}
