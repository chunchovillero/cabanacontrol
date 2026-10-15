import { submitLogin } from './login'
import { expect, test } from '@playwright/test'

test.use({
  launchOptions: { args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'] },
})

test('staff consulta IA simulada, revisa texto y convierte una consulta manual a borrador', async ({
  page,
}, info) => {
  test.setTimeout(120000)
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
  await page
    .getByLabel('Correo electrónico')
    .fill(`e2e-assistant-${info.project.name}@example.invalid`)
  await page.getByLabel('Contraseña', { exact: true }).fill('E2E-fictional-passphrase-2026!')
  await submitLogin(page)
  const companies = page.getByRole('button', {
    name: new RegExp(`Seleccionar Empresa asistente ${info.project.name}`),
  })
  await companies.last().click()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
    'Empresa asistente',
  )
  await page.goto('/asistente')
  await expect(
    page.getByText('Proveedor simulado · Datos ficticios · Sin llamadas a OpenAI'),
  ).toBeVisible()
  const start = new Date(Date.now() + 90 * 86400000).toISOString().slice(0, 10)
  const end = new Date(Date.now() + 93 * 86400000).toISOString().slice(0, 10)
  await page
    .getByLabel('Texto revisado para analizar')
    .fill(`Consulta para 2 personas desde ${start} hasta ${end}`)
  await expect(page.getByRole('button', { name: 'Consultar asistente' })).toBeDisabled()
  await page.getByLabel('Revisé el texto y autorizaré su envío a OpenAI.').check()
  await page.getByRole('button', { name: 'Consultar asistente' }).click()
  await expect(page.getByText('Precio por confirmar', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Preparar respuesta para esta cabaña' }).click()
  await expect(page.getByLabel('Respuesta para WhatsApp editable')).toHaveValue(
    /Precio por confirmar/,
  )
  await expect(
    page.getByText(`Cabaña asistente ${info.project.name}`, { exact: false }).first(),
  ).toBeVisible()
  await page.goto('/consultas/nueva')
  await page
    .getByLabel('Texto original (se guarda en esta empresa)')
    .fill('Consulta ficticia por teléfono, con revisión humana.')
  await page
    .getByLabel('Texto revisado para enviar a IA')
    .fill(`Consulta para 2 personas desde ${start} hasta ${end}`)
  await page.getByRole('button', { name: 'Guardar consulta', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Ficha de consulta' })).toBeVisible()
  await page.getByLabel('Revisé el texto y autorizo enviarlo a OpenAI.').check()
  await page.getByRole('button', { name: 'Analizar texto revisado' }).click()
  await expect(page.getByText('Campos propuestos por IA: requieren revisión')).toBeVisible()
  await page.context().grantPermissions(['microphone'])
  await page.getByRole('button', { name: 'Iniciar dictado' }).click()
  await expect(page.getByText('Grabando · parada automática antes de 60 segundos')).toBeVisible()
  await page.waitForTimeout(1000)
  await page.getByRole('button', { name: 'Detener dictado' }).click()
  await expect(page.getByLabel('Revisar dictado')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Enviar a transcribir' })).toBeDisabled()
  await page.getByLabel('Revisé el audio y autorizo enviarlo a OpenAI para transcribir.').check()
  await page.getByRole('button', { name: 'Enviar a transcribir' }).click()
  await expect(page.getByLabel('Texto revisado para enviar a IA')).toHaveValue(/Dictado simulado/)
  await page
    .getByLabel('Texto revisado para enviar a IA')
    .fill('Texto corregido por el operador, sin envío automático.')
  await page
    .getByLabel('Buscar cabaña', { exact: true })
    .fill(`Cabaña asistente ${info.project.name}`)
  const properties = await (await page.request.get('/api/v1/properties/')).json()
  await page.getByLabel('Cabaña', { exact: true }).selectOption(properties.results[0].id)
  await page.getByLabel('Buscar huésped', { exact: true }).fill('Persona ficticia IA')
  await expect(page.getByLabel('Huésped principal').locator('option')).toHaveCount(2)
  await page.getByLabel('Huésped principal').selectOption({ index: 1 })
  await page.getByLabel('Entrada', { exact: true }).fill(start)
  await page.getByLabel('Salida (exclusiva)').fill(end)
  await page.getByLabel('Adultos', { exact: true }).fill('2')
  await page.getByLabel('Precio total pactado (CLP)').fill('150000.00')
  await expect(page.getByRole('button', { name: 'Convertir a borrador' })).toBeDisabled()
  await page
    .getByLabel(
      'Revisé huésped, cabaña, fechas, ocupación y precio. Crear un borrador no retiene disponibilidad.',
    )
    .check()
  await page.getByRole('button', { name: 'Convertir a borrador' }).click()
  await expect(page).toHaveURL(/\/reservas\/[0-9a-f-]+$/)
  await expect(page.getByText('Borrador', { exact: true })).toBeVisible()
})
