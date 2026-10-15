import { z } from 'zod'
import { request } from '@/lib/api'

const eventSchema = z.object({
  id: z.string(),
  kind: z.enum(['reservation', 'block']),
  entity_id: z.string().uuid(),
  property_id: z.string().uuid(),
  property_name: z.string(),
  property_active: z.boolean(),
  title: z.string(),
  start: z.string(),
  end: z.string(),
  status: z.string(),
  blocks_inventory: z.boolean(),
  url: z.string().startsWith('/reservas'),
})
const calendarSchema = z.object({ timezone: z.string(), events: z.array(eventSchema) })
export type CalendarEvent = z.infer<typeof eventSchema>

export const calendarApi = {
  async get(tenant: string, start: string, end: string, property?: string) {
    const params = new URLSearchParams({ from: start, to: end })
    if (property) params.set('property_id', property)
    return calendarSchema.parse(
      await request(`/api/v1/calendar/?${params}`, { headers: { 'X-Tenant-Context': tenant } }),
    )
  },
}
