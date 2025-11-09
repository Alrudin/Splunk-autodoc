interface AppConfig {
  API_BASE_URL: string
}

declare global {
  interface Window {
    APP_CONFIG?: AppConfig
  }
}

export function getConfig(): AppConfig {
  return {
    API_BASE_URL: window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000/api/v1',
  }
}

export const config = getConfig()
