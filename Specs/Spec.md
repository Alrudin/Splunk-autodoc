# Splunk Event Flow Graph – System Spec (Frontend + Backend, Dockerized) v2.0

## 1) Goal & Scope

**Goal:** Ingest one or more Splunk `$SPLUNK_HOME/etc` directory snapshots and generate an accurate, explorable graph that shows how events travel **from inputs on hosts → (optional forwarders/HFs/routers) → indexes**.

**Split architecture:**  

- **Frontend (Web UI):** Upload data, browse the topology graph, filter/search, inspect nodes/edges, export views.  
- **Backend (API, Python):** Parse/merge Splunk conf, resolve flows, persist graph + findings, serve them over REST, manage uploads/jobs/exports.

**Primary use cases:** Troubleshooting routing, auditing architecture, impact analysis for transforms/props changes, and documentation/export.

---

## 2) High-Level Architecture

```
+-----------------------+        REST/JSON        +--------------------------+
|      Frontend         |  <--------------------> |        Backend API       |
| React + TS + D3/Vis   |                         | Python (FastAPI)         |
| Upload UI, Graph UI   |                         | - Uploads / Jobs         |
| Filters, Exports      |                         | - Parser & Resolver      |
+-----------+-----------+                         | - Store (Postgres/SQLite)|
            |                                      | - Exports (PNG/DOT/JSON) |
            v                                      +------------+-------------+
    Object storage / volume (uploaded zips)                      |
                                                                 v
                                                     Persistent volumes / DB
```

**Containers:**  

- `frontend` (Node build + nginx runtime)  
- `api` (Python/FastAPI + worker)  
- `db` (Postgres; SQLite allowed for single-container dev)  
- `minio` or local volume (optional) for upload artifacts

---

## 3) Data Flow

1. **User uploads** one or more `$SPLUNK_HOME/etc` snapshots as `.zip`/`.tar.gz`.  
2. **Backend** stores the artifact, registers a **Job** and unpacks to a working area.  
3. **Parser** merges Splunk configs with precedence; **Resolver** builds a canonical host→host **graph** and **findings**.  
4. **Graph + findings** are saved to the DB as versioned entities.  
5. **Frontend** fetches graphs via REST, renders interactive topology, enables filtering and exports.

---

## 4) Backend (Python, API-Driven)

**Tech:** Python 3.11+, FastAPI, Pydantic, SQLAlchemy, Alembic, Uvicorn/Gunicorn.  
**Optional async processing:** RQ/Celery + Redis (recommended for large inputs). In v2.0 we keep jobs simple; worker runs in same image.

### 4.1 Domain Model (DB)

- **Project**: logical container for one or more uploads/graphs (`id`, `name`, `labels`, `created_at`).  
- **Upload**: artifact record (`id`, `project_id`, `filename`, `size`, `status`, `storage_uri`).  
- **Job**: parse/resolve request (`id`, `upload_id`, `status`, `log`, `started_at`, `finished_at`).  
- **Graph**: versioned canonical structure (`id`, `project_id`, `version`, `json_blob`, `meta`).  
- **Finding**: validation issues linked to a graph (`id`, `graph_id`, `severity`, `code`, `message`, `context`).  

> DB: Postgres 15 in prod; SQLite allowed for local dev.

### 4.2 Canonical Graph JSON

**Hosts:**
```json
{"id":"hf01","roles":["heavy_forwarder"],"labels":["prod","site=eu1"],"apps":["Splunk_TA_nix"]}
```

**Edges:**
```json
{
  "src_host":"uf01","dst_host":"hf01",
  "protocol":"splunktcp","path_kind":"forwarding",
  "sources":["monitor:///var/log/messages"],
  "sourcetypes":["linux:messages"],
  "indexes":["os"],
  "filters":["TRANSFORMS:route_os"],
  "drop_rules":[],
  "tls":true,
  "weight":14,
  "app_contexts":["Splunk_TA_nix"],
  "confidence":"explicit"
}
```

