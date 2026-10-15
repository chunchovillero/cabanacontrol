import { z } from 'zod'
import { request, write } from '@/lib/api'

const connectionSchema = z.object({
  id: z.string().uuid(),
  business_id: z.string(),
  phone_number_id: z.string(),
  display_phone: z.string(),
  enabled: z.boolean(),
  revision: z.number().int(),
  token_configured: z.boolean(),
})
export const conversationSchema = z.object({
  id: z.string().uuid(),
  contact_phone: z.string(),
  last_inbound_at: z.string().nullable(),
  revision: z.number().int(),
  expires_at: z.string(),
  consent_granted: z.boolean(),
  expired: z.boolean(),
})
const messageSchema = z.object({
  id: z.string().uuid(),
  conversation_id: z.string().uuid(),
  direction: z.enum(['inbound', 'outbound']),
  text: z.string(),
  status: z.string(),
  occurred_at: z.string(),
  expires_at: z.string(),
  inquiry_id: z.string().uuid().nullable(),
})
const templateSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  language: z.string(),
  body: z.string(),
  approved: z.boolean(),
  enabled: z.boolean(),
  purpose: z.string(),
  verified_at: z.string().nullable(),
})
const jobSchema = z.object({
  id: z.string().uuid(),
  message_id: z.string().uuid(),
  state: z.string(),
  attempts: z.number(),
  last_error_code: z.string(),
  created_at: z.string(),
})
const headers = (tenant: string) => ({ 'X-Tenant-Context': tenant })
const pageSchema = <T extends z.ZodType>(schema: T) =>
  z.object({
    count: z.number(),
    next: z.string().nullable(),
    previous: z.string().nullable(),
    results: z.array(schema),
  })
export type Conversation = z.infer<typeof conversationSchema>
export const whatsappApi = {
  async capabilities(tenant: string) {
    return z
      .object({ ready: z.boolean(), enabled: z.boolean(), simulated: z.boolean() })
      .parse(await request('/api/v1/whatsapp/capabilities/', { headers: headers(tenant) }))
  },
  async connection(tenant: string) {
    return connectionSchema
      .nullable()
      .parse(await request('/api/v1/whatsapp/connection/', { headers: headers(tenant) }))
  },
  async configure(tenant: string, data: Record<string, unknown>) {
    return connectionSchema.parse(
      await write('/api/v1/whatsapp/connection/', data, 'PATCH', headers(tenant)),
    )
  },
  async conversations(tenant: string, archived: boolean, page: number) {
    return pageSchema(conversationSchema).parse(
      await request(`/api/v1/whatsapp/conversations/?archived=${archived}&page=${page}`, {
        headers: headers(tenant),
      }),
    )
  },
  async conversation(tenant: string, id: string) {
    return conversationSchema.parse(
      await request(`/api/v1/whatsapp/conversations/${encodeURIComponent(id)}/`, {
        headers: headers(tenant),
      }),
    )
  },
  async messages(tenant: string, id: string, page: number, archived = false) {
    return pageSchema(messageSchema)
      .extend({ conversation: conversationSchema.optional() })
      .parse(
        await request(
          `/api/v1/whatsapp/conversations/${encodeURIComponent(id)}/messages/?page=${page}&archived=${archived}`,
          { headers: headers(tenant) },
        ),
      )
  },
  async templates(tenant: string, page: number) {
    return pageSchema(templateSchema).parse(
      await request(`/api/v1/whatsapp/templates/?page=${page}`, { headers: headers(tenant) }),
    )
  },
  async saveTemplate(tenant: string, data: Record<string, unknown>) {
    return templateSchema.parse(
      await write('/api/v1/whatsapp/templates/', data, 'POST', headers(tenant)),
    )
  },
  async consent(
    tenant: string,
    data: { conversation_id: string; revision: number; granted: boolean; source: string },
  ) {
    return conversationSchema.parse(
      await write('/api/v1/whatsapp/consent/', data, 'POST', headers(tenant)),
    )
  },
  async prepare(tenant: string, id: string) {
    return z
      .object({ text: z.string(), revision: z.number().int() })
      .parse(
        await write(
          '/api/v1/whatsapp/messages/prepare/',
          { conversation_id: id },
          'POST',
          headers(tenant),
        ),
      )
  },
  async send(
    tenant: string,
    data: {
      conversation_id: string
      text: string
      revision: number
      request_id: string
      reviewed: boolean
      template_id: string | null
    },
  ) {
    return jobSchema.parse(
      await write('/api/v1/whatsapp/messages/send/', data, 'POST', headers(tenant)),
    )
  },
  async jobs(tenant: string, page: number) {
    return pageSchema(jobSchema).parse(
      await request(`/api/v1/whatsapp/jobs/?page=${page}`, { headers: headers(tenant) }),
    )
  },
}
export const statusLabels: Record<string, string> = {
  received: 'Recibido',
  queued: 'En cola',
  pending: 'Pendiente',
  working: 'Procesando',
  retry: 'Reintento pendiente',
  accepted: 'Aceptado por proveedor',
  sent: 'Enviado',
  delivered: 'Entregado',
  read: 'Leído',
  failed: 'Fallido',
  blocked: 'Bloqueado por cambio de autorización',
  unknown: 'Resultado incierto: revisar sin reenviar automáticamente',
}
