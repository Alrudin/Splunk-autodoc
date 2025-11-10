import { http, HttpResponse } from 'msw'
import type { Project, Upload, Job, Graph } from '@/types'

// Mock data
const mockProjects: Project[] = [
  { 
    id: 1, 
    name: 'Test Project', 
    labels: ['test'], 
    created_at: '2025-01-01T00:00:00Z', 
    updated_at: '2025-01-01T00:00:00Z' 
  },
]

const mockGraphs: Graph[] = [
  {
    id: 1,
    project_id: 1,
    job_id: 1,
    version: '1.0',
    json_blob: {
      hosts: [{ id: 'h1', roles: ['indexer'], labels: [], apps: [] }],
      edges: [],
      meta: { 
        generator: 'test', 
        generated_at: '2025-01-01T00:00:00Z', 
        host_count: 1, 
        edge_count: 0, 
        source_hosts: ['h1'], 
        traceability: {} 
      }
    },
    meta: {},
    created_at: '2025-01-01T00:00:00Z'
  }
]

export const handlers = [
  // Projects
  http.get('http://localhost:8000/api/v1/projects', () => {
    return HttpResponse.json(mockProjects)
  }),
  
  http.post('http://localhost:8000/api/v1/projects', async ({ request }) => {
    const body = await request.json() as { name: string; labels?: string[] }
    const newProject: Project = { 
      id: Date.now(), 
      ...body, 
      created_at: new Date().toISOString(), 
      updated_at: new Date().toISOString() 
    }
    mockProjects.push(newProject)
    return HttpResponse.json(newProject, { status: 201 })
  }),
  
  http.delete('http://localhost:8000/api/v1/projects/:id', () => {
    return new HttpResponse(null, { status: 204 })
  }),
  
  // Graphs
  http.get('http://localhost:8000/api/v1/graphs/:id', ({ params }) => {
    const graph = mockGraphs.find(g => g.id === Number(params.id))
    if (!graph) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(graph)
  }),
  
  http.get('http://localhost:8000/api/v1/projects/:id/graphs', () => {
    return HttpResponse.json(mockGraphs)
  }),
  
  // Findings
  http.get('http://localhost:8000/api/v1/graphs/:id/findings', () => {
    return HttpResponse.json([])
  }),
  
  // Jobs
  http.get('http://localhost:8000/api/v1/jobs/:id', ({ params }) => {
    return HttpResponse.json({
      id: Number(params.id),
      upload_id: 1,
      status: 'completed',
      log: 'Job completed successfully',
      started_at: '2025-01-01T00:00:00Z',
      finished_at: '2025-01-01T00:00:01Z',
      created_at: '2025-01-01T00:00:00Z'
    })
  }),
]
