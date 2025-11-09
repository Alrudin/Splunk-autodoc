# Phase Breakdown

## Task 1: Implement FastAPI Application Core and Project/Upload/Job Routers

Create `app/main.py` with FastAPI app initialization, CORS middleware, and router registration
Implement `app/routers/projects.py` with CRUD endpoints for projects (POST, GET, PATCH, DELETE)
Implement `app/routers/uploads.py` with upload creation endpoint (POST /projects/{id}/uploads)
Implement `app/routers/jobs.py` with job creation and status endpoints (POST /uploads/{id}/jobs, GET /jobs/{id})
Register all routers and include healthcheck router from `app/healthcheck.py`

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/app/config.py`
- `/Users/johan/src/Splunk-autodoc/api/app/database.py`
- `/Users/johan/src/Splunk-autodoc/api/app/healthcheck.py`
- `/Users/johan/src/Splunk-autodoc/api/app/models/project.py`
- `/Users/johan/src/Splunk-autodoc/api/app/models/upload.py`
- `/Users/johan/src/Splunk-autodoc/api/app/models/job.py`


## Task 2: Create Pydantic Schemas for API Request/Response Validation

Create `app/schemas/` directory with `__init__.py`
Implement schemas for Project (ProjectCreate, ProjectUpdate, ProjectResponse)
Implement schemas for Upload (UploadCreate, UploadResponse)
Implement schemas for Job (JobCreate, JobResponse, JobStatus)
Implement schemas for Graph (GraphResponse, HostSchema, EdgeSchema) and Finding (FindingResponse)
Include proper validation, field descriptions, and examples per spec section 11

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/app/models/project.py`
- `/Users/johan/src/Splunk-autodoc/api/app/models/upload.py`
- `/Users/johan/src/Splunk-autodoc/api/app/models/job.py`
- `/Users/johan/src/Splunk-autodoc/api/app/models/graph.py`
- `/Users/johan/src/Splunk-autodoc/api/app/models/finding.py`
- `/Users/johan/src/Splunk-autodoc/Specs/Spec.md`


## Task 3: Implement Storage Service and File Upload Handling

Create `app/services/storage.py` with functions for saving uploaded files, extracting archives (.zip/.tar.gz), and managing storage paths
Implement safe path validation and extraction with security checks (no path traversal)
Create directory structure management for `/data/artifacts/{upload_id}/`, `/data/work/{job_id}/`, `/data/graphs/`, `/data/exports/`
Add file cleanup utilities and storage URI generation
Handle multipart file uploads in upload router using this service

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/app/config.py`
- `/Users/johan/src/Splunk-autodoc/api/app/models/upload.py`
- `/Users/johan/src/Splunk-autodoc/Specs/Spec.md`


## Task 4: Implement Splunk Configuration Parser Service

- Create \`app/services/parser.py\` with functions to parse Splunk conf files (inputs.conf, outputs.conf, props.conf, transforms.conf)
- Implement precedence resolution logic (system/default &lt; system/local &lt; app/default &lt; app/local)
- Parse all input types: monitor://, WinEventLog:, tcp://, udp://, splunktcp://, http/HEC, script://, modular inputs
- Parse outputs.conf: tcpout groups, defaultGroup, indexer discovery, SSL/TLS settings
- Parse props.conf and transforms.conf: TRANSFORMS-\* evaluation, \_MetaData:Index, sourcetype rewrites, nullQueue
- Return structured data (dicts/dataclasses) representing parsed configurations per spec section 4.3


Relevant Files:

\- `/Users/johan/src/Splunk-autodoc/Specs/Spec.md`


## Task 5: Implement Graph Resolver and Canonical Graph Builder

Create `app/services/resolver.py` to build canonical graph from parsed Splunk configs
Implement host-to-host edge resolution using inputs and outputs
Build Host objects with roles, labels, apps per spec section 4.2
Build Edge objects with src_host, dst_host, protocol, sources, sourcetypes, indexes, filters, TLS, weight, confidence
Apply heuristics for unknown targets and ambiguous routing
Generate graph metadata (generator, generated_at, counts, traceability)
Serialize to canonical JSON format and store in Graph model

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/app/models/graph.py`
- `/Users/johan/src/Splunk-autodoc/api/app/models/job.py`
- `/Users/johan/src/Splunk-autodoc/Specs/Spec.md`


