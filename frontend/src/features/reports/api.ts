import { z } from 'zod'
import { ApiError, publicUrl, request } from '@/lib/api'
import { dashboardSchema } from '@/features/dashboard/api'

export type ReportKind = 'summary' | 'reservations' | 'payments'
export type ReportFilters = {
  start: string
  end: string
  property: string
  kind: ReportKind
  status: string
}
const reservationSchema = z.object({
  id: z.string().uuid(),
  property_id: z.string().uuid(),
  property_name: z.string(),
  property_active: z.boolean(),
  check_in: z.string(),
  check_out: z.string(),
  status: z.string(),
  status_label: z.string(),
  currency: z.string(),
  total_amount: z.string(),
  received_amount: z.string(),
  balance: z.string(),
})
const paymentSchema = z.object({
  id: z.string().uuid(),
  reservation_id: z.string().uuid(),
  property_id: z.string().uuid(),
  property_name: z.string(),
  paid_at: z.string(),
  currency: z.string(),
  amount: z.string(),
  method: z.string(),
  method_label: z.string(),
})
const pageSchema = z.object({
  count: z.number(),
  page: z.number(),
  next: z.boolean(),
  previous: z.boolean(),
})
export const summarySchema = dashboardSchema.extend({ cancelled_count: z.number() })
export type Summary = z.infer<typeof summarySchema>
export type ReservationRow = z.infer<typeof reservationSchema>
export type PaymentRow = z.infer<typeof paymentSchema>
function params(filters: ReportFilters, page?: number) {
  const values = new URLSearchParams({ from: filters.start, to: filters.end, kind: filters.kind })
  if (filters.property) values.set('property_id', filters.property)
  if (filters.kind === 'reservations' && filters.status) values.set('status', filters.status)
  if (page !== undefined) values.set('page', String(page))
  return values
}
export const reportApi = {
  async get(tenant: string, filters: ReportFilters, page: number) {
    const body = await request(`/api/v1/reports/?${params(filters, page)}`, {
      headers: { 'X-Tenant-Context': tenant },
    })
    if (filters.kind === 'summary')
      return { kind: 'summary' as const, data: summarySchema.parse(body) }
    if (filters.kind === 'reservations')
      return {
        kind: 'reservations' as const,
        data: pageSchema.extend({ results: z.array(reservationSchema) }).parse(body),
      }
    return {
      kind: 'payments' as const,
      data: pageSchema.extend({ results: z.array(paymentSchema) }).parse(body),
    }
  },
  async download(tenant: string, filters: ReportFilters, signal: AbortSignal) {
    let response: Response
    try {
      response = await fetch(publicUrl(`/api/v1/reports/export/?${params(filters)}`), {
        credentials: 'same-origin',
        headers: { 'X-Tenant-Context': tenant },
        signal: AbortSignal.any([signal, AbortSignal.timeout(30000)]),
      })
    } catch {
      throw new ApiError(
        0,
        'No se pudo descargar el archivo. Comprueba tu conexión e intenta nuevamente.',
      )
    }
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => null)
      const parsed = z
        .object({ error: z.object({ details: z.union([z.string(), z.array(z.string())]) }) })
        .safeParse(body)
      throw new ApiError(
        response.status,
        parsed.success
          ? Array.isArray(parsed.data.error.details)
            ? parsed.data.error.details.join(' ')
            : parsed.data.error.details
          : 'No se pudo exportar. Revisa los filtros y tu empresa activa.',
      )
    }
    if (!response.headers.get('Content-Type')?.startsWith('text/csv'))
      throw new ApiError(0, 'El servidor no entregó un archivo CSV válido.')
    return response.blob()
  },
}
