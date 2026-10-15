import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { HealthPage } from './HealthPage'

describe('Conexión de servicios', () => {
  it('muestra conexión verificada por backend y PostgreSQL', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok', database: 'ok' })),
    )
    render(<HealthPage />)
    expect(
      await screen.findByText('Backend y PostgreSQL conectados correctamente.'),
    ).toBeInTheDocument()
  })

  it('muestra error cuando la API devuelve 503', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}', { status: 503 }))
    render(<HealthPage />)
    expect(await screen.findByText(/No se pudo verificar/)).toBeInTheDocument()
  })

  it('rechaza un cuerpo exitoso que no confirma PostgreSQL', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ status: 'ok' })))
    render(<HealthPage />)
    expect(await screen.findByText(/No se pudo verificar/)).toBeInTheDocument()
  })
})
