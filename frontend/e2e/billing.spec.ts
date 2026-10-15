import { expect, test } from '@playwright/test'
import { submitLogin } from './login'

test('trial vencido conserva operación y capacidad 1/1 sin permitir segunda cabaña', async ({
  page,
}, info) => {
  await page.goto('/ingresar')
  await page
    .getByLabel('Correo electrónico')
    .fill(`e2e-billing-${info.project.name}@example.invalid`)
  await page.getByLabel('Contraseña', { exact: true }).fill('E2E-fictional-passphrase-2026!')
  await submitLogin(page)
  await page.getByRole('button', { name: `Seleccionar Empresa plan ${info.project.name}` }).click()
  await page.getByRole('link', { name: 'Plan y uso', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Prueba de 14 días' })).toBeVisible()
  await expect(page.getByRole('alert')).toContainText('sin suspensión automática ni cobros')
  await expect(page.getByText('1 / 1', { exact: true })).toHaveCount(2)
  await expect(page.getByText(/CLP\/mes · Referencia de simulación/)).toHaveCount(3)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.getByRole('link', { name: 'Cabañas', exact: true }).click()
  await page.getByRole('link', { name: 'Nueva cabaña' }).click()
  await page.getByLabel('Nombre', { exact: true }).fill('No debe crearse')
  await page.getByLabel('Código', { exact: true }).fill(`LIMIT-${Date.now()}`)
  await page.getByLabel('Capacidad máxima', { exact: true }).fill('2')
  await page.getByLabel('Tarifa base (CLP)').fill('50000')
  await page.getByLabel('Hora de entrada').fill('15:00')
  await page.getByLabel('Hora de salida').fill('11:00')
  const rejected = page.waitForResponse(
    (r) => r.url().endsWith('/api/v1/properties/') && r.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Guardar cabaña' }).click()
  expect((await rejected).status()).toBe(409)
  await expect(page.getByRole('alert')).toContainText('capacidad del plan')
  expect((await page.request.get('/api/v1/properties/')).status()).toBe(200)
  await page.getByRole('link', { name: 'Plan y uso', exact: true }).click()
  await expect(page.getByText('1 / 1', { exact: true })).toHaveCount(2)
})
