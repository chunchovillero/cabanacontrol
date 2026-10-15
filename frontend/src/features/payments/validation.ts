import { z } from 'zod'

export const paymentFormSchema = z.object({
  amount: z
    .string()
    .regex(/^\d{1,12}(?:[.,]\d{1,2})?$/, 'Ingresa un monto positivo con hasta dos decimales.')
    .refine((value) => /[1-9]/.test(value), 'El abono debe ser mayor que cero.'),
  paid_at: z.string().min(1, 'Indica fecha y hora del pago.'),
  method: z.enum(['cash', 'transfer', 'card', 'other']),
  reference: z.string().trim().max(150),
})
export function validateReceipt(file: File) {
  if (file.size > 5 * 1024 * 1024) throw new Error('El comprobante no puede superar 5 MB.')
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type))
    throw new Error('Usa un comprobante JPG, PNG o WebP.')
}
