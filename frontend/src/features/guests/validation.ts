import { z } from 'zod'

export function normalizeRut(value: string): string | null {
  const input = value.trim()
  if (!/^(?:[0-9]{1,8}|[0-9]{1,2}(?:\.[0-9]{3}){2}|[0-9]{1,3}\.[0-9]{3})-?[0-9Kk]$/.test(input))
    return null
  const compact = input.replace(/[.-]/g, '').toUpperCase()
  const body = String(Number(compact.slice(0, -1)))
  if (body === '0') return null
  const total = [...body]
    .reverse()
    .reduce((sum, digit, index) => sum + Number(digit) * (2 + (index % 6)), 0)
  const remainder = 11 - (total % 11)
  const expected = remainder === 11 ? '0' : remainder === 10 ? 'K' : String(remainder)
  return compact.at(-1) === expected ? `${body}-${expected}` : null
}

export const guestFormSchema = z
  .object({
    first_name: z.string().trim().min(1, 'Ingresa los nombres.').max(150),
    last_name: z.string().trim().min(1, 'Ingresa los apellidos.').max(150),
    document_type: z.enum(['rut', 'passport', 'other']),
    document_number: z.string().trim().min(1, 'Ingresa el documento.').max(40),
    phone: z
      .string()
      .trim()
      .max(32)
      .refine(
        (value) =>
          !value ||
          (/^\+?[0-9 ()-]+$/.test(value) &&
            value.replace(/[^0-9]/g, '').length >= 7 &&
            value.replace(/[^0-9]/g, '').length <= 15),
        'Ingresa un teléfono válido.',
      ),
    email: z
      .string()
      .trim()
      .max(254)
      .refine((value) => !value || z.email().safeParse(value).success, 'Ingresa un correo válido.'),
    notes: z.string().max(2000),
  })
  .superRefine((data, context) => {
    if (data.document_type === 'rut' && !normalizeRut(data.document_number)) {
      context.addIssue({
        code: 'custom',
        path: ['document_number'],
        message: 'El RUT no es válido. Revisa el número y su dígito verificador.',
      })
    }
    if (
      data.document_type !== 'rut' &&
      (!/^[\p{L}\p{N} .\-/]+$/u.test(data.document_number) ||
        !/[\p{L}\p{N}]/u.test(data.document_number))
    ) {
      context.addIssue({
        code: 'custom',
        path: ['document_number'],
        message: 'El documento contiene caracteres no permitidos.',
      })
    }
  })
