import { z } from 'zod'
import { request } from '@/lib/api'

export const dashboardSchema = z.object({
  timezone: z.string(),
  from_date: z.string(),
  to_date: z.string(),
  today: z.object({
    date: z.string(),
    active_properties: z.number(),
    occupied: z.number(),
    retained: z.number(),
    blocked: z.number(),
    available: z.number(),
    arrivals: z.number(),
    departures: z.number(),
  }),
  occupied_nights: z.number(),
  capacity_nights: z.number(),
  occupancy_percent: z.string(),
  blocked_nights: z.number(),
  money: z.array(
    z.object({
      currency: z.string(),
      collected: z.string(),
      agreed: z.string(),
      outstanding: z.string(),
      credit: z.string(),
    }),
  ),
})
export type Dashboard = z.infer<typeof dashboardSchema>
export const dashboardApi = {
  async get(tenant: string, start: string, end: string, property?: string) {
    const params = new URLSearchParams({ from: start, to: end })
    if (property) params.set('property_id', property)
    return dashboardSchema.parse(
      await request(`/api/v1/dashboard/?${params}`, { headers: { 'X-Tenant-Context': tenant } }),
    )
  },
}
