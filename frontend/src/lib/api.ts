import { config } from './config'
import type {
  Project,
  CreateProject,
  UpdateProject,
  Upload,
  Job,
  Graph,
  Finding,
  GraphQueryParams,
} from '@/types'

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T | undefined> {
  const url = `${config.API_BASE_URL}${endpoint}`
  
  // Build headers conditionally: don't set Content-Type for FormData
  const headers: Record<string, string> = { ...(options?.headers as Record<string, string>) }
  if (options?.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: response.statusText }))
    throw new ApiError(response.status, error.message || 'Request failed')
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined
  }

  return response.json()
}

export const api = {
  // Projects
  getProjects: () => request<Project[]>('/projects'),
  getProject: (id: number) => request<Project>(`/projects/${id}`),
  createProject: (data: CreateProject) =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),
  updateProject: (id: number, data: UpdateProject) =>
    request<Project>(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteProject: (id: number) => request<void>(`/projects/${id}`, { method: 'DELETE' }),

  // Uploads
  createUpload: (projectId: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request<Upload>(`/projects/${projectId}/uploads`, {
      method: 'POST',
      body: formData,
    })
  },

  // Jobs
  createJob: (uploadId: number) => request<Job>(`/uploads/${uploadId}/jobs`, { method: 'POST' }),
  getJob: (id: number) => request<Job>(`/jobs/${id}`),

  // Graphs
  getProjectGraphs: (projectId: number) => request<Graph[]>(`/projects/${projectId}/graphs`),
  getGraph: (id: number) => request<Graph>(`/graphs/${id}`),
  getGraphFindings: (id: number) => request<Finding[]>(`/graphs/${id}/findings`),
  queryGraph: (id: number, params: GraphQueryParams) => {
    const query = new URLSearchParams()
    // Only append defined values to avoid "undefined" strings in query
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        query.append(key, String(value))
      }
    })
    const queryString = query.toString()
    return request<Graph>(`/graphs/${id}/query${queryString ? `?${queryString}` : ''}`)
  },
  validateGraph: (id: number) => request<Finding[]>(`/graphs/${id}/validate`, { method: 'POST' }),
  exportGraph: (id: number, format: 'dot' | 'json' | 'png' | 'pdf') => {
    return `${config.API_BASE_URL}/graphs/${id}/exports?format=${format}`
  },
}