**Meta:** generator, generated_at, counts, source_hosts, traceability pointers (file:line).

### 4.3 Parsing & Resolution (unchanged logic, moved server-side)

- **Inputs:** `inputs.conf` stanzas (monitor://, WinEventLog:, udp://, tcp://, script://, splunktcp://, http/HEC, modular).  
- **Precedence:** `system/default < system/local < app/default < app/local` + app load order.  
- **Props/Transforms:** `TRANSFORMS-*` evaluation order, `_MetaData:Index`, setnull, setparsing, sourcetype rewrites.  
- **Outputs:** groups, defaultGroup, indexer discovery, SSL/TLS.  
- **Heuristics:** placeholder hosts for unknown targets; ambiguity flags; transform wins over input index.

### 4.4 Validation Rules → Findings

- **DANGLING_OUTPUT** (no outputs.conf or unreachable target).  
- **UNKNOWN_INDEX** (edge references index not declared in dest cluster).  
- **UNSECURED_PIPE** (splunktcp/http without TLS).  
- **DROP_PATH** (nullQueue).  
- **AMBIGUOUS_GROUP** (multiple tcpout groups, no defaultGroup).

### 4.5 REST API (FastAPI)

Base: `/api/v1`

**Projects**  

- `POST /projects` → create  
- `GET /projects` / `GET /projects/{id}`  
- `PATCH /projects/{id}` (rename, labels)  
- `DELETE /projects/{id}`

**Uploads & Jobs**  

- `POST /projects/{id}/uploads` (multipart file) → `{upload_id}`  
- `POST /uploads/{upload_id}/jobs` → start parse/resolve  
- `GET /jobs/{job_id}` → status/log  
- `GET /uploads/{upload_id}`

**Graphs & Findings**  

- `GET /projects/{id}/graphs` → list versions  
- `GET /graphs/{graph_id}` → canonical JSON (paged optional)  
- `GET /graphs/{graph_id}/findings`  
- `GET /graphs/{graph_id}/exports?format=dot|json|png|pdf`  
- `POST /graphs/{graph_id}/validate` (re-run rules)  

**Search/Filter**  

- `GET /graphs/{graph_id}/query?host=hf01&index=os&protocol=splunktcp`  
  Returns filtered subgraph (server-side convenience for large sets).

**Auth**  

- Bearer JWT (opaque in dev). API keys optional.  
- CORS enabled for configured FE origin.

**OpenAPI**  

- Auto at `/docs` and `/openapi.json`. Keep response schemas typed via Pydantic.

---

## 5) Frontend (React + TypeScript)

**Tech:** React + Vite, TypeScript, Tailwind, Zustand (state), **D3 or Vis.js** for graph, shadcn/ui, lucide-react, Recharts (if needed).  
**Build:** SPA served by `nginx` container.

### 5.1 Core Views

- **Projects:** list/create/delete; open recent graph version.  
- **Upload:** drag-drop `.zip`/`.tar.gz` (one or multiple hosts). Show parsing job progress and link to result graph.  
- **Graph Explorer:**  
  - **Topology:** force-directed; nodes=hosts; edge thickness=weight; color by protocol or path_kind.  
  - **Hierarchy:** left→right (inputs→HFs→indexers).  
  - **Index overlay:** badges/legend on edges; optional “ghost index nodes” toggle.  
  - **Interaction:** search (host/app/index/sourcetype/source), filters (role, protocol, tls, drop/dangling), minimap, zoom/pan, fit.  
  - **Inspect Node:** roles, apps, inputs summary, outputs/groups, counts.  
  - **Inspect Edge:** sources, sourcetypes, index outcomes, transforms trace, TLS, findings affecting this edge.  
  - **Exports:** PNG/PDF/DOT/JSON of current filtered view.  
- **Findings:** table with severity, code, message, quick filters to highlight affected nodes/edges.

**Performance targets:**  

- 2k hosts / 20k edges initial render < 5s on dev laptop; filter interactions < 200ms.

---

## 6) Storage & Files

- **Artifacts:** stored under `/data/artifacts/{upload_id}/upload.{ext}`; extracted to `/data/work/{job_id}/…`.  
- **Graphs:** DB row + compressed JSON blob (optional externalized to `/data/graphs/{graph_id}.json`).  
- **Exports:** temp files streamed; optional persisted under `/data/exports/{graph_id}/…`.

---

## 7) Containerization & Deployment

### 7.1 Images

- `ghcr.io/org/splunk-flow-frontend:TAG`  
  - Stage 1: Node 20 build → `dist/`  
  - Stage 2: `nginx:alpine` serve `/usr/share/nginx/html`  
- `ghcr.io/org/splunk-flow-api:TAG`  
  - `python:3.11-slim`, installs: fastapi, uvicorn, pydantic, sqlalchemy, alembic, psycopg, (redis + rq/celery optional)  
  - Non-root user, `gunicorn -k uvicorn.workers.UvicornWorker`  
- `postgres:15-alpine` (prod) / `sqlite` (dev single-container)  
- `redis:7-alpine` (optional if async jobs enabled)

### 7.2 docker-compose (prod-like example)

```yaml
version: "3.9"
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: flow
      POSTGRES_USER: flow
      POSTGRES_PASSWORD: flowpass
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck: { test: ["CMD-SHELL","pg_isready -U flow"], interval: 10s, retries: 5 }

  api:
    image: ghcr.io/org/splunk-flow-api:${TAG:-latest}
    environment:
      DB_URL: postgresql+psycopg://flow:flowpass@db:5432/flow
      ALLOW_ORIGINS: http://localhost:5173
      STORAGE_ROOT: /data
      WORKERS: "4"
    depends_on: [db]
    volumes:
      - api-data:/data
    ports: ["8000:8000"]

  frontend:
    image: ghcr.io/org/splunk-flow-frontend:${TAG:-latest}
    depends_on: [api]
    environment:
      API_BASE_URL: http://localhost:8000/api/v1
    ports: ["8080:80"]

volumes:
  db-data:
  api-data:
```

> For single-box **dev**, you can switch to SQLite by setting `DB_URL=sqlite:////data/flow.db` and dropping `db` service.

### 7.3 K8s (outline)

- Deployments for `api` and `frontend`, `StatefulSet` for `db`.  
- PVCs for `/var/lib/postgresql/data` and `/data`.  
- Ingress with TLS; `api` readiness: `/healthz` (DB + storage check).

---

## 8) Security

- **Auth:** JWT bearer; rotate signing key via env; CORS restricted to FE origin(s).  
- **Uploads:** accept only `.zip`/`.tar.gz`; content-type + magic sniff; extract with safe path checks.  
- **Secrets:** never persist `pass4SymmKey`, HEC tokens; redact during parse.  
- **RBAC:** roles `viewer|uploader|admin`; project-scoped permissions.  
- **TLS:** Terminate at ingress / reverse proxy; `Strict-Transport-Security` on FE.

---

## 9) Observability

- **Structured logs (JSON)** in both services.  
- **/metrics** (Prometheus): request duration, job duration, graph size stats.  
- **Tracing** (OTel) optional; job IDs propagate to logs.

---

## 10) CI/CD

- **Lint/Test:** `ruff`, `pytest` (API), `vitest`/`eslint` (FE).  
- **Build:** multi-stage Docker images; tagged by git sha & semver.  
- **Migrations:** `alembic upgrade head` on `api` start.  
- **Security:** `trivy` scan images; `npm audit --omit=dev` for FE.

---

## 11) API Schemas (Pydantic – excerpt)

```python
class Edge(BaseModel):
    src_host: str
    dst_host: str
    protocol: Literal["splunktcp","http_event_collector","syslog","tcp","udp"]
    path_kind: Literal["forwarding","hec","syslog","scripted_input","modinput"]
    sources: list[str] = []
    sourcetypes: list[str] = []
    indexes: list[str] = []
    filters: list[str] = []
    drop_rules: list[str] = []
    tls: bool | None = None
    weight: int = 1
    app_contexts: list[str] = []
    confidence: Literal["explicit","derived"] = "explicit"

class Host(BaseModel):
    id: str
    roles: list[str] = []
    labels: list[str] = []
    apps: list[str] = []

class Graph(BaseModel):
    hosts: list[Host]
    edges: list[Edge]
    meta: dict[str, Any]
```

---

## 12) Frontend Integration (API usage)

- **Upload flow:**  
  - `POST /projects` → `POST /projects/{id}/uploads` (multipart) → `POST /uploads/{upload_id}/jobs` → poll `GET /jobs/{job_id}` until `status=finished` → open `GET /projects/{id}/graphs` latest.  
- **Graph view:**  
  - `GET /graphs/{graph_id}` → feed to D3/Vis.js → client-side filters; fall back to `GET /graphs/{graph_id}/query` for server-side slicing on very large graphs.  
- **Exports:**  
  - Trigger `GET /graphs/{graph_id}/exports?format=dot|json|png|pdf` → download.

---

## 13) Performance & Limits

- **Parsing:** streaming read; no full-file assumption; cap max upload (default 3GB).  
- **Graph size targets:** 2k hosts / 20k edges; JSON kept < 50MB; gzip over wire.  
- **Server:** default 4 workers; job concurrency = CPU count; optional Redis queue for >1 concurrent parse.

---

## 14) Testing & Fixtures

- **Golden etc samples**: UF→HF→IDX, HEC token index override, indexer discovery + SSL, dangling outputs, unknown index, drops.  
- **Unit tests**: parsers, precedence, transforms evaluation, outputs resolution.  
- **API tests**: upload, job lifecycle, graph retrieval, query filters, exports.  
- **FE e2e**: Playwright for upload→graph render→export flow.

---

## 15) Acceptance Criteria (Done = ✅)

- ✅ **API**: OpenAPI available; endpoints above work end-to-end.  
- ✅ **Upload & Job**: large `.zip` accepted; safe unpacking; job logs; timeout/err states.  
- ✅ **Graph**: correct host→host edges; index routing, drops, TLS flags present.  
- ✅ **Findings**: dangling outputs, unknown indexes, unsecured pipes, drops surfaced.  
- ✅ **Frontend**: topology & hierarchical views; filters; node/edge inspectors; exports PNG/PDF/DOT/JSON.  
- ✅ **Dockerized**: `docker compose up` brings FE+API+DB; healthchecks pass.  
- ✅ **Determinism**: same inputs → identical `graph.json` (modulo timestamps).  

---

## 16) Roadmap

- **v2.1**: Background workers (Redis) + cancel/retry; signed artifact uploads.  
- **v2.2**: Diff two graphs (before/after), side-by-side compare.  
- **v2.3**: Optional “Index nodes” mode; volume overlays from `metrics.log`/license CSV.  
- **v2.4**: SSO (OIDC), multi-tenant orgs/projects.

---

## 17) Repo Layout

```
/frontend
  /src (React/TS, D3/Vis, shadcn/ui)
  /public
  vite.config.ts
  package.json
/api
  /app
    main.py (FastAPI)
    routers/ (projects, uploads, jobs, graphs, exports)
    services/ (parse, resolve, validate, storage)
    models/ (sqlalchemy)
    schemas/ (pydantic)
    migrations/ (alembic)
    utils/
  Dockerfile
  pyproject.toml
/deploy
  docker-compose.yml
  k8s/ (manifests)
/samples
  etc_* (fixtures)
/docs
  spec.md (this file)
```
