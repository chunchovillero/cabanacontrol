import { randomUUID } from 'node:crypto'
import { expect, test } from '@playwright/test'
import { submitLogin } from './login'

test('propietario actualiza perfil y empresa, con persistencia tras recargar', async ({
  page,
}, info) => {
  await page.goto('/ingresar')
  await page
    .getByLabel('Correo electrónico')
    .fill(`e2e-settings-${info.project.name}@example.invalid`)
  await page.getByLabel('Contraseña', { exact: true }).fill('E2E-fictional-passphrase-2026!')
  await submitLogin(page)
  await page.getByRole('button', { name: /^Seleccionar / }).click()
  await page.getByRole('link', { name: 'Perfil y empresa' }).click()
  const suffix = randomUUID().slice(0, 8)
  await page.getByLabel('Nombre', { exact: true }).fill(`Perfil ${suffix}`)
  const profileResponse = page.waitForResponse(
    (r) => r.url().endsWith('/auth/profile/') && r.request().method() === 'PATCH',
  )
  await page.getByRole('button', { name: 'Guardar perfil' }).click()
  const savedProfile = await profileResponse
  expect(savedProfile.request().postDataJSON().first_name).toBe(`Perfil ${suffix}`)
  expect(savedProfile.status()).toBe(200)
  expect((await savedProfile.json()).first_name).toBe(`Perfil ${suffix}`)
  await expect(page.getByRole('status')).toHaveText('Cambios guardados.')
  await page.getByLabel('Nombre de la empresa', { exact: true }).fill(`Empresa ${suffix}`)
  await page.getByLabel('Correo de contacto (opcional)').fill(`contact-${suffix}@example.invalid`)
  await page.getByLabel('Teléfono de contacto (opcional)').fill('+56 9 1234 5678')
  const response = page.waitForResponse(
    (r) => r.url().endsWith('/company-settings/') && r.request().method() === 'PATCH',
  )
  await page.getByRole('button', { name: 'Guardar empresa' }).click()
  expect((await response).status()).toBe(200)
  await page.reload()
  await expect(page.getByLabel('Nombre', { exact: true })).toHaveValue(`Perfil ${suffix}`)
  await expect(page.getByLabel('Nombre de la empresa', { exact: true })).toHaveValue(
    `Empresa ${suffix}`,
  )
  await expect(page.getByLabel('Correo de contacto (opcional)')).toHaveValue(
    `contact-${suffix}@example.invalid`,
  )
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.getByRole('link', { name: 'Empresas', exact: true }).click()
  await expect(page.getByRole('heading', { name: `Empresa ${suffix}` })).toBeVisible()
  await expect(page.getByText(`Hola, Perfil ${suffix}`)).toBeVisible()
})
