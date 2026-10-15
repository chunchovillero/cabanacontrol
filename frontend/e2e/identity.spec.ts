import { submitLogin } from './login'
import { expect, test, type Page } from '@playwright/test'

const companyA = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
const companyB = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
const companyC = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'

async function login(page: Page, who: 'a' | 'b' = 'a') {
  await page.goto('/ingresar')
  await page
    .getByLabel('Correo electrónico')
    .fill(`e2e-identity-${test.info().project.name}-${who}@example.invalid`)
  await page.getByLabel('Contraseña', { exact: true }).fill('E2E-fictional-passphrase-2026!')
  await submitLogin(page)
  await expect(page.getByRole('heading', { name: 'Tus empresas' })).toBeVisible()
}

test('sesión, selección de empresa, persistencia y cierre', async ({ page }) => {
  await login(page)
  await expect(page.getByRole('heading', { name: 'Empresa ficticia B', exact: true })).toHaveCount(
    0,
  )
  await page.getByRole('button', { name: 'Seleccionar Empresa ficticia A' }).click()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
    'Empresa ficticia A',
  )
  await page.reload()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
    'Empresa ficticia A',
  )
  await page.getByRole('button', { name: 'Seleccionar Empresa compartida ficticia' }).click()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText('Colaborador')
  const members = await page.request.get(`/api/v1/tenants/${companyC}/memberships/`)
  expect(members.status()).toBe(403)
  await page.getByRole('link', { name: 'Conocer CabañaControl', exact: true }).click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Menos planillas.')
  await page.getByRole('link', { name: 'Ir a mi cuenta', exact: false }).click()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText('Colaborador')
  await page.getByRole('button', { name: 'Cerrar sesión' }).click()
  await expect(page.getByRole('link', { name: 'Ingresar a mi cuenta' })).toBeVisible()
  expect((await page.request.get('/api/v1/auth/me/')).status()).toBe(403)
  expect(await page.evaluate(() => localStorage.length)).toBe(0)
})

test('rechaza IDs ajenos y escrituras sin CSRF', async ({ page }) => {
  await login(page, 'b')
  expect((await page.request.get(`/api/v1/tenants/${companyA}/`)).status()).toBe(404)
  expect(
    (
      await page.request.post(`/api/v1/tenants/${companyB}/select/`, {
        data: {},
      })
    ).status(),
  ).toBe(403)
  const csrf = await page.request.get('/api/v1/auth/csrf/')
  const { csrf_token } = (await csrf.json()) as { csrf_token: string }
  expect(
    (
      await page.request.post(`/api/v1/tenants/${companyA}/select/`, {
        data: {},
        headers: { 'X-CSRFToken': csrf_token },
      })
    ).status(),
  ).toBe(404)
  await page.getByRole('button', { name: 'Seleccionar Empresa ficticia B' }).click()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
    'Empresa ficticia B',
  )
  expect((await page.request.get(`/api/v1/tenants/${companyA}/memberships/`)).status()).toBe(404)
})

test('recuperación genérica y formulario responsive', async ({ page }) => {
  await page.goto('/recuperar')
  await page
    .getByLabel('Correo electrónico')
    .fill(`missing-${test.info().project.name}@example.invalid`)
  await page.getByRole('button', { name: 'Enviar instrucciones' }).click()
  await expect(page.getByRole('status')).toContainText('Si el correo corresponde')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.goto('/restablecer')
  await expect(page.getByRole('alert')).toContainText('El enlace está incompleto')
})
