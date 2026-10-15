import { z } from 'zod'
import { ApiError, request, write } from '@/lib/api'

export const guestSummarySchema = z.object({
  id: z.string().uuid(),
  first_name: z.string(),
  last_name: z.string(),
  document_type: z.enum(['rut', 'passport', 'other']),
  document_masked: z.string(),
  active: z.boolean(),
})
export const guestDetailSchema = guestSummarySchema.extend({
  document_number: z.string().nullable(),
  phone: z.string(),
  email: z.string(),
  notes: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type GuestSummary = z.infer<typeof guestSummarySchema>
export type Guest = z.infer<typeof guestDetailSchema>
export type GuestInput = {
  first_name: string
  last_name: string
  document_type: Guest['document_type']
  document_number: string
  phone: string
  email: string
  notes: string
}
const resultSchema = z.object({
  count: z.number(),
  page: z.number(),
  has_next: z.boolean(),
  has_previous: z.boolean(),
  results: z.array(guestSummarySchema),
})
const headers = (tenant: string) => ({ 'X-Tenant-Context': tenant })

export const guestApi = {
  async search(tenant: string, query: string, active: string, page: number) {
    return resultSchema.parse(
      await write(
        '/api/v1/guests/search/',
        { query, page, ...(active === 'all' ? {} : { active: active === 'true' }) },
        'POST',
        headers(tenant),
      ),
    )
  },
  async get(tenant: string, id: string) {
    return guestDetailSchema.parse(
      await request(`/api/v1/guests/${encodeURIComponent(id)}/`, { headers: headers(tenant) }),
    )
  },
  async create(tenant: string, data: GuestInput) {
    return guestDetailSchema.parse(await write('/api/v1/guests/', data, 'POST', headers(tenant)))
  },
  async update(tenant: string, id: string, data: Partial<GuestInput> & { active?: boolean }) {
    return guestDetailSchema.parse(
      await write(`/api/v1/guests/${encodeURIComponent(id)}/`, data, 'PATCH', headers(tenant)),
    )
  },
}

export function duplicateGuestId(error: unknown): string | null {
  if (!(error instanceof ApiError)) return null
  const parsed = z
    .object({
      error: z.object({
        code: z.literal('duplicate_document'),
        details: z.object({ existing_guest_id: z.string().uuid() }),
      }),
    })
    .safeParse(error.payload)
  return parsed.success ? parsed.data.error.details.existing_guest_id : null
}

export const documentLabels = { rut: 'RUT chileno', passport: 'Pasaporte', other: 'Otro documento' }
