import { z } from 'zod'
import { request, write } from '@/lib/api'
import { guestSummarySchema } from '@/features/guests/api'

export const statusLabels = {
  draft: 'Borrador',
  pending: 'Pendiente',
  confirmed: 'Confirmada',
  checked_in: 'En estadía',
  checked_out: 'Finalizada',
  cancelled: 'Cancelada',
  no_show: 'No se presentó',
}
export const sourceLabels = {
  direct: 'Directa',
  phone: 'Teléfono',
  whatsapp: 'WhatsApp',
  other: 'Otra',
}
export const blockLabels = {
  maintenance: 'Mantenimiento',
  owner_use: 'Uso del propietario',
  other: 'Otro',
}
export const reservationSchema = z.object({
  id: z.string().uuid(),
  property_id: z.string().uuid(),
  property_name: z.string(),
  primary_guest_id: z.string().uuid(),
  guest: guestSummarySchema,
  check_in: z.string(),
  check_out: z.string(),
  adults: z.number().int(),
  children: z.number().int(),
  status: z.enum([
    'draft',
    'pending',
    'confirmed',
    'checked_in',
    'checked_out',
    'cancelled',
    'no_show',
  ]),
  hold_until: z.string().nullable(),
  hold_active: z.boolean(),
  total_amount: z.string(),
  received_amount: z.string(),
  balance: z.string(),
  payment_state: z.enum(['unpaid', 'partial', 'paid', 'credit']),
  currency: z.string(),
  source: z.enum(['direct', 'phone', 'whatsapp', 'other']),
  created_at: z.string(),
  updated_at: z.string(),
})
const detailSchema = reservationSchema.extend({ notes: z.string(), cancel_reason: z.string() })
export type Reservation = z.infer<typeof detailSchema>
export type ReservationInput = {
  property_id: string
  primary_guest_id: string
  check_in: string
  check_out: string
  adults: number
  children: number
  total_amount: string
  source: Reservation['source']
  notes: string
  hold_until?: string | null
  status?: 'draft' | 'pending' | 'confirmed'
}
const blockSchema = z.object({
  id: z.string().uuid(),
  property_id: z.string().uuid(),
  property_name: z.string(),
  start_date: z.string(),
  end_date: z.string(),
  reason: z.enum(['maintenance', 'owner_use', 'other']),
  notes: z.string(),
  active: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type Block = z.infer<typeof blockSchema>
export type BlockInput = Pick<Block, 'property_id' | 'start_date' | 'end_date' | 'reason' | 'notes'>
const availabilityItem = z.object({
  property_id: z.string().uuid(),
  property_name: z.string(),
  capacity: z.number(),
  available: z.boolean(),
})
const paginated = <T extends z.ZodType>(item: T) =>
  z.object({
    count: z.number(),
    next: z.string().nullable(),
    previous: z.string().nullable(),
    results: z.array(item),
  })
const headers = (tenant: string) => ({ 'X-Tenant-Context': tenant })

export const reservationApi = {
  async list(tenant: string, filters: Record<string, string>) {
    return paginated(reservationSchema).parse(
      await request(`/api/v1/reservations/?${new URLSearchParams(filters)}`, {
        headers: headers(tenant),
      }),
    )
  },
  async get(tenant: string, id: string) {
    return detailSchema.parse(
      await request(`/api/v1/reservations/${id}/`, { headers: headers(tenant) }),
    )
  },
  async save(tenant: string, data: ReservationInput, id?: string) {
    return detailSchema.parse(
      await write(
        id ? `/api/v1/reservations/${id}/` : '/api/v1/reservations/',
        data,
        id ? 'PATCH' : 'POST',
        headers(tenant),
      ),
    )
  },
  async action(
    tenant: string,
    id: string,
    action: 'confirm' | 'cancel' | 'status',
    data: Record<string, string | null>,
  ) {
    return detailSchema.parse(
      await write(`/api/v1/reservations/${id}/${action}/`, data, 'POST', headers(tenant)),
    )
  },
  async availability(
    tenant: string,
    start: string,
    end: string,
    guests: number,
    property?: string,
    page = 1,
  ) {
    const params = new URLSearchParams({
      from: start,
      to: end,
      guests: String(guests),
      page: String(page),
    })
    if (property) params.set('property_id', property)
    return paginated(availabilityItem).parse(
      await request(`/api/v1/availability/?${params}`, { headers: headers(tenant) }),
    )
  },
}
export const blockApi = {
  async list(tenant: string, page: number, active: string) {
    const params = new URLSearchParams({ page: String(page) })
    if (active !== 'all') params.set('active', active)
    return paginated(blockSchema).parse(
      await request(`/api/v1/availability-blocks/?${params}`, { headers: headers(tenant) }),
    )
  },
  async get(tenant: string, id: string) {
    return blockSchema.parse(
      await request(`/api/v1/availability-blocks/${id}/`, { headers: headers(tenant) }),
    )
  },
  async save(tenant: string, data: Partial<BlockInput> & { active?: boolean }, id?: string) {
    return blockSchema.parse(
      await write(
        id ? `/api/v1/availability-blocks/${id}/` : '/api/v1/availability-blocks/',
        data,
        id ? 'PATCH' : 'POST',
        headers(tenant),
      ),
    )
  },
}
