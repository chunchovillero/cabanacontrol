import { expect, test } from '@playwright/test'

test('presentación pública con precios, demostración y acceso sin contratar', async ({
  page,
}, info) => {
  const writes: string[] = []
  page.on('request', (request) => {
    if (['POST', 'PATCH', 'DELETE', 'PUT'].includes(request.method())) writes.push(request.url())
  })
  await page.goto('/conocer')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Menos planillas.')
  await expect(page.getByRole('article', { name: 'Plan Inicial' })).toContainText('$4.500')
  await expect(page.getByRole('article', { name: 'Plan Crecimiento' })).toContainText('$9.900')
  await expect(page.getByRole('article', { name: 'Plan Operador' })).toContainText('$19.900')
  await page.getByRole('button', { name: 'pagos', exact: true }).click()
  await expect(page.getByText('Saldo pendiente', { exact: true })).toBeVisible()
  await expect(page.getByText('$120.000', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'limpieza', exact: true }).click()
  await expect(page.getByText(/^Dormitorios/)).toBeVisible()
  await page.getByRole('button', { name: 'reservas', exact: true }).click()
  await page.getByText('¿Puedo pagar o contratar desde esta página?', { exact: true }).click()
  await expect(page.getByText(/no hay checkout ni cobros reales habilitados/)).toBeVisible()
  await page.getByRole('link', { name: 'Precios', exact: true }).click()
  await expect(page).toHaveURL(/#precios$/)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.screenshot({
    path: `../docs/screenshots/landing-${info.project.name}.png`,
    fullPage: true,
  })
  await page.getByRole('link', { name: 'Ingresar', exact: false }).first().click()
  await expect(page.getByRole('button', { name: 'Iniciar sesión' })).toBeVisible()
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Menos planillas.')
  expect(writes).toEqual([])
})
