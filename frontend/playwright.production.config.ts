import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './production-e2e',
  workers: 1,
  fullyParallel: false,
  reporter: 'list',
  use: {
    baseURL: 'https://localhost:25443',
    // Only this fictional localhost certificate. p_smoke separately verifies its chain/SAN.
    ignoreHTTPSErrors: true,
    trace: 'off',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['iPhone 13'], defaultBrowserType: 'chromium' } },
  ],
})
