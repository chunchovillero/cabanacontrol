import { submitLogin } from './login'
import { expect, test, type Page } from '@playwright/test'

const tenant = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
async function login(page: Page, email: string) {
  await page.goto('/ingresar')
  await page.getByLabel('Correo electrónico').fill(email)
  await page.getByLabel('Contraseña', { exact: true }).fill('E2E-fictional-passphrase-2026!')
  await submitLogin(page)
  await page.getByRole('button', { name: 'Seleccionar Empresa ficticia A' }).click()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
    'Empresa ficticia A',
  )
}
async function write(page: Page, url: string, data: unknown, method = 'POST') {
  const token = await (await page.request.get('/api/v1/auth/csrf/')).json()
  return page.request.fetch(url, {
    method,
    data,
    headers: { 'X-CSRFToken': token.csrf_token, 'X-Tenant-Context': tenant },
  })
}

test('staff registra abonos exactos, sobrepago, comprobante y anulación con aislamiento', async ({
  page,
  browser,
}, info) => {
  test.setTimeout(120000)
  const suffix = `${info.project.name}-${Date.now()}`
  const name = `Cabaña ficticia pagos ${suffix}`
  await login(page, `e2e-payment-owner-${info.project.name}@example.invalid`)
  const propertyResponse = await write(page, '/api/v1/properties/', {
    name,
    code: `P-${suffix}`.toUpperCase(),
    capacity: 4,
    base_rate: '50000.00',
    check_in_time: '15:00',
    check_out_time: '11:00',
    description: '',
    address: '',
  })
  expect(propertyResponse.status()).toBe(201)
  const property = await propertyResponse.json()
  const guestResponse = await write(page, '/api/v1/guests/', {
    first_name: 'Persona ficticia de pagos',
    last_name: suffix,
    document_type: 'passport',
    document_number: 'E2E-FAKE-PAYMENT',
    phone: '',
    email: '',
    notes: 'Nota privada ficticia',
  })
  expect(guestResponse.status()).toBe(201)
  const guest = await guestResponse.json()
  const start = new Date(Date.now() + 10 * 86400000).toISOString().slice(0, 10)
  const end = new Date(Date.now() + 12 * 86400000).toISOString().slice(0, 10)
  const response = await write(page, '/api/v1/reservations/', {
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
  expect(response.status()).toBe(201)
  const reservation = await response.json()
  const context = await browser.newContext({
    baseURL: 'http://localhost:15174',
    viewport: page.viewportSize()!,
  })
  const staff = await context.newPage()
  try {
    await login(staff, `e2e-payment-staff-${info.project.name}@example.invalid`)
    await staff.goto(`/reservas/${reservation.id}`)
    async function record(amount: string, receipt = false) {
      await staff.getByRole('button', { name: 'Registrar abono', exact: true }).click()
      await staff.getByLabel('Monto del abono (CLP)', { exact: true }).fill(amount)
      await staff
        .getByLabel('Referencia de operación (opcional)', { exact: true })
        .fill('Referencia ficticia E2E')
      if (receipt)
        await staff.getByLabel('Comprobante (opcional)', { exact: true }).setInputFiles({
          name: 'synthetic-proof.png',
          mimeType: 'image/png',
          buffer: Buffer.from(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
            'base64',
          ),
        })
      await staff.getByRole('button', { name: 'Guardar abono', exact: true }).click()
      await expect(staff.getByText('Abono registrado.', { exact: true })).toBeVisible()
      await expect(staff.getByRole('button', { name: 'Guardar abono', exact: true })).toHaveCount(0)
    }
    await record('40000,10', true)
    const summary = staff
      .locator('dl')
      .filter({ has: staff.getByText('Recibido válido', { exact: true }) })
    await expect(summary).toContainText('$ 60.000,15')
    await record('60000.15')
    await expect(summary).toContainText('Pagada')
    await record('10000.10')
    await expect(summary).toContainText('Saldo a favor')
    await expect(summary).toContainText('$ 110.000,35')
    const first = staff
      .getByRole('article')
      .filter({ has: staff.getByRole('heading', { name: '$ 40.000,10', exact: true }) })
    const receipt = await first
      .getByRole('link', { name: 'Descargar comprobante' })
      .getAttribute('href')
    expect((await staff.request.get(receipt!)).status()).toBe(200)
    await first.getByRole('button', { name: 'Anular pago', exact: true }).click()
    const dialog = staff.getByRole('dialog', { name: 'Anular pago', exact: true })
    await expect(dialog.getByRole('button', { name: 'Confirmar anulación' })).toBeDisabled()
    await dialog.getByLabel('Motivo de anulación', { exact: true }).fill('Corrección ficticia E2E')
    await dialog.getByRole('button', { name: 'Confirmar anulación', exact: true }).click()
    await expect(first).toContainText('Anulado')
    await expect(summary).toContainText('$ 30.000')
    const download = await staff.request.get(receipt!)
    expect(download.status()).toBe(200)
    expect(download.headers()['content-disposition']).toContain('attachment')
    expect(download.headers()['cache-control']).toBe('no-store')
    const ledger = await (
      await staff.request.get(`/api/v1/reservations/${reservation.id}/payments/`)
    ).json()
    expect(ledger.count).toBe(3)
    expect(
      ledger.results.filter((item: { status: string }) => item.status === 'voided'),
    ).toHaveLength(1)
    const last = ledger.results.find((item: { amount: string }) => item.amount === '10000.10')
    const retry = await write(staff, `/api/v1/reservations/${reservation.id}/payments/`, {
      request_id: last.request_id,
      amount: last.amount,
      paid_at: last.paid_at,
      method: last.method,
      reference: last.reference,
    })
    expect(retry.status()).toBe(200)
    expect(
      (await (await staff.request.get(`/api/v1/reservations/${reservation.id}/payments/`)).json())
        .count,
    ).toBe(3)
    expect(
      (
        await write(
          page,
          `/api/v1/reservations/${reservation.id}/`,
          { total_amount: '50000.00' },
          'PATCH',
        )
      ).status(),
    ).toBe(200)
    await staff.reload()
    await expect(
      staff.locator('dl').filter({ has: staff.getByText('Recibido válido', { exact: true }) }),
    ).toContainText('$ 20.000,25')
    expect(
      (
        await write(
          page,
          `/api/v1/reservations/${reservation.id}/`,
          { total_amount: '80000.25' },
          'PATCH',
        )
      ).status(),
    ).toBe(200)
    await staff.reload()
    await expect(
      staff.getByRole('heading', { name: `Reserva · ${name}`, exact: true }),
    ).toBeVisible()
    await expect(
      staff.locator('dl').filter({ has: staff.getByText('Recibido válido', { exact: true }) }),
    ).toContainText('$ 70.000,25')
    expect(
      await staff.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true)
    await staff.screenshot({
      path: `../docs/screenshots/fase5-pagos-${info.project.name}.png`,
      fullPage: true,
    })
    await staff.goto('/reservas')
    await staff.getByLabel('Solo reservas con deuda', { exact: true }).check()
    await staff.getByLabel('Desde', { exact: true }).fill(start)
    await staff.getByLabel('Hasta (exclusiva)', { exact: true }).fill(end)
    await expect(staff.getByRole('heading', { name, exact: true })).toBeVisible()
    await staff.goto(`/reservas/${reservation.id}`)
    await staff.getByRole('button', { name: 'Cancelar reserva', exact: true }).click()
    await staff.getByLabel('Motivo obligatorio', { exact: true }).fill('Cancelación ficticia E2E')
    await staff.getByRole('button', { name: 'Aplicar cambio', exact: true }).click()
    await expect(staff.getByText('Cancelada', { exact: true })).toBeVisible()
    await expect(staff.getByRole('button', { name: 'Registrar abono', exact: true })).toHaveCount(0)
    const debts = await (
      await staff.request.get(`/api/v1/reservations/?debt=true&property_id=${property.id}`)
    ).json()
    expect(debts.count).toBe(0)
    expect(
      (await (await staff.request.get(`/api/v1/reservations/${reservation.id}/payments/`)).json())
        .count,
    ).toBe(3)
    await page.goto('/')
    await page.getByRole('button', { name: 'Seleccionar Empresa compartida ficticia' }).click()
    await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
      'Empresa compartida ficticia',
    )
    expect((await page.request.get(receipt!)).status()).toBe(404)
    expect(
      (await page.request.get(`/api/v1/reservations/${reservation.id}/payments/`)).status(),
    ).toBe(404)
  } finally {
    await context.close().catch(() => undefined)
  }
})
