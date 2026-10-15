import { expect, test } from '@playwright/test'

test('frontend compilado conserva sesión, cabañas y fotos bajo HTTPS', async ({ page }, info) => {
  const suffix = info.project.name === 'mobile' ? 'a' : 'b'
  await page.goto('/ingresar')
  await page.getByLabel('Correo electrónico').fill(`p-owner-${suffix}@example.invalid`)
  await page.getByLabel('Contraseña', { exact: true }).fill('P-fictional-passphrase-2026!')
  await page.getByRole('button', { name: 'Iniciar sesión' }).click()
  await page.getByRole('button', { name: `Seleccionar Empresa ficticia P ${suffix}` }).click()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
    `Empresa ficticia P ${suffix}`,
  )
  await page.goto('/cabanas')
  await expect(page.getByText(`Cabaña ficticia ${suffix}`, { exact: true }).first()).toBeVisible()
  await page.reload()
  await expect(page.getByText(`Empresa ficticia P ${suffix}`, { exact: true })).toBeVisible()
  await expect(page.getByText(`Cabaña ficticia ${suffix}`, { exact: true }).first()).toBeVisible()
  const cookies = await page.context().cookies()
  expect(cookies.find((cookie) => cookie.name === 'sessionid')).toMatchObject({
    secure: true,
    httpOnly: true,
    sameSite: 'Lax',
  })
  expect(await page.evaluate(() => localStorage.length)).toBe(0)
  const cabins = await (await page.request.get('/api/v1/properties/')).json()
  const cabin = cabins.results[0]
  const photos = await (await page.request.get(`/api/v1/properties/${cabin.id}/photos/`)).json()
  expect(
    (
      await page.request.get(`/api/v1/properties/${cabin.id}/photos/${photos[0].id}/file/`)
    ).status(),
  ).toBe(200)
})
