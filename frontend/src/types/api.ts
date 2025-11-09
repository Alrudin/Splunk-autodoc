// Projects
export interface Project {
  id: number
  name: string
  labels: string[]
  created_at: string
  updated_at: string
}

export interface CreateProject {
  name: string
  labels?: string[]
}

export interface UpdateProject {
  name?: string
  labels?: string[]
}

// Uploads
export interface Upload {
  id: number
  project_id: number
  filename: string
  size: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  storage_uri: string
  created_at: string
}

// Jobs
export interface Job {
  id: number
  upload_id: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  log: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
}

// Graphs
export interface Host {
  id: string
  roles: string[]
  labels: string[]
  apps: string[]
}

export interface Edge {
  src_host: string
  dst_host: string
  protocol: 'splunktcp' | 'http_event_collector' | 'syslog' | 'tcp' | 'udp'
  path_kind: 'forwarding' | 'hec' | 'syslog' | 'scripted_input' | 'modinput'
  sources: string[]
  sourcetypes: string[]
  indexes: string[]
  filters: string[]
  drop_rules: string[]
  tls: boolean | null
  weight: number
  app_contexts: string[]
  confidence: 'explicit' | 'derived'
}

export interface GraphMeta {
  generator: string
  generated_at: string
  host_count: number
  edge_count: number
  source_hosts: string[]
  traceability: Record<string, unknown>
}

export interface CanonicalGraph {
  hosts: Host[]
  edges: Edge[]
  meta: GraphMeta
}

export interface Graph {
  id: number
  project_id: number
  job_id: number
  version: string
  json_blob: CanonicalGraph
  meta: Record<string, unknown>
  created_at: string
}

// Findings
export interface Finding {
  id: number
  graph_id: number
  severity: 'error' | 'warning' | 'info'
  code: string
  message: string
  context: Record<string, unknown>
  created_at: string
}

// Query parameters
export interface GraphQueryParams {
  host?: string
  index?: string
  protocol?: string
}
