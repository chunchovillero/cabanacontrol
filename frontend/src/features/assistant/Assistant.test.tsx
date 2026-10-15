import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { AssistantPage } from './AssistantPage'
import { answerSchema, assistantApi } from './api'
import { VoiceRecorder } from './VoiceRecorder'

vi.mock('@/features/auth/TenantAccess', () => ({
  useTenantContext: () => ({
    tenant: {
      id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      name: 'Ficticia',
      role: 'staff',
      timezone: 'America/Santiago',
      currency: 'CLP',
    },
  }),
}))
afterEach(() => vi.unstubAllGlobals())

function mount(element = <AssistantPage />) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{element}</MemoryRouter>
    </QueryClientProvider>,
  )
}

it('exige revisión humana, invalida revisión al editar y limita configuración de staff', async () => {
  vi.spyOn(assistantApi, 'capabilities').mockResolvedValue({
    ready: true,
    enabled: true,
    simulated: true,
    voice_enabled: false,
    settings: {
      enabled: true,
      voice_enabled: false,
      daily_requests: 50,
      daily_tokens: 100000,
      daily_audio_seconds: 600,
      daily_budget_usd: '1.0000',
    },
  })
  vi.spyOn(assistantApi, 'message').mockResolvedValue({
    context: 'signed',
    results: [{ tool: 'clarify', data: { messages: ['Indica el año.'] } }],
  })
  mount()
  await screen.findByText(/Proveedor simulado/)
  expect(screen.queryByRole('button', { name: 'Desactivar IA' })).not.toBeInTheDocument()
  const text = screen.getByLabelText('Texto revisado para analizar')
  fireEvent.change(text, { target: { value: '2 personas' } })
  const send = screen.getByRole('button', { name: 'Consultar asistente' })
  expect(send).toBeDisabled()
  const reviewed = screen.getByRole('checkbox')
  fireEvent.click(reviewed)
  expect(send).toBeEnabled()
  fireEvent.change(text, { target: { value: '3 personas' } })
  expect(send).toBeDisabled()
  fireEvent.click(reviewed)
  fireEvent.click(send)
  await screen.findByText('Indica el año.')
  expect(assistantApi.message).toHaveBeenCalledWith(
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    '3 personas',
    '',
  )
  fireEvent.click(screen.getByRole('button', { name: 'Limpiar conversación' }))
  await waitFor(() => expect(screen.queryByText('Indica el año.')).not.toBeInTheDocument())
})

it('rechaza enlaces externos y herramientas de escritura en las tarjetas', () => {
  for (const url of ['https://evil.invalid', '//evil.invalid', '/reservas/../../secreto']) {
    expect(
      answerSchema.safeParse({
        context: '',
        results: [{ tool: 'list_arrivals', data: { items: [{ url }] } }],
      }).success,
    ).toBe(false)
  }
  expect(
    answerSchema.safeParse({ context: '', results: [{ tool: 'confirm_reservation', data: {} }] })
      .success,
  ).toBe(false)
})

it('ofrece texto manual cuando el navegador no tiene micrófono', () => {
  vi.stubGlobal('MediaRecorder', undefined)
  mount(<VoiceRecorder tenant="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" onText={() => undefined} />)
  expect(screen.getByText(/Tu navegador no permite dictado/)).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Enviar a transcribir' })).not.toBeInTheDocument()
})
