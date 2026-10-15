import { z } from 'zod'
import { request } from '@/lib/api'

export const dayKinds = {
  cleaning: 'Limpieza pendiente',
  arrivals: 'Entradas',
  departures: 'Salidas',
  overdue_stays: 'Salidas pendientes',
  expired_holds: 'Retenciones vencidas',
  maintenance: 'Mantenimiento',
}
export type DayKind = keyof typeof dayKinds
const daySchema = z.object({
  date: z.string(),
  timezone: z.string(),
  kind: z.string(),
  counts: z.record(z.string(), z.number()),
  count: z.number(),
  page: z.number(),
  next: z.boolean(),
  previous: z.boolean(),
  results: z.array(
    z.object({
      id: z.string().uuid(),
      property_name: z.string(),
      property_active: z.boolean(),
      start: z.string(),
      end: z.string(),
      status: z.string(),
      url: z.string().regex(/^\/(reservas|limpieza)(\/|$)/),
    }),
  ),
})
export const operationsApi = {
  async day(tenant: string, date: string, kind: DayKind, page: number, property?: string) {
    const params = new URLSearchParams({ date, kind, page: String(page) })
    if (property) params.set('property_id', property)
    return daySchema.parse(
      await request(`/api/v1/operations/day/?${params}`, {
        headers: { 'X-Tenant-Context': tenant },
      }),
    )
  },
}
