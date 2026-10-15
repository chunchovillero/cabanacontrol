import { submitLogin } from './login'
import { createHmac, randomUUID } from 'node:crypto'
import { expect, test } from '@playwright/test'

test('staff recibe texto firmado, revisa consulta y autoriza respuesta simulada con baja', async ({
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
    .fill(`e2e-whatsapp-${info.project.name}@example.invalid`)
  await page.getByLabel('Contraseña', { exact: true }).fill('E2E-fictional-passphrase-2026!')
  await submitLogin(page)
  await page
    .getByRole('button', { name: new RegExp(`Seleccionar Empresa WhatsApp ${info.project.name}`) })
    .last()
    .click()
  await expect(page.getByRole('region', { name: 'Empresa activa' })).toContainText(
    'Empresa WhatsApp',
  )
  const session = await (await page.request.get('/api/v1/auth/me/')).json()
  const tenant = session.active_tenant
  const identity = BigInt(`0x${tenant.id.replaceAll('-', '')}`)
  async function incoming(text: string) {
    const body = JSON.stringify({
      object: 'whatsapp_business_account',
      entry: [
        {
          id: identity.toString(),
          changes: [
            {
              field: 'messages',
              value: {
                metadata: { phone_number_id: (identity + 1n).toString() },
                messages: [
                  {
                    id: `wamid.e2e.${randomUUID()}`,
                    from: '999000000002',
                    timestamp: String(Math.floor(Date.now() / 1000)),
                    type: 'text',
                    text: { body: text },
                  },
                ],
              },
            },
          ],
        },
      ],
    })
    const signature =
      'sha256=' +
      createHmac('sha256', 'e2e-whatsapp-app-secret-not-real').update(body).digest('hex')
    const response = await page.request.post('/webhooks/whatsapp/', {
      data: body,
      headers: { 'Content-Type': 'application/json', 'X-Hub-Signature-256': signature },
    })
    expect(response.status()).toBe(200)
  }
  const question = `Consulta ficticia ${randomUUID()}: dos personas, fechas por indicar.`
  await incoming(question)
  await page.goto('/whatsapp')
  await expect(
    page.getByText('WhatsApp simulado · Datos ficticios · Sin envíos reales'),
  ).toBeVisible()
  await expect(page.getByText('Configuración administrativa')).toHaveCount(0)
  await expect(page.getByRole('link', { name: '+999000000002' })).toBeVisible({ timeout: 15000 })
  await page.getByRole('link', { name: '+999000000002' }).click()
  await expect(page.getByText(question, { exact: true })).toBeVisible({ timeout: 15000 })
  const queryLink = page
    .getByRole('link', { name: 'Revisar consulta y preparar borrador de reserva' })
    .first()
  const queryPath = await queryLink.getAttribute('href')
  expect(queryPath).toMatch(/^\/consultas\/[0-9a-f-]{36}$/)
  const inquiry = await (
    await page.request.get(`/api/v1/inquiries/${queryPath!.split('/').at(-1)}/`)
  ).json()
  expect(inquiry.channel).toBe('whatsapp_api')
  expect(inquiry.extraction).toEqual({})
  await page
    .getByLabel('Origen del permiso o motivo de baja')
    .fill('Permiso ficticio registrado por operador')
  await page.getByRole('button', { name: 'Registrar permiso', exact: true }).click()
  await page.getByRole('button', { name: 'Preparar respuesta manual' }).click()
  const responseText = `Respuesta ficticia revisada ${randomUUID()}`
  await page.getByLabel('Respuesta para revisar').fill(responseText)
  const send = page.getByRole('button', { name: 'Autorizar envío de respuesta' })
  await expect(send).toBeDisabled()
  await page
    .getByLabel('Revisé destinatario, contenido y permiso. Autorizar esta respuesta.')
    .check()
  await expect(send).toBeEnabled()
  await send.click()
  await expect(page.getByText(responseText, { exact: true }).locator('..')).toContainText(
    'Aceptado por proveedor',
    { timeout: 15000 },
  )
  await incoming('BAJA')
  const conversationId = new URL(page.url()).pathname.split('/').at(-1)
  await expect
    .poll(
      async () => {
        const response = await page.request.get(`/api/v1/whatsapp/conversations/${conversationId}/`)
        return (await response.json()).consent_granted
      },
      { timeout: 15000 },
    )
    .toBe(false)
  await expect(page.getByText('BAJA', { exact: true }).first()).toBeVisible({ timeout: 15000 })
  await page.getByLabel('Respuesta para revisar').fill('No debe enviarse sin nuevo permiso')
  await page
    .getByLabel('Revisé destinatario, contenido y permiso. Autorizar esta respuesta.')
    .check()
  await expect(send).toBeDisabled()
})
