import { submitLogin } from './login'
import { readFile } from 'node:fs/promises'
import { expect, test, type Page } from '@playwright/test'
import { localHold } from '../src/features/reservations/dates'

const tenant = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
async function login(page: Page, prefix: string, variant: string) {
  await page.goto('/ingresar')
  await page.getByLabel('Correo electrónico').fill(`e2e-${prefix}-${variant}@example.invalid`)
  await page.getByLabel('Contraseña', { exact: true }).fill('E2E-fictional-passphrase-2026!')
  await submitLogin(page)
  await page.getByRole('button', { name: 'Seleccionar Empresa ficticia A' }).click()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
    'Empresa ficticia A',
  )
}
async function write(page: Page, url: string, data: unknown) {
  const csrf = await (await page.request.get('/api/v1/auth/csrf/')).json()
  const response = await page.request.post(url, {
    data,
    headers: { 'X-CSRFToken': csrf.csrf_token, 'X-Tenant-Context': tenant },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}
async function download(page: Page) {
  const event = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Descargar CSV', exact: true }).click()
  const file = await event
  expect(file.suggestedFilename()).toMatch(/^cabanacontrol-.*\.csv$/)
  expect(await file.failure()).toBeNull()
  return readFile((await file.path())!, 'utf8')
}
test('staff concilia reportes, exporta todas las páginas, canceladas y CSV protegido', async ({
  page,
  browser,
}, info) => {
  test.setTimeout(180000)
  await login(page, 'report-owner', info.project.name)
  const suffix = `${info.project.name}-${Date.now()}`
  const name = `=1+2; Cabaña ficticia reporte ${suffix}`
  const property = await write(page, '/api/v1/properties/', {
    name,
    code: `R-${suffix}`.toUpperCase(),
    capacity: 4,
    base_rate: '50000.00',
    check_in_time: '15:00',
    check_out_time: '11:00',
    description: '',
    address: '',
  })
  const guest = await write(page, '/api/v1/guests/', {
    first_name: 'Persona ficticia reportes',
    last_name: suffix,
    document_type: 'passport',
    document_number: 'FAKE-REPORTS',
    phone: '',
    email: '',
    notes: 'Nota ficticia confidencial',
  })
  const start = new Date(Date.now() + 86400000).toISOString().slice(0, 10)
  const end = new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 10)
  const data = {
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
  }
  const booked = await write(page, '/api/v1/reservations/', data)
  const paidAt = new Date().toISOString()
  await write(page, `/api/v1/reservations/${booked.id}/payments/`, {
    amount: '40000.10',
    paid_at: paidAt,
    method: 'cash',
    reference: '',
    request_id: crypto.randomUUID(),
  })
  const cancelled = await write(page, '/api/v1/reservations/', {
    ...data,
    status: 'pending',
    total_amount: '20.00',
    check_in: end,
    check_out: new Date(Date.now() + 4 * 86400000).toISOString().slice(0, 10),
    hold_until: new Date(Date.now() + 3600000).toISOString(),
  })
  await write(page, `/api/v1/reservations/${cancelled.id}/payments/`, {
    amount: '30.00',
    paid_at: new Date().toISOString(),
    method: 'transfer',
    reference: '',
    request_id: crypto.randomUUID(),
  })
  await write(page, `/api/v1/reservations/${cancelled.id}/cancel/`, {
    reason: 'Cancelación ficticia',
  })
  for (let i = 0; i < 25; i++)
    await write(page, '/api/v1/reservations/', { ...data, status: 'draft', total_amount: '0.00' })
  const context = await browser.newContext({
    baseURL: 'http://localhost:15174',
    viewport: page.viewportSize()!,
  })
  const staff = await context.newPage()
  try {
    await login(staff, 'report-staff', info.project.name)
    await staff.goto('/reportes')
    await expect(staff.getByRole('heading', { name: 'Reportes y exportaciones' })).toBeVisible()
    await staff.getByLabel('Buscar cabaña', { exact: true }).fill(name)
    await expect(staff.getByLabel('Cabaña', { exact: true }).locator('option')).toHaveCount(2)
    await staff.getByLabel('Cabaña', { exact: true }).selectOption(property.id)
    await staff
      .getByLabel('Desde', { exact: true })
      .fill(localHold(paidAt, 'America/Santiago').slice(0, 10))
    await staff
      .getByLabel('Hasta (exclusiva)')
      .fill(new Date(Date.now() + 5 * 86400000).toISOString().slice(0, 10))
    await staff.getByRole('button', { name: 'Aplicar periodo' }).click()
    await expect(staff.locator('dl').filter({ hasText: 'Cobrado' })).toContainText('40.030,10')
    await expect(staff.locator('dl').filter({ hasText: 'Cobrado' })).toContainText('60.000,15')
    const summary = await download(staff)
    expect(summary).toContain('"40030.10";"100000.25";"60000.15";"10.00"')
    await staff.getByLabel('Reporte', { exact: true }).selectOption('reservations')
    await expect(staff.getByText('27 registros · Página 1')).toBeVisible()
    await staff.getByRole('button', { name: 'Página siguiente' }).click()
    await expect(staff.getByText('27 registros · Página 2')).toBeVisible()
    const csv = await download(staff)
    expect(csv.split('\r\n').filter(Boolean)).toHaveLength(28)
    expect(csv).toContain(`"'${name}"`)
    expect(csv).toContain(cancelled.id)
    expect(csv).toContain(booked.id)
    expect(csv).not.toContain('Persona ficticia reportes')
    expect(csv).not.toContain('FAKE-REPORTS')
    expect(csv).not.toContain('Nota ficticia confidencial')
    await staff.getByLabel('Estado de reserva').selectOption('cancelled')
    await expect(staff.getByText('1 registros · Página 1')).toBeVisible()
    const cancelledCsv = await download(staff)
    expect(cancelledCsv).toContain(cancelled.id)
    expect(cancelledCsv).not.toContain(booked.id)
    await staff.screenshot({
      path: `../docs/screenshots/phase7-reports-${info.project.name}.png`,
      fullPage: true,
    })
    expect(
      await staff.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBeTruthy()
    await staff.getByLabel('Reporte', { exact: true }).selectOption('payments')
    await expect(staff.getByText('2 registros · Página 1')).toBeVisible()
    const payments = await download(staff)
    expect(payments).toContain('"40000.10"')
    expect(payments).toContain('"30.00"')
    await page.goto('/')
    await page.getByRole('button', { name: 'Seleccionar Empresa compartida ficticia' }).click()
    await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
      'Empresa compartida ficticia',
    )
    const response = await page.request.get(
      `/api/v1/reports/export/?from=${start}&to=${end}&kind=reservations&property_id=${property.id}`,
      { headers: { 'X-Tenant-Context': 'cccccccc-cccc-4ccc-8ccc-cccccccccccc' } },
    )
    expect(response.status()).toBe(404)
  } finally {
    await context.close()
  }
})
