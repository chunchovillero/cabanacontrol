import { afterEach, expect, it, vi } from 'vitest'
import { reportApi, type ReportFilters } from './api'

const filters: ReportFilters = {
  start: '2026-10-01',
  end: '2026-11-01',
  property: '22222222-2222-4222-8222-222222222222',
  kind: 'reservations',
  status: 'cancelled',
}
afterEach(() => vi.unstubAllGlobals())
it('exporta mismos filtros sin page, con contexto autenticado y señal de cancelación', async () => {
  const fetcher = vi.fn().mockResolvedValue(
    new Response('\ufeff"Reserva"\r\n', {
      headers: { 'Content-Type': 'text/csv; charset=utf-8' },
    }),
  )
  vi.stubGlobal('fetch', fetcher)
  const blob = await reportApi.download('tenant-context', filters, new AbortController().signal)
  expect(blob.size).toBeGreaterThan(0)
  const [url, options] = fetcher.mock.calls[0]
  expect(String(url)).toContain('status=cancelled')
  expect(String(url)).toContain('property_id=22222222')
  expect(String(url)).not.toContain('page=')
  expect(options).toMatchObject({
    credentials: 'same-origin',
    headers: { 'X-Tenant-Context': 'tenant-context' },
  })
  expect(options.signal).toBeInstanceOf(AbortSignal)
})
it('rechaza error de permiso y no lo convierte en descarga', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ error: { details: 'Empresa no autorizada.' } }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      }),
    ),
  )
  await expect(reportApi.download('tenant', filters, new AbortController().signal)).rejects.toThrow(
    'Empresa no autorizada.',
  )
})
it('rechaza HTML accidental recibido como HTTP 200', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValue(
        new Response('<html>Ingresar</html>', { headers: { 'Content-Type': 'text/html' } }),
      ),
  )
  await expect(reportApi.download('tenant', filters, new AbortController().signal)).rejects.toThrow(
    'CSV válido',
  )
})

it('muestra instrucción de reducir filtros ante límite de filas', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { details: ['La exportación supera 5.000 filas. Reduce el periodo.'] },
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      ),
    ),
  )
  await expect(reportApi.download('tenant', filters, new AbortController().signal)).rejects.toThrow(
    'Reduce el periodo',
  )
})
