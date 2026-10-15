import { submitLogin } from './login'
import { expect, test, type Page } from '@playwright/test'

async function login(page: Page, variant: string) {
  await page.goto('/ingresar')
  await page
    .getByLabel('Correo electrónico')
    .fill(`e2e-operations-staff-${variant}@example.invalid`)
  await page.getByLabel('Contraseña', { exact: true }).fill('E2E-fictional-passphrase-2026!')
  await submitLogin(page)
  await page.getByRole('button', { name: 'Seleccionar Empresa ficticia A' }).click()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
    'Empresa ficticia A',
  )
}
test('staff finaliza estadía, completa limpieza y prepara WhatsApp manual sin enviar', async ({
  page,
}, info) => {
  test.setTimeout(120000)
  await login(page, info.project.name)
  const name = `Cabaña ficticia operación ${info.project.name}`
  const properties = await (
    await page.request.get(`/api/v1/properties/?search=${encodeURIComponent(name)}`)
  ).json()
  const property = properties.results.find((item: { name: string }) => item.name === name)
  expect(property).toBeTruthy()
  const reservations = await (
    await page.request.get(`/api/v1/reservations/?property_id=${property.id}&status=checked_in`)
  ).json()
  const reservation = reservations.results[0]
  expect(reservation).toBeTruthy()
  await page.goto('/operacion')
  await expect(page.getByRole('heading', { name: 'Operación diaria' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Bloquear por mantenimiento' })).toHaveCount(0)
  await page.getByLabel('Buscar cabaña', { exact: true }).fill(name)
  await expect(page.getByLabel('Cabaña', { exact: true }).locator('option')).toHaveCount(2)
  await page.getByLabel('Cabaña', { exact: true }).selectOption(property.id)
  await page.getByRole('button', { name: /^Salidas ·/ }).click()
  await expect(page.locator(`a[href="/reservas/${reservation.id}"]`)).toBeVisible()
  await page.goto(`/reservas/${reservation.id}`)
  await page.getByRole('button', { name: 'Preparar WhatsApp' }).click()
  await expect(page.getByLabel('Mensaje para revisar')).toContainText('Estado: En estadía')
  await page.getByLabel('Teléfono internacional de WhatsApp').fill('+9990000000')
  await page.getByLabel('Mensaje para revisar').fill('Mensaje ficticio editable; no enviar')
  const link = page.getByRole('link', { name: 'Abrir WhatsApp' })
  await expect(link).toHaveAttribute('href', /https:\/\/wa\.me\/9990000000\?text=/)
  const href = await link.getAttribute('href')
  expect(new URL(href!).searchParams.get('text')).toBe('Mensaje ficticio editable; no enviar')
  await page.getByRole('button', { name: 'Finalizada', exact: true }).click()
  await page.getByRole('button', { name: 'Aplicar cambio' }).click()
  await expect(page.getByRole('button', { name: 'Finalizada', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Aplicar cambio' })).toHaveCount(0)
  await expect(page.getByText('Finalizada', { exact: true })).toBeVisible()
  const tasks = await (
    await page.request.get(`/api/v1/housekeeping/?property_id=${property.id}&status=pending`)
  ).json()
  const task = tasks.results.find(
    (item: { reservation_id: string }) => item.reservation_id === reservation.id,
  )
  expect(task).toBeTruthy()
  await page.goto(`/limpieza/${task.id}`)
  await expect(page.getByRole('heading', { name: `Limpieza · ${name}` })).toBeVisible()
  await page.getByLabel('Estado', { exact: true }).selectOption('completed')
  await expect(page.getByRole('button', { name: 'Guardar tarea' })).toBeDisabled()
  for (const item of ['Baño', 'Cocina', 'Dormitorios', 'Inventario'])
    await page.getByLabel(item, { exact: true }).check()
  await page.getByRole('button', { name: 'Guardar tarea' }).click()
  await expect(
    page.getByText('Historial conservado. Para corregirlo, crea una tarea nueva.'),
  ).toBeVisible()
  await expect(page.getByText('Baño: Revisado')).toBeVisible()
  await page.screenshot({
    path: `../docs/screenshots/phase8-cleaning-${info.project.name}.png`,
    fullPage: true,
  })
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy()
  await page.goto('/operacion')
  await page.getByLabel('Buscar cabaña', { exact: true }).fill(name)
  await expect(page.getByLabel('Cabaña', { exact: true }).locator('option')).toHaveCount(2)
  await page.getByLabel('Cabaña', { exact: true }).selectOption(property.id)
  await page.getByRole('button', { name: /^Limpieza pendiente ·/ }).click()
  await expect(page.getByRole('button', { name: /^Limpieza pendiente ·/ })).toContainText(
    String(tasks.count - 1),
  )
  await expect(page.locator(`a[href="/limpieza/${task.id}"]`)).toHaveCount(0)
  await page.screenshot({
    path: `../docs/screenshots/phase8-operations-${info.project.name}.png`,
    fullPage: true,
  })
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy()
  await page.goto('/limpieza/nueva')
  await page.getByLabel('Buscar cabaña', { exact: true }).fill(name)
  await expect(page.getByLabel('Cabaña', { exact: true }).locator('option')).toHaveCount(2)
  await page.getByLabel('Cabaña', { exact: true }).selectOption(property.id)
  await page.getByRole('button', { name: 'Guardar tarea' }).click()
  await expect(page.getByRole('heading', { name: `Limpieza · ${name}` })).toBeVisible()
  await page.getByLabel('Estado', { exact: true }).selectOption('cancelled')
  await page.getByLabel('Motivo de cancelación').fill('Motivo ficticio E2E')
  await page.getByRole('button', { name: 'Guardar tarea' }).click()
  await expect(page.getByText('Motivo: Motivo ficticio E2E')).toBeVisible()
})
