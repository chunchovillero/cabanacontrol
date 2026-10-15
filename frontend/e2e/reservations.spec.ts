import { submitLogin } from './login'
import { expect, test, type Page } from '@playwright/test'
import { localHold } from '../src/features/reservations/dates'

const company = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
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
async function write(page: Page, url: string, data: unknown) {
  const csrf = await (await page.request.get('/api/v1/auth/csrf/')).json()
  return page.request.post(url, {
    data,
    headers: { 'X-CSRFToken': csrf.csrf_token, 'X-Tenant-Context': company },
  })
}

test('reservar con retención, evitar solapamientos, permitir recambio y bloquear fechas', async ({
  page,
  browser,
}, info) => {
  test.setTimeout(120000)
  const suffix = `${info.project.name}-${Date.now()}`
  const name = `Cabaña ficticia reserva ${suffix}`
  const guestName = `Persona ficticia ${suffix}`
  await login(page, `e2e-reservation-${info.project.name}@example.invalid`)
  const propertyResponse = await write(page, '/api/v1/properties/', {
    name,
    code: `R-${suffix}`.toUpperCase(),
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
    first_name: guestName,
    last_name: 'Prueba',
    document_type: 'passport',
    document_number: 'E2E-FAKE-ONLY',
    phone: '',
    email: '',
    notes: 'Nota restringida ficticia',
  })
  expect(guestResponse.status()).toBe(201)
  const guest = await guestResponse.json()
  const context = await browser.newContext({
    baseURL: 'http://localhost:15174',
    viewport: page.viewportSize()!,
  })
  const staff = await context.newPage()
  try {
    await login(staff, `e2e-reservation-staff-${info.project.name}@example.invalid`)
    const start = new Date(Date.now() + 45 * 86400000).toISOString().slice(0, 10)
    const end = new Date(Date.now() + 48 * 86400000).toISOString().slice(0, 10)
    const later = new Date(Date.now() + 50 * 86400000).toISOString().slice(0, 10)
    async function fill(startDate = start, endDate = end, status = 'pending') {
      await staff.goto('/reservas/nueva')
      await staff.getByLabel('Buscar cabaña', { exact: true }).fill(name)
      await expect(
        staff.getByRole('option', { name: `${name} · 4 personas`, exact: true }),
      ).toHaveCount(1)
      await staff.getByLabel('Cabaña', { exact: true }).selectOption(property.id)
      await staff.getByLabel('Buscar huésped', { exact: true }).fill(guestName)
      await expect(staff.locator(`option[value="${guest.id}"]`)).toHaveCount(1)
      await staff.getByLabel('Huésped principal', { exact: true }).selectOption(guest.id)
      await staff.getByLabel('Entrada', { exact: true }).fill(startDate)
      await staff.getByLabel('Salida (exclusiva)', { exact: true }).fill(endDate)
      await staff.getByLabel('Adultos', { exact: true }).fill('2')
      await staff.getByLabel('Precio total pactado (CLP)', { exact: true }).fill('150000.25')
      await staff.getByLabel('Estado inicial', { exact: true }).selectOption(status)
      if (status === 'pending')
        await staff
          .getByLabel('Retener hasta', { exact: true })
          .fill(localHold(new Date(Date.now() + 86400000).toISOString(), 'America/Santiago'))
    }
    await fill()
    expect(
      await staff.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true)
    await staff.getByRole('button', { name: 'Guardar reserva', exact: true }).click()
    await expect(
      staff.getByRole('heading', { name: `Reserva · ${name}`, exact: true }),
    ).toBeVisible()
    const id = new URL(staff.url()).pathname.split('/').at(-1)!
    await expect(staff.getByText(/Retención vigente hasta/)).toBeVisible()
    await staff.getByRole('button', { name: 'Confirmar reserva', exact: true }).click()
    await staff.getByRole('button', { name: 'Aplicar cambio', exact: true }).click()
    await expect(staff.getByText('Confirmada', { exact: true })).toBeVisible()
    const detail = await (await staff.request.get(`/api/v1/reservations/${id}/`)).json()
    expect(detail.guest.document_number).toBeUndefined()
    expect(JSON.stringify(detail)).not.toContain('Nota restringida ficticia')
    await staff.getByRole('link', { name: 'Editar reserva', exact: true }).click()
    await staff.getByLabel('Precio total pactado (CLP)', { exact: true }).fill('160000.75')
    await staff.getByRole('button', { name: 'Guardar reserva', exact: true }).click()
    await expect(
      staff.getByRole('heading', { name: `Reserva · ${name}`, exact: true }),
    ).toBeVisible()
    expect(
      (await (await staff.request.get(`/api/v1/reservations/${id}/`)).json()).total_amount,
    ).toBe('160000.75')
    await staff.screenshot({
      path: `../docs/screenshots/fase4-reserva-${info.project.name}.png`,
      fullPage: true,
    })
    await staff.goto('/reservas/disponibilidad')
    await staff.getByLabel('Entrada', { exact: true }).fill(start)
    await staff.getByLabel('Salida (exclusiva)', { exact: true }).fill(end)
    await staff.getByLabel('Personas', { exact: true }).fill('4')
    await staff.getByRole('button', { name: 'Consultar', exact: true }).click()
    const option = staff
      .getByRole('article')
      .filter({ has: staff.getByRole('heading', { name, exact: true }) })
    await expect(staff.getByRole('article').first()).toBeVisible()
    while ((await option.count()) === 0) {
      const next = staff.getByRole('button', { name: 'Siguiente', exact: true })
      await expect(next).toBeEnabled()
      const response = staff.waitForResponse(
        (item) => item.url().includes('/api/v1/availability/?') && item.ok(),
      )
      await next.click()
      await response
      await expect(staff.getByText('Consultando disponibilidad…', { exact: true })).toHaveCount(0)
    }
    await expect(option).toContainText('No disponible')
    expect(
      await staff.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true)
    await staff.screenshot({
      path: `../docs/screenshots/fase4-disponibilidad-${info.project.name}.png`,
      fullPage: true,
    })
    await fill(start, end, 'confirmed')
    await staff.getByRole('button', { name: 'Guardar reserva', exact: true }).click()
    await expect(staff.getByRole('alert')).toContainText('no está disponible')
    await fill(end, later, 'confirmed')
    await staff.getByRole('button', { name: 'Guardar reserva', exact: true }).click()
    await expect(
      staff.getByRole('heading', { name: `Reserva · ${name}`, exact: true }),
    ).toBeVisible()
    await staff.goto(`/reservas/${id}`)
    await staff.getByRole('button', { name: 'Cancelar reserva', exact: true }).click()
    await staff.getByLabel('Motivo obligatorio').fill('Cancelación ficticia E2E')
    await staff.getByRole('button', { name: 'Aplicar cambio', exact: true }).click()
    await expect(staff.getByText('Cancelada', { exact: true })).toBeVisible()
    await page.goto('/reservas/bloqueos/nuevo')
    await page.getByLabel('Buscar cabaña', { exact: true }).fill(name)
    await expect(page.getByRole('option', { name, exact: true })).toHaveCount(1)
    await page.getByLabel('Cabaña', { exact: true }).selectOption(property.id)
    await page.getByLabel('Inicio', { exact: true }).fill(start)
    await page.getByLabel('Fin (exclusivo)', { exact: true }).fill(end)
    await page.getByRole('button', { name: 'Guardar bloqueo', exact: true }).click()
    await expect(
      page.getByRole('heading', { name: 'Bloqueos de fechas', exact: true }),
    ).toBeVisible()
    await fill(start, end, 'confirmed')
    await staff.getByRole('button', { name: 'Guardar reserva', exact: true }).click()
    await expect(staff.getByRole('alert')).toContainText('no está disponible')
    expect((await write(staff, '/api/v1/availability-blocks/', {})).status()).toBe(403)
    const article = page
      .getByRole('article')
      .filter({ has: page.getByRole('heading', { name, exact: true }) })
    await article.getByRole('button', { name: 'Liberar fechas', exact: true }).click()
    await page.getByRole('button', { name: 'Confirmar liberación', exact: true }).click()
    await expect(article).toHaveCount(0)
    await fill(start, end, 'confirmed')
    await staff.getByRole('button', { name: 'Guardar reserva', exact: true }).click()
    await expect(
      staff.getByRole('heading', { name: `Reserva · ${name}`, exact: true }),
    ).toBeVisible()
    expect(
      await staff.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true)
    await page.goto('/')
    await page.getByRole('button', { name: 'Seleccionar Empresa compartida ficticia' }).click()
    await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
      'Empresa compartida ficticia',
    )
    expect((await page.request.get(`/api/v1/reservations/${id}/`)).status()).toBe(404)
  } finally {
    await context.close().catch(() => undefined)
  }
})
