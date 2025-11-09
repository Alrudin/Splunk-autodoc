# Splunk Event Flow Graph - AI Agent Instructions

## Project Overview

This is a **split-architecture application** that parses Splunk configuration snapshots and generates interactive event flow topology graphs. The system traces how data flows from inputs → forwarders → indexes, identifying routing issues and architectural insights.

**Architecture**: React/TypeScript SPA + Python/FastAPI backend + PostgreSQL/SQLite + Docker deployment

## Critical Domain Knowledge

### The Core Problem Domain

This tool analyzes **Splunk configuration files** (`inputs.conf`, `outputs.conf`, `props.conf`, `transforms.conf`) to build a canonical host-to-host graph showing data flow. Understanding Splunk's configuration precedence and routing logic is essential:

- **Precedence order**: `system/default < system/local < app/default < app/local`
- **Index routing**: Determined by input `index=`, `TRANSFORMS-*` rules in props.conf, or `_MetaData:Index` in transforms.conf
- **Output groups**: `tcpout` groups with `defaultGroup`, indexer discovery, SSL/TLS settings
- **Transforms evaluation**: Applied in order; first match wins; can drop to `nullQueue`

The resolver must handle ambiguity (unknown indexes, dangling outputs, placeholder hosts) and generate findings (validation warnings/errors).

## Backend (Python/FastAPI)

### Architecture Patterns

**SQLAlchemy 2.0 ORM models** in `api/app/models/` follow these conventions:
- Use `Mapped[type]` type hints with `mapped_column()` (modern SQLAlchemy 2.0 style)
- Set `model_config = {"from_attributes": True}` for Pydantic compatibility
- Use server defaults: `server_default=func.now()` for timestamps
- Cascade deletes: `ondelete="CASCADE"` on foreign keys, `cascade="all, delete-orphan"` on relationships
- Use `TYPE_CHECKING` for circular import handling with forward references

**Router patterns** in `api/app/routers/`:
- Schemas (Pydantic models) are now defined in separate `api/app/schemas/` modules, not inline in router files (see `projects.py`)
- Use `db: Session = Depends(get_db)` dependency injection (with `# noqa: B008` to suppress ruff warning)
- Return model instances using explicit `response_model=Schema` and function return type hints (e.g., `-> UploadResponse`), with Pydantic schemas configured as `from_attributes=True`
- Standard error handling: try/except with `db.rollback()` on failure, raise `HTTPException` with appropriate status codes
- Use `status.HTTP_*` constants from `fastapi`

**Database session management**:
- `get_db()` generator in `database.py` provides sessions with automatic cleanup
- Call `db.commit()` before `db.refresh()` to get updated model with generated IDs
- Always rollback on exceptions before re-raising

### Key Commands & Workflows

**Run API in development** (from `api/` directory):
```bash
uvicorn app.main:app --reload --port 8000
```

**Database migrations** (Alembic):
```bash
# Create new migration after model changes
alembic revision --autogenerate -m "description"
# Apply migrations
alembic upgrade head
# View history
alembic history
```

**Linting and type checking**:
```bash
ruff check .           # Lint
ruff check --fix .     # Auto-fix
mypy app/              # Type check
```

**Docker build** (from project root):
```bash
cd deploy && docker compose up --build
```

### Configuration

Settings via `app/config.py` using `pydantic-settings`:
- Environment variables are case-insensitive (`.env` file supported)
- Database URL: Use `DB_URL`, `DATABASE_URL`, or `database_url` (checked in order)
- SQLite for dev: `sqlite:///./flow.db`
- PostgreSQL for prod: `postgresql+psycopg://user:pass@host:5432/db`
- Storage root for uploads/work/graphs: `STORAGE_ROOT=/data`

### Service Implementation (Not Yet Complete)

Services in `api/app/services/` will contain business logic:
- **parser.py**: Parse Splunk conf files with precedence resolution
- **resolver.py**: Build canonical graph from parsed configs
- **validator.py**: Generate findings (DANGLING_OUTPUT, UNKNOWN_INDEX, etc.)
- **storage.py**: Handle file uploads, extraction, safe path validation
- **export.py**: Generate DOT/JSON/PNG/PDF exports

**When implementing parsers/resolvers**, refer to `/Specs/Spec.md` sections 4.3 (parsing logic) and 4.2 (canonical graph format).

## Frontend (React/TypeScript)

### Architecture (Planned)

The `frontend/` directory is **currently empty** but will follow these patterns per spec:
- **Vite + React 18 + TypeScript** with strict mode
- **State management**: Zustand store for global state (current project, graph data, filters)
- **Routing**: React Router v6 for Projects, Upload, Graph Explorer, Findings views
- **UI Components**: shadcn/ui (Radix UI primitives) + Tailwind CSS
- **Graph visualization**: D3.js or Vis.js for force-directed/hierarchical layouts
- **API client**: Fetch-based client with base URL from config, typed responses

**Key views to implement**:
1. **Projects**: List/create/delete projects
2. **Upload**: Drag-drop `.zip`/`.tar.gz`, show job progress
3. **Graph Explorer**: Interactive topology with filters, node/edge inspectors, export buttons
4. **Findings**: Table of validation issues with severity filtering

### Frontend Development Commands

```bash
cd frontend
npm install
npm run dev           # Starts on http://localhost:5173
npm run build         # TypeScript compile + Vite build
npm run lint          # ESLint
```

## Docker & Deployment

### Docker Compose Setup

