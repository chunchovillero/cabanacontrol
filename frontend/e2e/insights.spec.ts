import { submitLogin } from './login'
import { expect, test, type Page } from '@playwright/test'
import { localHold } from '../src/features/reservations/dates'

const tenant = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
async function write(page: Page, url: string, data: unknown, method = 'POST') {
  const token = await (await page.request.get('/api/v1/auth/csrf/')).json()
  const response = await page.request.fetch(url, {
    method,
    data,
    headers: { 'X-CSRFToken': token.csrf_token, 'X-Tenant-Context': tenant },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}
test('calendario mensual/semanal, bloqueos, cifras y cambio de empresa', async ({ page }, info) => {
  test.setTimeout(120000)
  await page.goto('/ingresar')
  await page
    .getByLabel('Correo electrónico')
    .fill(`e2e-insights-${info.project.name}@example.invalid`)
  await page.getByLabel('Contraseña', { exact: true }).fill('E2E-fictional-passphrase-2026!')
  await submitLogin(page)
  await page.getByRole('button', { name: 'Seleccionar Empresa ficticia A' }).click()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toBeVisible()
  const suffix = `${info.project.name}-${Date.now()}`
  const name = `Cabaña ficticia calendario ${suffix}`
  const property = await write(page, '/api/v1/properties/', {
    name,
    code: `I-${suffix}`.toUpperCase(),
    capacity: 4,
    base_rate: '50000.00',
    check_in_time: '15:00',
    check_out_time: '11:00',
    description: '',
    address: '',
  })
  const guest = await write(page, '/api/v1/guests/', {
    first_name: 'Persona ficticia indicadores',
    last_name: suffix,
    document_type: 'passport',
    document_number: 'FAKE-INSIGHTS',
    phone: '',
    email: '',
    notes: 'Nota privada ficticia',
  })
  const start = new Date(Date.now() + 86400000).toISOString().slice(0, 10)
  const end = new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 10)
  const blockEnd = new Date(Date.now() + 4 * 86400000).toISOString().slice(0, 10)
  const reservation = await write(page, '/api/v1/reservations/', {
    property_id: property.id,
    primary_guest_id: guest.id,
    check_in: start,
    check_out: end,
    adults: 2,
    children: 0,
    total_amount: '100000.25',
    source: 'direct',
    status: 'confirmed',
    notes: '',
  })
  const paidAt = new Date().toISOString()
  await write(page, `/api/v1/reservations/${reservation.id}/payments/`, {
    amount: '40000.10',
    paid_at: paidAt,
    method: 'cash',
    reference: '',
    request_id: crypto.randomUUID(),
  })
  await write(page, '/api/v1/availability-blocks/', {
    property_id: property.id,
    start_date: end,
    end_date: blockEnd,
    reason: 'maintenance',
    notes: '',
  })
  await page.goto('/calendario')
  await expect(page.getByRole('heading', { name: 'Calendario de reservas' })).toBeVisible()
  await page.getByLabel('Buscar cabaña', { exact: true }).fill(name)
  await expect(page.getByLabel('Cabaña', { exact: true }).locator('option')).toHaveCount(2)
  await page.getByLabel('Cabaña', { exact: true }).selectOption(property.id)
  await expect(
    page.locator('.cabin-calendar').getByRole('link', { name: new RegExp(name) }),
  ).toHaveCount(2)
  await expect(page.locator('.calendar-event').filter({ hasText: 'Confirmada' })).toHaveCSS(
    'background-color',
    'rgb(22, 101, 52)',
  )
  await expect(page.locator('.calendar-event').filter({ hasText: 'Mantenimiento' })).toHaveCSS(
    'background-color',
    'rgb(55, 65, 81)',
  )
  await expect(page.locator('main')).not.toContainText('Persona ficticia indicadores')
  await expect(page.locator('main')).not.toContainText('Nota privada ficticia')
  await page
    .locator('.cabin-calendar')
    .getByRole('link', { name: /Confirmada/ })
    .click()
  await expect(page).toHaveURL(new RegExp(`/reservas/${reservation.id}$`))
  await page.goto('/calendario')
  await page.getByLabel('Buscar cabaña', { exact: true }).fill(name)
  await expect(page.getByLabel('Cabaña', { exact: true }).locator('option')).toHaveCount(2)
  await page.getByLabel('Cabaña', { exact: true }).selectOption(property.id)
  await page.getByRole('tab', { name: /Vista del semana/i }).click()
  await expect(page.getByRole('tab', { name: /Vista del semana/i })).toBeVisible()
  await page.getByLabel('Mostrar', { exact: true }).selectOption('block')
  await expect(page.locator('ul').getByRole('link', { name: /Mantenimiento/ })).toBeVisible()
  await page.screenshot({
    path: `../docs/screenshots/phase6-calendar-${info.project.name}.png`,
    fullPage: true,
  })
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy()
  await page.goto('/panel')
  await page.getByLabel('Buscar cabaña', { exact: true }).fill(name)
  await expect(page.getByLabel('Cabaña', { exact: true }).locator('option')).toHaveCount(2)
  await page.getByLabel('Cabaña', { exact: true }).selectOption(property.id)
  await page
    .getByLabel('Desde', { exact: true })
    .fill(localHold(paidAt, 'America/Santiago').slice(0, 10))
  await page.getByLabel('Hasta (exclusiva)').fill(blockEnd)
  await page.getByRole('button', { name: 'Actualizar periodo' }).click()
  await expect(page.locator('dl').filter({ hasText: 'Cobrado' })).toContainText('40.000,10')
  await expect(page.locator('dl').filter({ hasText: 'Cobrado' })).toContainText('60.000,15')
  await expect(page.locator('main')).toContainText('2 noches reservadas')
  await page.screenshot({
    path: `../docs/screenshots/phase6-dashboard-${info.project.name}.png`,
    fullPage: true,
  })
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy()
  await page.goto('/')
  await page.getByRole('button', { name: 'Seleccionar Empresa compartida ficticia' }).click()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
    'Empresa compartida ficticia',
  )
  const forbidden = await page.request.get(
    `/api/v1/calendar/?from=${start}&to=${end}&property_id=${property.id}`,
  )
  expect(forbidden.status()).toBe(404)
  await page.goto('/calendario')
  await expect(page.getByText('No hay eventos para estos filtros.')).toBeVisible()
  await expect(page.locator('main')).not.toContainText(name)
})
