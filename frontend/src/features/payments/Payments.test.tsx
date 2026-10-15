import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from '@/app/App'
import { api, ApiError, type Session } from '@/lib/api'
import { reservationApi, type Reservation } from '@/features/reservations/api'
import { paymentApi, type Payment } from './api'
import { paymentFormSchema, validateReceipt } from './validation'

const tenant = {
  id: '22222222-2222-4222-8222-222222222222',
  name: 'Empresa ficticia',
  role: 'staff' as const,
  timezone: 'America/Santiago',
  currency: 'CLP',
}
const session: Session = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'staff@example.invalid',
  name: 'Colaborador ficticio',
  is_platform_admin: false,
  active_tenant: tenant,
}
const reservation: Reservation = {
  id: '44444444-4444-4444-8444-444444444444',
  property_id: '55555555-5555-4555-8555-555555555555',
  property_name: 'Cabaña ficticia',
  primary_guest_id: '33333333-3333-4333-8333-333333333333',
  guest: {
    id: '33333333-3333-4333-8333-333333333333',
    first_name: 'Persona ficticia',
    last_name: 'Prueba',
    document_type: 'passport',
    document_masked: '••••TEST',
    active: true,
  },
  check_in: '2099-01-10',
  check_out: '2099-01-12',
  adults: 2,
  children: 0,
  status: 'confirmed',
  hold_until: null,
  hold_active: false,
  total_amount: '100.25',
  received_amount: '0.00',
  balance: '100.25',
  payment_state: 'unpaid',
  currency: 'CLP',
  source: 'direct',
  notes: '',
  cancel_reason: '',
  created_at: '2026-10-13T00:00:00Z',
  updated_at: '2026-10-13T00:00:00Z',
}
const payment: Payment = {
  id: '66666666-6666-4666-8666-666666666666',
  reservation_id: reservation.id,
  request_id: '77777777-7777-4777-8777-777777777777',
  amount: '60.10',
  currency: 'CLP',
  paid_at: '2026-10-13T15:00:00Z',
  method: 'transfer',
  reference: 'Referencia ficticia',
  status: 'recorded',
  receipt_url: null,
  recorded_by_id: session.id,
  voided_by_id: null,
  void_reason: '',
  voided_at: null,
  created_at: '2026-10-13T15:01:00Z',
  updated_at: '2026-10-13T15:01:00Z',
}
const clients: QueryClient[] = []
beforeEach(() => {
  vi.spyOn(api, 'me').mockResolvedValue(session)
  vi.spyOn(reservationApi, 'get').mockResolvedValue(reservation)
  vi.spyOn(paymentApi, 'list').mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  })
})
afterEach(() => {
  clients.forEach((client) => client.clear())
  clients.length = 0
})
function mount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  })
  clients.push(client)
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/reservas/${reservation.id}`]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Validación de pagos', () => {
  it.each(['0', '0,00', '-1', 'NaN', '1.234', '1000000000000.00'])(
    'rechaza importe %s',
    (amount) => {
      expect(
        paymentFormSchema.safeParse({
          amount,
          paid_at: '2026-10-13T12:00',
          method: 'transfer',
          reference: '',
        }).success,
      ).toBe(false)
    },
  )
  it('acepta decimal chileno sin convertir a float', () => {
    expect(
      paymentFormSchema.safeParse({
        amount: '60,10',
        paid_at: '2026-10-13T12:00',
        method: 'transfer',
        reference: '',
      }).success,
    ).toBe(true)
  })
  it('valida formato y tamaño de comprobantes', () => {
    expect(() =>
      validateReceipt(new File(['test'], 'x.pdf', { type: 'application/pdf' })),
    ).toThrow()
    expect(() =>
      validateReceipt(
        new File([new Uint8Array(5 * 1024 * 1024 + 1)], 'x.png', { type: 'image/png' }),
      ),
    ).toThrow()
  })
})

describe('Pagos de reserva', () => {
  it('registra texto decimal y reutiliza solicitud en un reintento', async () => {
    vi.spyOn(paymentApi, 'record')
      .mockRejectedValueOnce(new ApiError(0, 'No pudimos confirmar el resultado.'))
      .mockResolvedValue(payment)
    mount()
    await userEvent.click(await screen.findByRole('button', { name: 'Registrar abono' }))
    await userEvent.type(screen.getByLabelText('Monto del abono (CLP)'), '60,10')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar abono' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('confirmar el resultado')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar abono' }))
    expect(await screen.findByText('Abono registrado.')).toBeVisible()
    const calls = vi.mocked(paymentApi.record).mock.calls
    expect(calls[0][2].amount).toBe('60.10')
    expect(calls[0][2].request_id).toBe(calls[1][2].request_id)
    expect(calls[0][2].paid_at).toMatch(/Z$/)
  })
  it('permite anular a staff con motivo y conserva el historial', async () => {
    vi.spyOn(paymentApi, 'list').mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [payment],
    })
    vi.spyOn(paymentApi, 'void').mockResolvedValue({
      ...payment,
      status: 'voided',
      void_reason: 'Error ficticio',
      voided_by_id: session.id,
      voided_at: '2026-10-14T00:00:00Z',
    })
    mount()
    await userEvent.click(await screen.findByRole('button', { name: 'Anular pago' }))
    const dialog = screen.getByRole('dialog', { name: 'Anular pago' })
    expect(within(dialog).getByRole('button', { name: 'Confirmar anulación' })).toBeDisabled()
    await userEvent.type(within(dialog).getByLabelText('Motivo de anulación'), 'Error ficticio')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Confirmar anulación' }))
    expect(await screen.findByText('Pago anulado; el historial se conserva.')).toBeVisible()
    expect(paymentApi.void).toHaveBeenCalledWith(tenant.id, payment.id, 'Error ficticio')
  })
  it('cancelada muestra saldo a favor y no permite abonos nuevos', async () => {
    vi.spyOn(reservationApi, 'get').mockResolvedValue({
      ...reservation,
      status: 'cancelled',
      received_amount: '120.35',
      balance: '-20.10',
      payment_state: 'credit',
    })
    mount()
    await screen.findByRole('heading', { name: 'Pagos y abonos' })
    expect(screen.queryByRole('button', { name: 'Registrar abono' })).not.toBeInTheDocument()
    expect(screen.getByText('$ 20,10', { exact: true })).toBeVisible()
    expect(screen.getByText(/no se generan devoluciones/)).toBeVisible()
  })
  it('fallo de comprobante no vuelve a registrar el pago', async () => {
    vi.spyOn(paymentApi, 'record').mockResolvedValue(payment)
    vi.spyOn(paymentApi, 'receipt').mockRejectedValue(new ApiError(400, 'Comprobante inválido.'))
    mount()
    await userEvent.click(await screen.findByRole('button', { name: 'Registrar abono' }))
    await userEvent.type(screen.getByLabelText('Monto del abono (CLP)'), '60.10')
    await userEvent.upload(
      screen.getByLabelText('Comprobante (opcional)'),
      new File(['fictional'], 'fake.png', { type: 'image/png' }),
    )
    await userEvent.click(screen.getByRole('button', { name: 'Guardar abono' }))
    expect(await screen.findByText(/El abono está registrado/)).toBeVisible()
    expect(paymentApi.record).toHaveBeenCalledTimes(1)
    expect(paymentApi.receipt).toHaveBeenCalledWith(tenant.id, payment.id, expect.any(File))
  })
})
