import { z } from 'zod'
import { write, request } from '@/lib/api'

export const methodLabels = {
  cash: 'Efectivo',
  transfer: 'Transferencia',
  card: 'Tarjeta',
  other: 'Otro',
}
export const paymentLabels = {
  unpaid: 'Sin abonos',
  partial: 'Pago parcial',
  paid: 'Pagada',
  credit: 'Saldo a favor',
}
const paymentSchema = z.object({
  id: z.string().uuid(),
  reservation_id: z.string().uuid(),
  request_id: z.string().uuid(),
  amount: z.string(),
  currency: z.string(),
  paid_at: z.string(),
  method: z.enum(['cash', 'transfer', 'card', 'other']),
  reference: z.string(),
  status: z.enum(['recorded', 'voided']),
  receipt_url: z.string().startsWith('/api/v1/payments/').nullable(),
  recorded_by_id: z.string().uuid(),
  voided_by_id: z.string().uuid().nullable(),
  void_reason: z.string(),
  voided_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type Payment = z.infer<typeof paymentSchema>
export type PaymentInput = Pick<
  Payment,
  'request_id' | 'amount' | 'paid_at' | 'method' | 'reference'
>
const resultSchema = z.object({
  count: z.number(),
  next: z.string().nullable(),
  previous: z.string().nullable(),
  results: z.array(paymentSchema),
})
const headers = (tenant: string) => ({ 'X-Tenant-Context': tenant })
export const paymentApi = {
  async list(tenant: string, reservation: string, page: number) {
    return resultSchema.parse(
      await request(`/api/v1/reservations/${reservation}/payments/?page=${page}`, {
        headers: headers(tenant),
      }),
    )
  },
  async record(tenant: string, reservation: string, data: PaymentInput) {
    return paymentSchema.parse(
      await write(`/api/v1/reservations/${reservation}/payments/`, data, 'POST', headers(tenant)),
    )
  },
  async void(tenant: string, id: string, reason: string) {
    return paymentSchema.parse(
      await write(`/api/v1/payments/${id}/void/`, { reason }, 'POST', headers(tenant)),
    )
  },
  async receipt(tenant: string, id: string, file: File) {
    const data = new FormData()
    data.set('file', file)
    return paymentSchema.parse(
      await write(`/api/v1/payments/${id}/receipt/`, data, 'POST', headers(tenant)),
    )
  },
}
