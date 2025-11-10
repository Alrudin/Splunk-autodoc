import { type ReactElement } from 'react'
import { render, type RenderOptions } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { useStore } from '@/store'

interface CustomRenderOptions extends RenderOptions {
  initialRoute?: string
}

// Custom render function with providers
export function renderWithProviders(
  ui: ReactElement,
  { initialRoute = '/', ...renderOptions }: CustomRenderOptions = {}
) {
  // Reset Zustand store before each test
  useStore.setState({
    currentProject: null,
    projects: [],
    currentGraph: null,
    findings: [],
    isLoading: false,
    error: null,
    filters: {},
  })

  // Set initial route if provided
  if (initialRoute !== '/') {
    window.history.pushState({}, '', initialRoute)
  }

  function Wrapper({ children }: { children: React.ReactNode }) {
    return <BrowserRouter>{children}</BrowserRouter>
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions })
}

// Re-export everything from React Testing Library
export * from '@testing-library/react'
export { renderWithProviders as render }
