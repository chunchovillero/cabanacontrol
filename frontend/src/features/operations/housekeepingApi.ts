import { z } from 'zod'
import { request, write } from '@/lib/api'

export const taskLabels = {
  pending: 'Pendiente',
  in_progress: 'En curso',
  completed: 'Completada',
  cancelled: 'Cancelada',
}
const taskSchema = z.object({
  id: z.string().uuid(),
  property_id: z.string().uuid(),
  property_name: z.string(),
  reservation_id: z.string().nullable(),
  assigned_to_id: z.string().nullable(),
  assigned_name: z.string().nullable(),
  source: z.enum(['manual', 'checkout']),
  status: z.enum(['pending', 'in_progress', 'completed', 'cancelled']),
  due_at: z.string(),
  bathroom: z.boolean(),
  kitchen: z.boolean(),
  bedrooms: z.boolean(),
  inventory: z.boolean(),
  notes: z.string(),
  cancel_reason: z.string(),
  completed_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type Task = z.infer<typeof taskSchema>
const headers = (tenant: string) => ({ 'X-Tenant-Context': tenant })
const pageSchema = z.object({
  count: z.number(),
  next: z.string().nullable(),
  previous: z.string().nullable(),
  results: z.array(taskSchema),
})
export const housekeepingApi = {
  async list(tenant: string, status: string, page: number) {
    const params = new URLSearchParams({ page: String(page) })
    if (status) params.set('status', status)
    return pageSchema.parse(
      await request(`/api/v1/housekeeping/?${params}`, { headers: headers(tenant) }),
    )
  },
  async get(tenant: string, id: string) {
    return taskSchema.parse(
      await request(`/api/v1/housekeeping/${id}/`, { headers: headers(tenant) }),
    )
  },
  async save(tenant: string, data: unknown, id?: string) {
    return taskSchema.parse(
      await write(
        id ? `/api/v1/housekeeping/${id}/` : '/api/v1/housekeeping/',
        data,
        id ? 'PATCH' : 'POST',
        headers(tenant),
      ),
    )
  },
  async assignees(tenant: string) {
    const items: { id: string; name: string }[] = []
    for (let page = 1; page <= 100; page++) {
      const data = z
        .object({
          next: z.string().nullable(),
          results: z.array(z.object({ id: z.string().uuid(), name: z.string() })),
        })
        .parse(
          await request(`/api/v1/housekeeping/assignees/?page=${page}`, {
            headers: headers(tenant),
          }),
        )
      items.push(...data.results)
      if (!data.next) return items
    }
    throw new Error('Hay demasiados integrantes para cargar. Contacta al administrador.')
  },
}