From `deploy/` directory:
```bash
docker compose up --build    # Build and start all services
docker compose down -v       # Stop and remove volumes (deletes data)
docker compose logs -f api   # Follow API logs
```

**Services**:
- `db`: PostgreSQL 15 with `db-data` volume
- `api`: FastAPI with `/data` volume for artifacts/work/graphs/exports
- `frontend`: Nginx serving React SPA
- Health checks on all services

**Environment variables** (see `deploy/.env.example`):
- `DB_URL`: Database connection string
- `ALLOW_ORIGINS`: CORS allowed origins (comma-separated)
- `STORAGE_ROOT`: Base path for file storage
- `WORKERS`: Gunicorn worker count (default 4)

### Dockerfile Patterns

**API Dockerfile** (multi-stage):
- Stage 1: Build with gcc/libpq-dev for Python packages
- Stage 2: Slim runtime with non-root user (`appuser`)
- Gunicorn + uvicorn workers: `CMD gunicorn app.main:app -k uvicorn.workers.UvicornWorker`

**Frontend Dockerfile** (to be created):
- Stage 1: Node.js build with Vite
- Stage 2: Nginx Alpine serving `dist/` → `/usr/share/nginx/html`

## Testing Strategy

**Backend testing** (pytest, not yet implemented):
- Unit tests for parsers, precedence, transforms evaluation
- API tests with FastAPI TestClient for endpoints
- Fixtures: Golden Splunk config samples (UF→HF→IDX scenarios)

**Frontend testing** (to be implemented):
- Vitest for component/unit tests
- Playwright for e2e: upload → graph render → export flow

## Common Patterns & Conventions

### Python Code Style

- **Formatting**: Configured via `ruff` in `pyproject.toml` (line-length 100, Python 3.11+)
- **Type hints**: Use modern syntax (`list[str]`, `dict[str, Any]`, `int | None`)
- **Imports**: Relative imports with `# type: ignore` comments for avoiding circular dependencies during development
- **Docstrings**: Google-style with Args/Returns/Raises sections
- **Error handling**: Explicit try/except with rollback, never bare `except:`

### Database Naming

- Tables: Plural snake_case (`projects`, `uploads`, `jobs`, `graphs`, `findings`)
- Indexes: Prefix with `ix_` (e.g., `ix_projects_name`)
- Foreign keys: Prefix with `fk_` (auto-generated by Alembic)
- Constraints: Use Alembic naming conventions for consistency

### API Conventions

- Base path: `/api/v1`
- RESTful resource naming: `/projects`, `/projects/{id}/uploads`, `/uploads/{id}/jobs`
- Use status codes: 201 Created, 204 No Content, 400 Bad Request, 404 Not Found, 500 Internal Server Error
- Return model instances, not manual dicts
- OpenAPI available at `/docs` (Swagger UI) and `/openapi.json`

### Git & Development Workflow

- Migration files named: `YYYY_MM_DD_HHMM-{hash}_{description}.py`
- Feature implementation follows `/phase-breakdown.md` task list
- Commit before running `alembic revision --autogenerate` to see clean diffs

## Critical Files to Reference

- **`/Specs/Spec.md`**: Complete system specification with API contracts, data models, algorithms
- **`/phase-breakdown.md`**: Detailed task breakdown for implementation phases
- **`api/app/models/`**: Existing ORM models showing relationship patterns
- **`api/app/routers/projects.py`**: Reference router with inline schemas pattern
- **`deploy/docker-compose.yml`**: Full service orchestration example

## What's Implemented vs. Planned

**✅ Implemented**:
- SQLAlchemy models (Project, Upload, Job, Graph, Finding) with migrations
- Basic routers for Projects, Uploads, Jobs (CRUD operations)
- Database setup with Alembic migrations
- Docker multi-stage builds and compose orchestration
- Health check endpoints (`/health`, `/healthz`, `/readyz`)

**🚧 In Progress / Planned**:
- Services layer (parser, resolver, validator, storage, export)
- Complete job processing workflow (parse → resolve → validate → store graph)
- Graph and Finding endpoints with query/filter/export
- Frontend React application (entire `frontend/src/` tree)
- Test suite (pytest for API, Vitest/Playwright for frontend)
- Background job queue (Redis + RQ/Celery planned for v2.1+)

## Development Tips

1. **When adding models**: Create model in `api/app/models/`, import in `database.py`, run `alembic revision --autogenerate`
2. **When adding routers**: Define inline Pydantic schemas, register router in `main.py` with prefix
3. **For Splunk parsing logic**: Always reference precedence rules and transform evaluation order in Spec.md section 4.3
4. **Storage paths**: Use `STORAGE_ROOT` from config, create structure: `/artifacts/{upload_id}`, `/work/{job_id}`, `/graphs/{graph_id}`, `/exports/`
5. **Performance**: Target 2k hosts / 20k edges; compress JSON blobs; stream large files; paginate query results
6. **Security**: Validate file extensions, check magic bytes, safe path extraction (no `../`), redact secrets during parse

## Quick Reference Commands

```bash
# Backend development
cd api
source .venv/bin/activate
uvicorn app.main:app --reload

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Linting and testing
ruff check . && mypy app/
pytest --cov=app

# Docker development
cd deploy
docker compose up --build
docker compose exec api alembic upgrade head

# Frontend (when implemented)
cd frontend
npm run dev
npm run build
```

---

**Remember**: This project parses complex Splunk configurations to generate topology graphs. The "why" behind routing decisions (precedence, transforms, index resolution) must be preserved in the graph's traceability metadata for users to understand the flow.