## Task 6: Implement Validation Service and Finding Generation

Create `app/services/validator.py` with validation rules for generated graphs
Implement finding detection: DANGLING_OUTPUT, UNKNOWN_INDEX, UNSECURED_PIPE, DROP_PATH, AMBIGUOUS_GROUP per spec section 4.4
Generate Finding records with severity (error/warning/info), code, message, and context
Store findings in database linked to graph_id
Provide re-validation endpoint logic for POST /graphs/{graph_id}/validate

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/app/models/finding.py`
- `/Users/johan/src/Splunk-autodoc/api/app/models/graph.py`
- `/Users/johan/src/Splunk-autodoc/Specs/Spec.md`


## Task 7: Implement Graph and Finding API Endpoints with Export Functionality

Create `app/routers/graphs.py` with endpoints: GET /projects/{id}/graphs, GET /graphs/{id}, GET /graphs/{id}/findings, GET /graphs/{id}/query
Implement `app/services/export.py` for graph exports: DOT, JSON, PNG, PDF formats
Add GET /graphs/{id}/exports?format=dot|json|png|pdf endpoint
Implement server-side filtering for query endpoint (host, index, protocol filters)
Use Graph and Finding models, return proper schemas

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/app/models/graph.py`
- `/Users/johan/src/Splunk-autodoc/api/app/models/finding.py`
- `/Users/johan/src/Splunk-autodoc/Specs/Spec.md`


## Task 8: Setup Frontend React Application with Routing and State Management

Create `frontend/src/` directory structure: components/, pages/, hooks/, lib/, types/
Setup React Router v6 with routes for Projects, Upload, Graph Explorer, Findings
Configure Zustand store for global state (current project, graph data, filters)
Create API client utility using fetch with base URL from config.js
Setup Tailwind CSS and shadcn/ui component library
Create main App.tsx, index.html, and vite.config.ts

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/frontend/package.json`
- `/Users/johan/src/Splunk-autodoc/frontend/Dockerfile`
- `/Users/johan/src/Splunk-autodoc/Specs/Spec.md`


## Task 9: Implement Frontend Project Management and Upload Flow UI

Create Projects page with list/create/delete functionality using API client
Implement Upload page with drag-drop file upload (react-dropzone or native)
Show upload progress and job status polling (GET /jobs/{id})
Display job logs and link to generated graph on completion
Use shadcn/ui components (Dialog, Button, Table, Toast) and lucide-react icons
Integrate with Zustand store for state management

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/Specs/Spec.md`


## Task 10: Implement Frontend Graph Visualization with D3/Vis.js

Create Graph Explorer page with D3.js or Vis.js force-directed graph rendering
Implement topology view (nodes=hosts, edges=flows) with zoom, pan, minimap
Add hierarchical layout option (left→right: inputs→HFs→indexers)
Implement node/edge styling: color by protocol/role, edge thickness by weight, TLS indicators
Create search and filter UI (host, app, index, sourcetype, protocol, TLS, role)
Implement node inspector panel (roles, apps, inputs, outputs) and edge inspector (sources, sourcetypes, indexes, transforms, findings)
Add performance optimizations for 2k hosts / 20k edges per spec section 5.1

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/frontend/package.json`
- `/Users/johan/src/Splunk-autodoc/Specs/Spec.md`


## Task 11: Implement Frontend Findings Table and Export Functionality

Create Findings page with table displaying severity, code, message, context
Add filtering by severity and code, with quick links to highlight affected nodes/edges in graph
Implement export functionality: trigger API calls to GET /graphs/{id}/exports?format=dot|json|png|pdf
Add export buttons to Graph Explorer with format selection (PNG, PDF, DOT, JSON)
Handle file downloads and show progress/success notifications
Use shadcn/ui Table, Select, and Toast components

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/Specs/Spec.md`