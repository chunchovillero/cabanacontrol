import { submitLogin } from './login'
import { expect, test } from '@playwright/test'

test('crear, editar, fotografiar y desactivar una cabaña sin borrar datos', async ({
  page,
}, info) => {
  await page.goto('/ingresar')
  await page
    .getByLabel('Correo electrónico')
    .fill(`e2e-property-${info.project.name}@example.invalid`)
  await page.getByLabel('Contraseña', { exact: true }).fill('E2E-fictional-passphrase-2026!')
  await submitLogin(page)
  await page.getByRole('button', { name: 'Seleccionar Empresa ficticia A' }).click()
  await page.getByRole('link', { name: 'Ver cabañas' }).click()
  await page.getByRole('link', { name: 'Nueva cabaña' }).click()
  const code = `E2E-${info.project.name}-${Date.now()}`.toUpperCase()
  await page.getByLabel('Nombre', { exact: true }).fill(`Cabaña ficticia ${info.project.name}`)
  await page.getByLabel('Código', { exact: true }).fill(code)
  await page.getByLabel('Capacidad máxima', { exact: true }).fill('5')
  await page.getByLabel('Tarifa base (CLP)').fill('50000,10')
  await page.getByLabel('Hora de entrada').fill('15:00')
  await page.getByLabel('Hora de salida').fill('11:00')
  await page.getByRole('button', { name: 'Guardar cabaña' }).click()
  await expect(
    page.getByRole('heading', { name: `Cabaña ficticia ${info.project.name}`, exact: true }),
  ).toBeVisible()
  const propertyUrl = page.url()
  const propertyId = new URL(propertyUrl).pathname.split('/').at(-1)!
  await page.getByRole('link', { name: 'Editar cabaña', exact: true }).click()
  await page.getByLabel('Capacidad máxima', { exact: true }).fill('6')
  await page.getByRole('button', { name: 'Guardar cabaña' }).click()
  await expect(page.getByText('6 personas', { exact: true })).toBeVisible()
  // PNG sintético de un píxel; no archivos ni fotografías personales.
  await page.getByLabel('Archivo', { exact: true }).setInputFiles({
    name: 'test.png',
    mimeType: 'image/png',
    buffer: Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
      'base64',
    ),
  })
  await page.getByLabel('Descripción de la fotografía').fill('Imagen sintética de prueba')
  await page.getByRole('button', { name: 'Subir foto', exact: true }).click()
  const image = page.getByRole('img', { name: 'Imagen sintética de prueba' })
  await expect(image).toBeVisible()
  const photoUrl = await image.getAttribute('src')
  expect((await page.request.get(photoUrl!)).status()).toBe(200)
  await page.getByRole('button', { name: 'Desactivar cabaña' }).click()
  await page
    .getByRole('alertdialog')
    .getByRole('button', { name: 'Confirmar', exact: true })
    .click()
  await expect(page.getByRole('button', { name: 'Reactivar cabaña' })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('img', { name: 'Imagen sintética de prueba' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.getByRole('link', { name: 'Empresas', exact: true }).click()
  await page.getByRole('button', { name: 'Seleccionar Empresa compartida ficticia' }).click()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
    'Empresa compartida ficticia',
  )
  expect((await page.request.get(`/api/v1/properties/${propertyId}/`)).status()).toBe(404)
  expect((await page.request.get(photoUrl!)).status()).toBe(404)
})
