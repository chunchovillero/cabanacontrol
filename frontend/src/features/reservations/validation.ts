import { z } from 'zod'

export const reservationFormSchema = z
  .object({
    property_id: z.string().uuid('Selecciona una cabaña.'),
    primary_guest_id: z.string().uuid('Selecciona un huésped.'),
    check_in: z.iso.date('Indica una fecha de entrada válida.'),
    check_out: z.iso.date('Indica una fecha de salida válida.'),
    adults: z.number().int().min(1, 'Debe haber al menos un adulto.').max(32767),
    children: z.number().int().min(0).max(32767),
    total_amount: z
      .string()
      .regex(/^\d{1,12}(?:\.\d{1,2})?$/, 'Ingresa un monto no negativo, con hasta dos decimales.'),
    source: z.enum(['direct', 'phone', 'whatsapp', 'other']),
    notes: z.string().max(2000),
    status: z.enum(['draft', 'pending', 'confirmed']),
    hold_until: z.string(),
  })
  .superRefine((value, ctx) => {
    if (value.check_out <= value.check_in)
      ctx.addIssue({
        code: 'custom',
        path: ['check_out'],
        message: 'La salida debe ser posterior a la entrada.',
      })
    if (value.status === 'pending' && !value.hold_until)
      ctx.addIssue({
        code: 'custom',
        path: ['hold_until'],
        message: 'Indica hasta cuándo retener las fechas.',
      })
  })
export const blockFormSchema = z
  .object({
    property_id: z.string().uuid('Selecciona una cabaña.'),
    start_date: z.iso.date(),
    end_date: z.iso.date(),
    reason: z.enum(['maintenance', 'owner_use', 'other']),
    notes: z.string().max(2000),
  })
  .refine((value) => value.end_date > value.start_date, {
    path: ['end_date'],
    message: 'El fin debe ser posterior al inicio.',
  })
