import { fileURLToPath, URL } from 'node:url'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  base: process.env.VITE_BASE_PATH ?? '/',
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    watch: { usePolling: process.env.VITE_USE_POLLING === 'true', interval: 500 },
    proxy: Object.fromEntries(
      ['/api', '/health', '/webhooks'].map((path) => [
        path,
        {
          target: process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000',
          changeOrigin: false,
        },
      ]),
    ),
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
