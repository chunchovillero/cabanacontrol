import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { expect, it, vi } from 'vitest'
import { WhatsAppConversation } from './WhatsAppPage'
import { whatsappApi } from './api'

const tenant = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
const id = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'
vi.mock('@/features/auth/TenantAccess', () => ({
  useTenantContext: () => ({
    tenant: {
      id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      role: 'staff',
      timezone: 'America/Santiago',
      currency: 'CLP',
    },
  }),
}))

const conversation = {
  id,
  contact_phone: '999000000002',
  last_inbound_at: new Date().toISOString(),
  revision: 1,
  expires_at: '2099-01-01T00:00:00Z',
  consent_granted: true,
  expired: false,
}

function mount() {
  vi.spyOn(whatsappApi, 'capabilities').mockResolvedValue({
    ready: true,
    enabled: true,
    simulated: true,
  })
  vi.spyOn(whatsappApi, 'conversation').mockResolvedValue(conversation)
  vi.spyOn(whatsappApi, 'messages').mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  })
  vi.spyOn(whatsappApi, 'templates').mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/whatsapp/${id}`]}>
        <Routes>
          <Route path="/whatsapp/:id" element={<WhatsAppConversation />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return client
}

it('nueva revisión conserva el texto escrito y exige volver a autorizar', async () => {
  const client = mount()
  await screen.findByText(/WhatsApp simulado/)
  const text = screen.getByLabelText('Respuesta para revisar')
  fireEvent.change(text, { target: { value: 'Respuesta ficticia en preparación' } })
  const send = screen.getByRole('button', { name: 'Autorizar envío de respuesta' })
  expect(send).toBeDisabled()
  fireEvent.click(
    screen.getByLabelText('Revisé destinatario, contenido y permiso. Autorizar esta respuesta.'),
  )
  expect(send).toBeEnabled()
  await act(async () => {
    client.setQueryData(['wa-conversation', tenant, id], { ...conversation, revision: 2 })
  })
  expect(text).toHaveValue('Respuesta ficticia en preparación')
  await waitFor(() => expect(send).toBeDisabled())
})

it('un fallo de transporte conserva request_id para el reintento y no envía al editar', async () => {
  mount()
  const sendApi = vi
    .spyOn(whatsappApi, 'send')
    .mockRejectedValue(new Error('Conexión incierta ficticia'))
  await screen.findByText(/WhatsApp simulado/)
  fireEvent.change(screen.getByLabelText('Respuesta para revisar'), {
    target: { value: 'Respuesta revisada' },
  })
  expect(sendApi).not.toHaveBeenCalled()
  fireEvent.click(
    screen.getByLabelText('Revisé destinatario, contenido y permiso. Autorizar esta respuesta.'),
  )
  fireEvent.click(screen.getByRole('button', { name: 'Autorizar envío de respuesta' }))
  await screen.findByText('Conexión incierta ficticia')
  fireEvent.click(screen.getByRole('button', { name: 'Autorizar envío de respuesta' }))
  await waitFor(() => expect(sendApi).toHaveBeenCalledTimes(2))
  expect(sendApi.mock.calls[0][1].request_id).toBe(sendApi.mock.calls[1][1].request_id)
})
