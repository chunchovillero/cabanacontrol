import { randomUUID } from 'node:crypto'
import { expect, test } from '@playwright/test'
import { submitLogin } from './login'

test('alta web crea propietario y primera empresa con acceso aislado', async ({ page }) => {
  const id = randomUUID()
  const email = `owner-${id}@example.invalid`
  const company = `Empresa nueva ${id}`
  await page.goto('/ingresar')
  await page.getByRole('link', { name: 'Crear cuenta y empresa' }).click()
  await page.getByLabel('Nombre', { exact: true }).fill('Propietario ficticio')
  await page.getByLabel('Correo electrónico').fill(email)
  await page.getByLabel('Nombre de la empresa', { exact: true }).fill(company)
  await page.getByLabel('Contraseña', { exact: true }).fill('Onboarding-fictional-passphrase-2026!')
  await page.getByLabel('Repite la contraseña').fill('Different-fictional-passphrase!')
  await page.getByRole('button', { name: 'Crear cuenta y empresa' }).click()
  await expect(page.getByRole('alert')).toHaveText('Las contraseñas no coinciden.')
  await page.getByLabel('Repite la contraseña').fill('Onboarding-fictional-passphrase-2026!')
  await page.getByRole('button', { name: 'Crear cuenta y empresa' }).click()
  await expect(page.getByRole('status')).toContainText('Cuenta y empresa creadas.')
  expect(await page.evaluate(() => localStorage.length)).toBe(0)
  await page.getByRole('link', { name: 'Iniciar sesión', exact: true }).click()
  await page.getByLabel('Correo electrónico').fill(email)
  await page.getByLabel('Contraseña', { exact: true }).fill('Onboarding-fictional-passphrase-2026!')
  await submitLogin(page)
  await expect(page.getByRole('button', { name: `Seleccionar ${company}` })).toBeVisible()
  await expect(page.getByRole('button', { name: /^Seleccionar / })).toHaveCount(1)
  await page.getByRole('button', { name: `Seleccionar ${company}` }).click()
  await page.getByRole('link', { name: 'Usuarios', exact: true }).click()
  await expect(page.getByText('Propietario · Acceso protegido')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
})
