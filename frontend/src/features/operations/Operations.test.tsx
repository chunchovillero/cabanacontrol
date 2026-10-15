import { expect, it } from 'vitest'
import { whatsappLink } from './WhatsAppComposer'

it('crea enlace oficial codificando texto y exigiendo prefijo internacional explícito', () => {
  const url = new URL(whatsappLink('+999 000-0000', 'Texto ficticio & revisión\nSin envío')!)
  expect(url.origin).toBe('https://wa.me')
  expect(url.pathname).toBe('/9990000000')
  expect(url.searchParams.get('text')).toBe('Texto ficticio & revisión\nSin envío')
})
it('rechaza teléfonos ambiguos, enlaces inyectados y mensajes demasiado largos', () => {
  for (const phone of ['', '9990000000', '+000000000', 'https://malicious.invalid', '+999<script>'])
    expect(whatsappLink(phone, 'Ficticio')).toBeNull()
  expect(whatsappLink('+9990000000', 'x'.repeat(2001))).toBeNull()
})
