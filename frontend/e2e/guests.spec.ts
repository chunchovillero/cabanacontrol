import { submitLogin } from './login'
import { expect, test } from '@playwright/test'

test('huésped con RUT, reutilización, extranjero y privacidad de staff', async ({
  page,
  browser,
}, info) => {
  await page.goto('/ingresar')
  await page.getByLabel('Correo electrónico').fill(`e2e-guest-${info.project.name}@example.invalid`)
  await page.getByLabel('Contraseña', { exact: true }).fill('E2E-fictional-passphrase-2026!')
  await submitLogin(page)
  await page.getByRole('button', { name: 'Seleccionar Empresa ficticia A' }).click()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
    'Empresa ficticia A',
  )
  await page.getByRole('link', { name: 'Huéspedes', exact: true }).click()
  await page.getByRole('link', { name: 'Nuevo huésped', exact: true }).click()
  await page.getByLabel('Nombres', { exact: true }).fill('Persona ficticia E2E')
  await page.getByLabel('Apellidos', { exact: true }).fill(`Prueba ${info.project.name}`)
  const body = String(90_000_000 + (Date.now() % 9_000_000))
  const sum = [...body]
    .reverse()
    .reduce((total, digit, index) => total + Number(digit) * (2 + (index % 6)), 0)
  const mod = 11 - (sum % 11)
  const rut = `${body}-${mod === 11 ? '0' : mod === 10 ? 'K' : mod}`
  await page.getByLabel('RUT', { exact: true }).fill(rut)
  await page.getByLabel('Notas restringidas (opcional)').fill('Nota privada ficticia E2E')
  await page.getByRole('button', { name: 'Guardar huésped', exact: true }).click()
  await expect(
    page.getByRole('heading', {
      name: `Persona ficticia E2E Prueba ${info.project.name}`,
      exact: true,
    }),
  ).toBeVisible()
  const guestId = new URL(page.url()).pathname.split('/').at(-1)!
  await page.getByRole('link', { name: 'Editar huésped', exact: true }).click()
  await page.getByLabel('Nombres', { exact: true }).fill('Persona ficticia editada')
  await page.getByRole('button', { name: 'Guardar huésped', exact: true }).click()
  await expect(
    page.getByRole('heading', {
      name: `Persona ficticia editada Prueba ${info.project.name}`,
      exact: true,
    }),
  ).toBeVisible()
  await page.goto('/huespedes/nuevo')
  await page.getByLabel('Nombres', { exact: true }).fill('Duplicado ficticio')
  await page.getByLabel('Apellidos', { exact: true }).fill('Prueba')
  await page.getByLabel('RUT', { exact: true }).fill(rut)
  await page.getByRole('button', { name: 'Guardar huésped', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Abrir ficha existente' })).toHaveAttribute(
    'href',
    `/huespedes/${guestId}`,
  )
  await page.getByRole('link', { name: 'Abrir ficha existente' }).click()
  await page.getByRole('link', { name: 'Volver a huéspedes' }).click()
  await page.getByLabel('Buscar por nombre o documento completo').fill(rut)
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  await expect(
    page.getByRole('heading', {
      name: `Persona ficticia editada Prueba ${info.project.name}`,
      exact: true,
    }),
  ).toBeVisible()
  expect(page.url()).not.toContain(rut)
  await page.goto('/huespedes/nuevo')
  await page.getByLabel('Nombres', { exact: true }).fill('Persona extranjera ficticia')
  await page.getByLabel('Apellidos', { exact: true }).fill('Prueba')
  await page.getByLabel('Tipo de documento').selectOption('passport')
  await page.getByLabel('Número de documento', { exact: true }).fill('P-TEST-E2E')
  await page.getByRole('button', { name: 'Guardar huésped', exact: true }).click()
  await expect(page.getByText('P-TEST-E2E', { exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)

  const staffContext = await browser.newContext()
  try {
    const staff = await staffContext.newPage()
    const origin = new URL(page.url()).origin
    await staff.goto(`${origin}/ingresar`)
    await staff
      .getByLabel('Correo electrónico')
      .fill(`e2e-guest-staff-${info.project.name}@example.invalid`)
    await staff.getByLabel('Contraseña', { exact: true }).fill('E2E-fictional-passphrase-2026!')
    await submitLogin(staff)
    await staff.getByRole('button', { name: 'Seleccionar Empresa ficticia A' }).click()
    await expect(staff.getByRole('region', { name: 'Empresa activa' })).toContainText(
      'Empresa ficticia A',
    )
    await staff.goto(`${origin}/huespedes/${guestId}`)
    await expect(
      staff.getByRole('heading', {
        name: `Persona ficticia editada Prueba ${info.project.name}`,
        exact: true,
      }),
    ).toBeVisible()
    await expect(staff.getByRole('link', { name: 'Editar huésped' })).toHaveCount(0)
    await expect(staff.getByText('Nota privada ficticia E2E', { exact: true })).toHaveCount(0)
    const detail = await staff.request.get(`${origin}/api/v1/guests/${guestId}/`)
    const data = (await detail.json()) as { document_number: string | null; notes: string | null }
    expect(data.document_number).toBeNull()
    expect(data.notes).toBeNull()
  } finally {
    await staffContext.close()
  }
  await page.goto('/')
  await page.getByRole('button', { name: 'Seleccionar Empresa compartida ficticia' }).click()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
    'Empresa compartida ficticia',
  )
  expect((await page.request.get(`/api/v1/guests/${guestId}/`)).status()).toBe(404)
})
