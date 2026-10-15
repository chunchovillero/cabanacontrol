import { expect, test } from '@playwright/test'
import { submitLogin } from './login'

test('compra simulada consentida, subida inmediata, bajada programada y cancelación', async ({
  page,
}, info) => {
  await page.goto('/ingresar')
  await page
    .getByLabel('Correo electrónico')
    .fill(`e2e-simulation-${info.project.name}@example.invalid`)
  await page.getByLabel('Contraseña', { exact: true }).fill('E2E-fictional-passphrase-2026!')
  await submitLogin(page)
  await page
    .getByRole('button', {
      name: new RegExp(`^Seleccionar Empresa simulación ${info.project.name}`),
    })
    .last()
    .click()
  await page.getByRole('link', { name: 'Plan y uso', exact: true }).click()
  await page.getByRole('link', { name: 'Revisar contratación simulada' }).click()
  await expect(page.getByText(/SIMULACIÓN LOCAL/)).toBeVisible()
  await page.getByRole('button', { name: 'Obtener cotización simulada' }).click()
  const confirm = page.getByRole('button', { name: 'Confirmar contratación simulada' })
  await expect(confirm).toBeDisabled()
  await page.getByRole('checkbox').check()
  await confirm.click()
  await page.getByRole('button', { name: 'Simular incierto', exact: true }).click()
  await expect(page.getByText(/Incierto: requiere conciliación/)).toBeVisible()
  await page.getByRole('button', { name: 'Simular aprobado', exact: true }).click()
  await expect(page.getByText('Plan: Inicial', { exact: false })).toBeVisible()
  await page.getByLabel('Plan de prueba').selectOption('growth')
  await page.getByRole('button', { name: 'Obtener cotización simulada' }).click()
  await expect(page.getByText(/Diferencia proporcional por subida/)).toBeVisible()
  await page.getByRole('checkbox').check()
  await confirm.click()
  await page.getByRole('button', { name: 'Simular aprobado', exact: true }).click()
  await expect(page.getByText('Plan: Crecimiento', { exact: false })).toBeVisible()
  await page.getByLabel('Plan de prueba').selectOption('initial')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Programar bajada al plan seleccionado' }).click()
  await expect(page.getByText(/Bajada programada: Inicial/)).toBeVisible()
  await page.getByRole('button', { name: 'Cancelar al final del periodo' }).click()
  await expect(page.getByText('Renovación: Desactivada', { exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByText('Plan: Crecimiento', { exact: false })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  expect(await page.evaluate(() => localStorage.length)).toBe(0)
})
