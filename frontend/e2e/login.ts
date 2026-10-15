import { expect, test, type Page } from '@playwright/test'

// A full suite can exceed the real per-IP login budget. Respect Retry-After;
// never clear throttle buckets, spoof an IP or weaken application settings.
export async function submitLogin(page: Page) {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const [response] = await Promise.all([
      page.waitForResponse(
        (result) =>
          result.url().endsWith('/api/v1/auth/login/') && result.request().method() === 'POST',
      ),
      page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click(),
    ])
    if (response.status() !== 429) {
      expect(response.status()).toBe(200)
      return
    }
    const seconds = Number(response.headers()['retry-after'])
    if (!Number.isFinite(seconds) || seconds < 1 || seconds > 600) {
      throw new Error('Retry-After de autenticación no válido para el ensayo.')
    }
    test.setTimeout(test.info().timeout + (seconds + 5) * 1000)
    console.info(`Autenticación limitada; espera de ${seconds} segundos según Retry-After.`)
    await new Promise((resolve) => setTimeout(resolve, (seconds + 1) * 1000))
  }
  throw new Error('No se pudo iniciar sesión después de respetar los límites.')
}
