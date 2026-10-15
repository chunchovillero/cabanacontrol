import { describe, expect, it, vi } from 'vitest'
import { api, ApiError } from './api'

function response(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), { status })
}

describe('Cliente de sesión y CSRF', () => {
  it('obtiene CSRF antes de escribir y usa cookies del mismo origen', async () => {
    const fetch = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(response({ csrf_token: 'masked-csrf-token' }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    await api.logout()
    expect(fetch.mock.calls[0][0]).toBe('/api/v1/auth/csrf/')
    expect(fetch.mock.calls[1][1]).toMatchObject({
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': 'masked-csrf-token' },
    })
  })

  it('reconoce sesión ausente sin ocultar errores de servidor', async () => {
    const fetch = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(response({}, 403))
      .mockResolvedValueOnce(response({}, 503))
    expect(await api.me()).toBeNull()
    await expect(api.me()).rejects.toBeInstanceOf(ApiError)
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('recorre páginas con rutas locales aunque next señale a un host externo', async () => {
    const fetch = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(response({ results: [], next: 'https://external.example.invalid/' }))
      .mockResolvedValueOnce(response({ results: [], next: null }))
    expect(await api.tenants()).toEqual([])
    expect(fetch.mock.calls[1][0]).toBe('/api/v1/tenants/?page=2')
  })

  it('informa fallos de red en español', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('socket'))
    await expect(api.me()).rejects.toThrow('No pudimos conectar con el servidor')
  })
})
