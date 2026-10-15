import { submitLogin } from './login'
import { randomUUID } from 'node:crypto'
import { expect, test } from '@playwright/test'

test('propietario invita desde web, invitado crea cuenta y permisos se pueden revocar', async ({
  page,
  browser,
}, info) => {
  test.setTimeout(90000)
  await expect
    .poll(
      async () => {
        try {
          return (await page.request.get('/health/')).status()
        } catch {
          return 0
        }
      },
      { timeout: 30000 },
    )
    .toBe(200)
  await page.goto('/ingresar')
  await page.getByLabel('Correo electrónico').fill(`e2e-team-${info.project.name}@example.invalid`)
  await page.getByLabel('Contraseña', { exact: true }).fill('E2E-fictional-passphrase-2026!')
  // Exercise Retry-After handling without changing any real authentication limits.
  await page.route(
    '**/api/v1/auth/login/',
    async (route) => {
      await route.fulfill({
        status: 429,
        headers: { 'Retry-After': '1', 'Content-Type': 'application/json' },
        body: JSON.stringify({
          error: {
            code: 'throttled',
            details: { detail: 'Espera un segundo antes de reintentar.' },
          },
        }),
      })
    },
    { times: 1 },
  )
  await submitLogin(page)
  await page
    .getByRole('button', { name: `Seleccionar Empresa equipo ${info.project.name}` })
    .last()
    .click()
  await page.getByRole('link', { name: 'Usuarios', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Usuarios', exact: true })).toBeVisible()
  await expect(page.getByText('Propietario · Acceso protegido')).toBeVisible()
  const email = `team-${randomUUID()}@example.invalid`
  await page.getByLabel('Correo del invitado').fill(email)
  await page.getByLabel('Permiso inicial').selectOption('manager')
  await page.getByRole('button', { name: 'Crear invitación', exact: true }).click()
  const invitation = await page.getByLabel('Enlace privado de invitación').inputValue()
  expect(invitation).toContain('/invitacion#token=')
  const guestContext = await browser.newContext({ viewport: page.viewportSize()! })
  try {
    const guest = await guestContext.newPage()
    await guest.goto(invitation)
    await expect(
      guest.getByText(`Empresa equipo ${info.project.name}`, { exact: true }),
    ).toBeVisible()
    expect(new URL(guest.url()).hash).toBe('')
    await guest.getByLabel('Nombre', { exact: true }).fill('Invitado ficticio')
    await guest.getByLabel('Apellido', { exact: true }).fill('Del equipo')
    await guest.getByLabel('Contraseña nueva').fill('New-fictional-passphrase-2026!')
    await guest.getByLabel('Repite tu contraseña').fill('New-fictional-passphrase-2026!')
    await guest.getByRole('button', { name: 'Crear cuenta y aceptar' }).click()
    await expect(guest.getByRole('heading', { name: 'Invitación aceptada' })).toBeVisible()
    await guest.getByRole('link', { name: 'Iniciar sesión', exact: true }).click()
    await guest.getByLabel('Correo electrónico').fill(email)
    await guest.getByLabel('Contraseña', { exact: true }).fill('New-fictional-passphrase-2026!')
    await submitLogin(guest)
    await guest
      .getByRole('button', { name: `Seleccionar Empresa equipo ${info.project.name}` })
      .click()
    await expect(guest.getByRole('region', { name: 'Empresa activa' })).toContainText(
      'Administrador',
    )
    await expect(guest.getByRole('link', { name: 'Usuarios', exact: true })).toHaveCount(0)
    await guest.goto('/usuarios')
    await expect(guest.getByRole('alert')).toContainText('Solo el propietario')
    await page.reload()
    const card = page
      .getByRole('article')
      .filter({
        has: page.getByRole('heading', { name: 'Invitado ficticio Del equipo', exact: true }),
      })
      .filter({ has: page.getByText(email, { exact: true }) })
    await expect(card).toBeVisible()
    await card.getByLabel(`Permiso de ${email}`).selectOption('staff')
    await card.getByLabel(`Revisé el cambio de acceso de ${email}.`).check()
    const savedRole = page.waitForResponse(
      (response) =>
        response.url().includes('/api/v1/team/memberships/') &&
        response.request().method() === 'PATCH' &&
        response.status() === 200,
    )
    await card.getByRole('button', { name: 'Guardar acceso' }).click()
    await savedRole
    await expect(card.getByLabel(`Permiso de ${email}`)).toHaveValue('staff')
    await guest.goto('/')
    await expect(guest.getByRole('region', { name: 'Empresa activa' })).toContainText('Colaborador')
    await card.getByLabel(`Acceso activo de ${email}`).uncheck()
    await card.getByLabel(`Revisé el cambio de acceso de ${email}.`).check()
    await card.getByRole('button', { name: 'Guardar acceso' }).click()
    await expect(card.getByLabel(`Acceso activo de ${email}`)).not.toBeChecked()
    await expect
      .poll(async () => (await guest.request.get('/api/v1/properties/')).status())
      .toBe(403)
    expect((await guest.request.get('/api/v1/auth/me/')).status()).toBe(200)
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true)
    await page.screenshot({
      path: `../docs/screenshots/phase11a-users-${info.project.name}.png`,
      fullPage: true,
    })
    await guest.goto(invitation)
    await expect(guest.getByRole('alert')).toContainText('no está disponible')
  } finally {
    await guestContext.close()
  }
})
