import { describe, expect, it, vi } from 'vitest'
import { guestApi } from './api'

describe('Privacidad de la búsqueda', () => {
  it('envía documentos en JSON y no en URL, con sesión, contexto y CSRF', async () => {
    const fetch = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: 'masked-csrf' })))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ count: 0, page: 1, has_next: false, has_previous: false, results: [] }),
        ),
      )
    await guestApi.search('22222222-2222-4222-8222-222222222222', '12.345.678-5', 'true', 1)
    expect(fetch.mock.calls[1][0]).toBe('/api/v1/guests/search/')
    expect(fetch.mock.calls[1][1]).toMatchObject({
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': 'masked-csrf',
        'X-Tenant-Context': '22222222-2222-4222-8222-222222222222',
      },
      body: JSON.stringify({ query: '12.345.678-5', page: 1, active: true }),
    })
  })
})
