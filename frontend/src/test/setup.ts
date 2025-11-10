import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'
import './mocks/server'

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock window.APP_CONFIG for tests
if (typeof window !== 'undefined') {
  window.APP_CONFIG = {
    API_BASE_URL: 'http://localhost:8000/api/v1'
  }
}
