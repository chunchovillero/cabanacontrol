import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// Lazy routes can take longer under concurrent Docker/browser test workloads.
configure({ asyncUtilTimeout: 3000 })

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})
