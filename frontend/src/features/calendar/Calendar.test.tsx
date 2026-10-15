import { expect, it } from 'vitest'
import { calendarInput } from './CalendarPage'
import type { CalendarEvent } from './api'

const event: CalendarEvent = {
  id: 'reservation:11111111-1111-4111-8111-111111111111',
  kind: 'reservation',
  entity_id: '11111111-1111-4111-8111-111111111111',
  property_id: '22222222-2222-4222-8222-222222222222',
  property_name: 'Cabaña ficticia',
  property_active: true,
  title: 'Cabaña ficticia · Confirmada',
  start: '2026-09-05',
  end: '2026-09-07',
  status: 'confirmed',
  blocks_inventory: true,
  url: '/reservas/11111111-1111-4111-8111-111111111111',
}
it('preserva fechas sin horas durante el cambio de horario chileno y salida exclusiva', () => {
  const input = calendarInput(event)
  expect(input).toMatchObject({
    start: '2026-09-05',
    end: '2026-09-07',
    allDay: true,
    url: event.url,
  })
  expect(input).not.toHaveProperty('property_id')
})
it('distingue bloqueos de estados de reserva', () => {
  const block = calendarInput({ ...event, kind: 'block', status: 'maintenance' })
  expect(block.color).not.toBe(calendarInput(event).color)
  expect(calendarInput({ ...event, status: 'cancelled' }).color).not.toBe(
    calendarInput(event).color,
  )
})
