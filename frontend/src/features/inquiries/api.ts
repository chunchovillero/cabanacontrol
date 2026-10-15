import { z } from 'zod'
import { request, write } from '@/lib/api'
import { reservationSchema, type ReservationInput } from '@/features/reservations/api'

export const inquirySchema = z.object({
  id: z.string().uuid(),
  channel: z.enum(['whatsapp_manual', 'whatsapp_api', 'phone', 'other']),
  original_text: z.string(),
  review_text: z.string(),
  extraction: z.record(z.string(), z.unknown()),
  response_text: z.string(),
  status: z.enum(['new', 'responded', 'waiting_customer', 'converted', 'discarded']),
  assignee_id: z.string().uuid().nullable(),
  guest_id: z.string().uuid().nullable(),
  revision: z.number().int(),
  converted_reservation_id: z.string().uuid().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  expires_at: z.string(),
  archived_at: z.string().nullable(),
  expired: z.boolean(),
  expiry_warning: z.boolean(),
})
export type Inquiry = z.infer<typeof inquirySchema>
const headers = (tenant: string) => ({ 'X-Tenant-Context': tenant })
export const inquiryApi = {
  async assignees(tenant: string, page: number) {
    return z
      .object({
        next: z.string().nullable(),
        previous: z.string().nullable(),
        results: z.array(
          z.object({
            id: z.string().uuid(),
            name: z.string(),
            role: z.string(),
            active: z.boolean(),
          }),
        ),
      })
      .parse(
        await request(`/api/v1/inquiries/assignees/?page=${page}`, { headers: headers(tenant) }),
      )
  },
  async list(tenant: string, archived: boolean, page: number, status = '') {
    const params = new URLSearchParams({ archived: String(archived), page: String(page) })
    if (status) params.set('status', status)
    return z
      .object({
        count: z.number(),
        next: z.string().nullable(),
        previous: z.string().nullable(),
        results: z.array(inquirySchema),
      })
      .parse(await request(`/api/v1/inquiries/?${params}`, { headers: headers(tenant) }))
  },
  async get(tenant: string, id: string) {
    return inquirySchema.parse(
      await request(`/api/v1/inquiries/${encodeURIComponent(id)}/`, { headers: headers(tenant) }),
    )
  },
  async save(tenant: string, data: Record<string, unknown>, id?: string) {
    return inquirySchema.parse(
      await write(
        id ? `/api/v1/inquiries/${encodeURIComponent(id)}/` : '/api/v1/inquiries/',
        data,
        id ? 'PATCH' : 'POST',
        headers(tenant),
      ),
    )
  },
  async analyze(tenant: string, id: string, revision: number, text: string) {
    return inquirySchema.parse(
      await write(
        `/api/v1/inquiries/${encodeURIComponent(id)}/analyze/`,
        { text, revision, reviewed: true },
        'POST',
        headers(tenant),
        35000,
      ),
    )
  },
  async convert(tenant: string, id: string, revision: number, data: ReservationInput) {
    return reservationSchema
      .extend({ notes: z.string(), cancel_reason: z.string() })
      .parse(
        await write(
          `/api/v1/inquiries/${encodeURIComponent(id)}/convert/`,
          { ...data, revision, reviewed: true },
          'POST',
          headers(tenant),
        ),
      )
  },
  async stats(tenant: string, from = '', to = '') {
    return z
      .object({
        counts: z.array(z.object({ channel: z.string(), status: z.string(), count: z.number() })),
      })
      .parse(
        await request(
          `/api/v1/inquiries/stats/${from && to ? `?${new URLSearchParams({ from, to })}` : ''}`,
          { headers: headers(tenant) },
        ),
      )
  },
}
export const inquiryStatusLabels = {
  new: 'Nueva',
  responded: 'Respondida',
  waiting_customer: 'Esperando cliente',
  converted: 'Convertida',
  discarded: 'Descartada',
}
