# Splunk Event Flow Graph - Claude Code Context

## Project Overview

**Splunk Event Flow Graph** (v2.0.0) is a comprehensive tool to visualize and analyze Splunk data flow from inputs through forwarders to indexes. It parses Splunk configuration snapshots (`$SPLUNK_HOME/etc` directories) and generates interactive topology graphs to identify routing issues, validate data flows, and understand Splunk infrastructure.

### Architecture

**Split architecture** with REST API communication:
- **Backend**: Python 3.11+ FastAPI service with SQLAlchemy ORM and PostgreSQL/SQLite database
- **Frontend**: React 18 SPA with TypeScript, Tailwind CSS, and D3.js/Vis.js for graph visualization
- **Deployment**: Docker-based with docker-compose for development and Kubernetes-ready for production

### Core Workflow

1. User uploads Splunk configuration snapshots (`.zip`/`.tar.gz` containing `etc/` directories)
2. Backend extracts, parses configs with precedence resolution (system/default → app/local)
3. Resolver builds canonical host→host graph showing data flow paths
4. Validator detects issues (dangling outputs, unknown indexes, unsecured pipes, etc.)
5. Frontend renders interactive topology with filters, inspectors, and export capabilities

---

## Technology Stack

### Backend
- **Framework**: FastAPI with Uvicorn/Gunicorn
- **Language**: Python 3.11+
- **ORM**: SQLAlchemy 2.0
- **Database**: PostgreSQL 15 (production) / SQLite (development)
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Graph Export**: Graphviz (dot, PNG, PDF, SVG)

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Graph Visualization**: vis-network (Vis.js)
- **UI Components**: shadcn/ui (Radix UI primitives)
- **Icons**: lucide-react
- **Routing**: React Router v6

### Testing
- **Backend**: pytest, pytest-asyncio, pytest-cov, httpx (for API tests)
- **Frontend**: Vitest, @testing-library/react, MSW (Mock Service Worker), Playwright
- **Coverage**: Both backend and frontend configured with coverage reporting

---

## Project Status (as of fix-test-errors branch)

### Implementation: 95% Complete

**Backend (100% Complete)**: 3,856+ lines
- ✅ All 5 core services implemented (parser, resolver, validator, storage, export)
- ✅ All 4 routers (projects, uploads, jobs, graphs)
- ✅ Complete SQLAlchemy models + Alembic migrations
- ✅ Pydantic v2 schemas for all endpoints
- ✅ Processor orchestration pipeline

**Frontend (100% Complete)**: 3,888+ lines
- ✅ All 4 pages (Projects, Upload, GraphExplorer, Findings)
- ✅ All core components (VisNetworkCanvas, NodeInspector, EdgeInspector, FilterPanel)
- ✅ All hooks (useProjects, useUpload, useJobPolling, useGraph)
- ✅ Zustand state management
- ✅ 16 shadcn/ui components integrated

**Tests (55% Complete)**: 11/20 files
- ✅ Backend unit tests: 5/5 complete (3,883 lines - parser, resolver, validator, storage, export)
- ✅ Backend integration tests: 1/5 complete (test_api_projects.py)
- ⏳ Backend integration tests: 4 files needed (uploads, jobs, graphs, end-to-end)
- ⏳ Frontend tests: 5 files skeleton only (hooks, components, pages tests)
- ⏳ E2E tests: 1 file needed (Playwright upload flow)

### Remaining Work (9 test files)

**Backend Integration Tests** (4 files):
1. `api/tests/integration/test_api_uploads.py` - Upload API endpoints
2. `api/tests/integration/test_api_jobs.py` - Jobs API endpoints
3. `api/tests/integration/test_api_graphs.py` - Graphs/exports API endpoints
4. `api/tests/integration/test_end_to_end.py` - Complete workflow test

**Frontend Tests** (5 files - skeletons exist, need implementation):
5. `frontend/src/hooks/__tests__/useProjects.test.ts`
6. `frontend/src/hooks/__tests__/useJobPolling.test.ts`
7. `frontend/src/components/__tests__/FilterPanel.test.tsx`
8. `frontend/src/pages/__tests__/Projects.test.tsx`
9. `frontend/src/pages/__tests__/Upload.test.tsx`

**E2E Test** (1 file):
10. `frontend/e2e/upload-flow.spec.ts` - Complete user workflow with Playwright

---

## Repository Structure

```
/Users/johan/src/Splunk-autodoc/
├── .venv/                      # Python virtual environment (activated with source .venv/bin/activate)
├── api/                        # Backend (Python/FastAPI)
│   ├── app/
│   │   ├── routers/           # API endpoints (projects, uploads, jobs, graphs)
│   │   ├── services/          # Business logic (parser, resolver, validator, storage, export, processor)
│   │   ├── models/            # SQLAlchemy ORM models (Project, Upload, Job, Graph, Finding)
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── migrations/        # Alembic database migrations (4 files)
│   │   ├── utils/             # Shared utilities
│   │   ├── main.py            # FastAPI app initialization
│   │   ├── config.py          # Pydantic Settings
│   │   ├── database.py        # SQLAlchemy setup
│   │   └── healthcheck.py     # Health endpoints
│   ├── tests/
│   │   ├── unit/              # Unit tests (5 complete: parser, resolver, validator, storage, export)
│   │   ├── integration/       # Integration tests (1/5 complete: test_api_projects.py)
│   │   ├── fixtures/          # Golden Splunk config fixtures (8 scenarios)
│   │   └── conftest.py        # pytest fixtures (db, storage, samples)
│   ├── pyproject.toml         # Python dependencies and config
│   ├── pytest.ini             # pytest configuration with markers
│   └── Dockerfile             # Multi-stage build for Python/FastAPI
│
├── frontend/                   # Frontend (React/TypeScript)
│   ├── src/
│   │   ├── pages/             # Route pages (Projects, Upload, GraphExplorer, Findings)
│   │   ├── components/        # React components + shadcn/ui
│   │   ├── hooks/             # Custom React hooks
│   │   ├── store/             # Zustand state management
│   │   ├── lib/               # Utilities, API client
│   │   ├── types/             # TypeScript type definitions
│   │   └── test/              # Test setup, MSW mocks, utils
│   ├── e2e/                   # Playwright E2E tests (needs implementation)
│   ├── public/                # Static assets
│   ├── package.json           # Node dependencies
│   ├── vite.config.ts         # Vite build configuration
│   ├── vitest.config.ts       # Vitest test configuration
│   ├── playwright.config.ts   # Playwright E2E configuration
│   └── Dockerfile             # Multi-stage build for React SPA
│
├── deploy/                     # Deployment configurations
│   ├── docker-compose.yml     # Orchestrates all services (db, api, frontend)
│   ├── .env.example           # Environment variable template
│   └── k8s/                   # Kubernetes manifests
│
├── samples/                    # Example Splunk configurations for testing
├── Specs/
│   └── Spec.md                # 📘 COMPLETE SYSTEM SPECIFICATION (source of truth)
├── phase-breakdown.md          # Main implementation tasks (11 tasks)
├── test-phase-breakdown.md     # Test implementation tasks (13 tasks)
├── TEST_IMPLEMENTATION_PROGRESS.md  # Detailed test status tracking
└── README.md                   # Setup, usage, deployment guide
```

---

## Development Environment Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker 20.10+ and docker-compose 2.0+ (for containerized development)
- PostgreSQL 14+ (optional, can use SQLite for development)

### Initial Setup

**Backend:**
```bash
# Virtual environment is already created at .venv/
# Always activate it before working with Python code
cd /Users/johan/src/Splunk-autodoc
source .venv/bin/activate

# Install/update dependencies
cd api
pip install -e ".[dev]"

# Verify installation
pytest --version
ruff --version
```

**Frontend:**
```bash
cd /Users/johan/src/Splunk-autodoc/frontend
npm install

# Verify installation
npm run test -- --version
```

---

## Development Workflows

### Backend Development

**Always activate virtual environment first:**
```bash
cd /Users/johan/src/Splunk-autodoc
source .venv/bin/activate
cd api
```

**Run development server:**
```bash
# Using uvicorn directly
uvicorn app.main:app --reload --port 8000

# Or using the processor module for job testing
python -m app.services.processor
```

**Run tests:**
```bash
# Run all tests
pytest

# Run only unit tests (fast)
pytest -m unit

# Run only integration tests
pytest -m integration

# Run with coverage report
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_parser.py

# Run specific test class or method
pytest tests/unit/test_parser.py::TestPrecedenceResolution::test_system_local_overrides_default

# Skip slow tests
pytest -m "not slow"

# Skip tests requiring Graphviz (if not installed)
pytest -m "not requires_graphviz"

# Verbose output
pytest -v

# Show print statements
pytest -s
```

**Linting and type checking:**
```bash
# Lint with ruff
ruff check .

# Format with ruff
ruff format .

# Type checking with mypy
mypy app
```

**Database migrations:**
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Frontend Development

```bash
cd /Users/johan/src/Splunk-autodoc/frontend

# Run development server (port 5173)
npm run dev

# Run tests
npm test                    # Interactive watch mode
npm run test:run            # Run once (CI mode)
npm run test:ui             # Vitest UI
npm run test:coverage       # With coverage report

# Run E2E tests with Playwright
npm run test:e2e            # Headless
npm run test:e2e:ui         # Interactive UI

# Linting
npm run lint
npm run lint:fix

# Build for production
npm run build
npm run preview             # Preview production build
```

### Docker Development

```bash
cd /Users/johan/src/Splunk-autodoc/deploy

# Start all services (PostgreSQL, API, Frontend)
docker compose up --build

# Access points:
# - Frontend: http://localhost:8080
# - API docs: http://localhost:8000/docs
# - API health: http://localhost:8000/healthz

# View logs
docker compose logs -f api
docker compose logs -f frontend

# Rebuild specific service
docker compose build api
docker compose up -d api

# Run tests in container
docker compose exec api pytest

# Access database
docker compose exec db psql -U flow -d flow

# Stop services
docker compose down

# Reset everything (WARNING: deletes data)
docker compose down -v
```

---

## Testing Infrastructure

### Backend Testing (pytest)

**Test Organization:**
- `tests/unit/` - Service layer unit tests (parser, resolver, validator, storage, export)
- `tests/integration/` - API endpoint integration tests
- `tests/fixtures/` - Golden Splunk configuration samples
- `tests/conftest.py` - Shared pytest fixtures

**pytest Markers** (defined in `pytest.ini`):
- `@pytest.mark.unit` - Fast unit tests (no DB, no network)
- `@pytest.mark.integration` - API tests with TestClient and DB
- `@pytest.mark.slow` - Tests that take >1 second
- `@pytest.mark.requires_graphviz` - Tests needing Graphviz installed

**Key Fixtures** (from `conftest.py`):

```python
# Database fixtures
test_db          # In-memory SQLite engine
test_db_session  # Session with auto-rollback after each test
temp_storage_root  # Temporary directory for file operations

# Sample model fixtures
sample_project   # Project instance in test DB
sample_upload    # Upload instance in test DB
sample_job       # Job instance in test DB
sample_graph     # Graph instance in test DB
sample_finding   # Finding instance in test DB
```

**Golden Config Fixtures** (from `tests/fixtures/splunk_configs.py`):

These create realistic Splunk configuration directories for testing:

```python
create_uf_config(tmp_path)                    # Universal Forwarder
create_hf_config(tmp_path)                    # Heavy Forwarder
create_idx_config(tmp_path)                   # Indexer
create_hec_config(tmp_path)                   # HTTP Event Collector
create_indexer_discovery_config(tmp_path)     # Indexer discovery
create_dangling_output_config(tmp_path)       # No outputs (finding)
create_ambiguous_routing_config(tmp_path)     # Multiple groups, no default
create_precedence_test_config(tmp_path)       # All precedence layers
```

**Test Pattern - Unit Tests:**

```python
from pathlib import Path
import pytest
from app.services.parser import parse_splunk_config
from tests.fixtures.splunk_configs import create_uf_config

@pytest.mark.unit
class TestParserFeature:
    def test_parse_uf_inputs(self, tmp_path: Path, temp_storage_root: Path):
        """Test parsing Universal Forwarder inputs.conf."""
        # Setup: Create golden config
        config_dir = create_uf_config(tmp_path)

        # Execute: Parse configuration
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        # Assert: Verify expected behavior
        assert len(parsed.inputs) > 0
        assert parsed.inputs[0].stanza == "[monitor:///var/log/messages]"
        assert parsed.inputs[0].index == "os"
```

**Test Pattern - Integration Tests:**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.database import get_db
from app.models.project import Project

@pytest.fixture
def client(test_db_session: Session):
    """FastAPI test client with database override."""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass  # Let fixture handle cleanup

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.mark.integration
class TestProjectsAPI:
    def test_get_project(self, client: TestClient, sample_project: Project):
        """Test GET /api/v1/projects/{id}."""
        response = client.get(f"/api/v1/projects/{sample_project.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_project.id
        assert data["name"] == sample_project.name
```

### Frontend Testing (Vitest + React Testing Library)

**Test Organization:**
- `src/hooks/__tests__/` - Custom React hooks tests
- `src/components/__tests__/` - Component tests
- `src/pages/__tests__/` - Page component tests
- `src/test/` - Test utilities, MSW mocks, setup

**MSW (Mock Service Worker)** for API mocking:
- Mock handlers defined in `src/test/mocks/handlers.ts`
- Server setup in `src/test/mocks/server.ts`
- Auto-started in `src/test/setup.ts`

**Test Pattern - Hooks:**

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { useProjects } from '@/hooks/useProjects';

describe('useProjects', () => {
  it('should fetch projects on mount', async () => {
    const { result } = renderHook(() => useProjects());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.projects).toHaveLength(2);
    expect(result.current.projects[0].name).toBe('Test Project 1');
  });

  it('should handle create project', async () => {
    const { result } = renderHook(() => useProjects());

    await result.current.createProject('New Project');

    await waitFor(() => expect(result.current.projects).toHaveLength(3));
  });
});
```

**Test Pattern - Components:**

```typescript
import { render, screen, fireEvent } from '@/test/utils';
import { FilterPanel } from '@/components/FilterPanel';

describe('FilterPanel', () => {
  it('should apply role filter', () => {
    const onFilterChange = vi.fn();

    render(<FilterPanel onFilterChange={onFilterChange} />);

    fireEvent.click(screen.getByRole('checkbox', { name: /indexer/i }));

    expect(onFilterChange).toHaveBeenCalledWith({ roles: ['indexer'] });
  });

  it('should clear all filters', () => {
    const onFilterChange = vi.fn();

    render(<FilterPanel onFilterChange={onFilterChange} filters={{ roles: ['indexer'] }} />);

    fireEvent.click(screen.getByText(/clear filters/i));

    expect(onFilterChange).toHaveBeenCalledWith({});
  });
});
```

### E2E Testing (Playwright)

**Test Pattern:**

```typescript
import { test, expect } from '@playwright/test';

test('complete upload workflow', async ({ page }) => {
  await page.goto('http://localhost:5173');

  // Create project
  await page.click('text=New Project');
  await page.fill('input[name="name"]', 'Test Project');
  await page.click('text=Create');

  // Upload file
  await page.click('text=Upload');
  await page.setInputFiles('input[type="file"]', 'samples/uf-hf-idx.zip');
  await page.click('text=Start Upload');

  // Wait for processing
  await expect(page.locator('text=completed')).toBeVisible({ timeout: 30000 });

  // View graph
  await page.click('text=View Graph');
  await expect(page.locator('canvas')).toBeVisible();

  // Export
  await page.click('text=Export');
  await page.click('text=DOT');
  const download = await page.waitForEvent('download');
  expect(download.suggestedFilename()).toContain('.dot');
});
```

---

## Code Patterns & Conventions

### Backend Patterns

**1. Pydantic Settings (config.py):**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_url: str = "sqlite:///./flow.db"
    storage_root: Path = Path("/data")

    model_config = {"env_file": ".env"}
```

**2. SQLAlchemy Models (models/):**
```python
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    uploads = relationship("Upload", back_populates="project", cascade="all, delete-orphan")
```

**3. Pydantic Schemas (schemas/):**
```python
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    labels: list[str] = Field(default_factory=list)

class ProjectResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}  # For SQLAlchemy models
```

**4. FastAPI Routers (routers/):**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.project import ProjectCreate, ProjectResponse
from app.models.project import Project

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project."""
    project = Project(name=data.name, labels=data.labels)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
```

**5. Service Layer (services/):**
```python
from pathlib import Path
from app.models.job import Job

def parse_splunk_config(job_id: int, work_dir: Path) -> ParsedConfig:
    """Parse Splunk configuration with precedence resolution."""
    # Implementation with proper error handling
    try:
        # Parse inputs.conf, outputs.conf, props.conf, transforms.conf
        parsed = _parse_with_precedence(work_dir)
        return parsed
    except Exception as e:
        logger.error(f"Failed to parse config for job {job_id}: {e}")
        raise
```

### Frontend Patterns

**1. Custom Hooks (hooks/):**
```typescript
import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import type { Project } from '@/types/api';

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    apiClient.get('/projects')
      .then(setProjects)
      .catch(setError)
      .finally(() => setIsLoading(false));
  }, []);

  return { projects, isLoading, error };
}
```

**2. Zustand Store (store/):**
```typescript
import { create } from 'zustand';

interface FilterState {
  roles: string[];
  indexes: string[];
  setRoles: (roles: string[]) => void;
  clearFilters: () => void;
}

export const useFilterStore = create<FilterState>((set) => ({
  roles: [],
  indexes: [],
  setRoles: (roles) => set({ roles }),
  clearFilters: () => set({ roles: [], indexes: [] }),
}));
```

**3. Component Patterns:**
```typescript
import { Button } from '@/components/ui/button';
import { useProjects } from '@/hooks/useProjects';

export function Projects() {
  const { projects, isLoading, error } = useProjects();

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {projects.map(project => (
        <div key={project.id}>{project.name}</div>
      ))}
    </div>
  );
}
```

### Type Safety

**Backend:**
- Use type hints everywhere: `def func(x: int) -> str:`
- Enable mypy strict mode
- Pydantic v2 for runtime validation

**Frontend:**
- TypeScript strict mode enabled
- Define types in `src/types/`
- Use `interface` for object shapes, `type` for unions/primitives

---

## Key Files Reference

### Essential Documentation (READ THESE FIRST)

1. **Specs/Spec.md** (13,748 bytes)
   - Complete system specification
   - Architecture diagrams
   - API contracts
   - Data models
   - Business logic details
   - **This is the source of truth for all implementation decisions**

2. **README.md** (15,049 bytes)
   - Setup instructions
   - Technology stack
   - Docker quick start
   - Testing guide
   - Deployment checklist

3. **TEST_IMPLEMENTATION_PROGRESS.md** (9,872 bytes)
   - Current test completion status (11/20 files)
   - Test patterns and conventions
   - Remaining work breakdown
   - Implementation notes

4. **phase-breakdown.md** (8,116 bytes)
   - 11 main implementation tasks with file references
   - Tasks 1-11 are all complete

5. **test-phase-breakdown.md** (9,522 bytes)
   - 13 test implementation tasks
   - Tasks 1-6 complete (backend unit tests + fixtures)
   - Tasks 7-13 remaining (integration + frontend tests)

### Configuration Files

- `api/pytest.ini` - pytest markers and configuration
- `api/pyproject.toml` - Python dependencies, tool configs
- `frontend/vitest.config.ts` - Vitest configuration
- `frontend/playwright.config.ts` - Playwright configuration
- `deploy/docker-compose.yml` - Docker orchestration
- `deploy/.env.example` - Environment variables template

---

## Common Development Tasks

### Running the Full Stack Locally

```bash
# Terminal 1: Backend
cd /Users/johan/src/Splunk-autodoc
source .venv/bin/activate
cd api
uvicorn app.main:app --reload

# Terminal 2: Frontend
cd /Users/johan/src/Splunk-autodoc/frontend
npm run dev

# Access:
# - Frontend: http://localhost:5173
# - Backend API docs: http://localhost:8000/docs
```

### Running Tests Before Committing

```bash
# Backend tests (activate venv first!)
cd /Users/johan/src/Splunk-autodoc
source .venv/bin/activate
cd api
pytest -m unit                    # Fast unit tests
pytest -m integration             # Integration tests
pytest --cov=app --cov-report=term-missing  # Coverage report

# Frontend tests
cd /Users/johan/src/Splunk-autodoc/frontend
npm run test:run
npm run lint
```

### Creating a New Backend Test File

```bash
cd /Users/johan/src/Splunk-autodoc
source .venv/bin/activate
cd api

# Create test file following the pattern
# See tests/integration/test_api_projects.py for integration test pattern
# See tests/unit/test_parser.py for unit test pattern

# Run new test
pytest tests/integration/test_api_uploads.py -v
```

### Creating a New Frontend Test File

```bash
cd /Users/johan/src/Splunk-autodoc/frontend

# Create test file following the pattern
# See src/test/utils.tsx for test utilities
# See src/test/mocks/handlers.ts for MSW mocks

# Run new test
npm test -- src/hooks/__tests__/useProjects.test.ts
```

### Debugging Failed Tests

```bash
# Backend: Show print statements and verbose output
cd /Users/johan/src/Splunk-autodoc
source .venv/bin/activate
cd api
pytest tests/unit/test_parser.py -v -s

# Frontend: Run Vitest UI for interactive debugging
cd /Users/johan/src/Splunk-autodoc/frontend
npm run test:ui
```

### Adding a New API Endpoint

1. Define Pydantic schemas in `api/app/schemas/`
2. Add endpoint to appropriate router in `api/app/routers/`
3. Implement business logic in `api/app/services/` if needed
4. Write integration test in `api/tests/integration/`
5. Update OpenAPI documentation (auto-generated from FastAPI)

### Adding a New Frontend Component

1. Create component in `frontend/src/components/`
2. Add types to `frontend/src/types/` if needed
3. Create test file in `frontend/src/components/__tests__/`
4. Update parent component/page to use new component
5. Add to Storybook if complex (optional)

---

## Important Notes for Claude Code

### When Working with This Project:

1. **Always activate the virtual environment** before running Python commands:
   ```bash
   source /Users/johan/src/Splunk-autodoc/.venv/bin/activate
   ```

2. **Specs/Spec.md is the source of truth** - refer to it for:
   - API endpoint specifications
   - Data model schemas
   - Business logic requirements
   - Graph canonical format

3. **Follow established test patterns**:
   - Backend unit tests: Use golden config fixtures from `tests/fixtures/splunk_configs.py`
   - Backend integration tests: Use DB override pattern from `test_api_projects.py`
   - Frontend tests: Use MSW mocks from `src/test/mocks/handlers.ts`

4. **Use pytest markers appropriately**:
   - `@pytest.mark.unit` for fast, isolated tests
   - `@pytest.mark.integration` for API tests with DB
   - `@pytest.mark.slow` for tests >1 second
   - `@pytest.mark.requires_graphviz` for export tests

5. **Test coverage is important**:
   - Backend unit tests: 100% coverage achieved
   - Integration tests: Need 4 more files
   - Frontend tests: Need 5 implementations + 1 E2E

6. **Type safety is enforced**:
   - Backend: mypy strict mode, type hints required
   - Frontend: TypeScript strict mode enabled
   - Pydantic v2 for runtime validation

7. **Git workflow**:
   - Current branch: fix-test-errors (or main)
   - Commit messages follow conventional commits
   - PR reviews required before merge

8. **Don't modify these files** (already complete and tested):
   - All files in `api/app/services/`
   - All files in `api/app/routers/`
   - All files in `api/app/models/`
   - All files in `api/tests/unit/`
   - All files in `frontend/src/pages/`
   - All files in `frontend/src/components/` (except tests)

9. **Focus areas** (what needs work):
   - Backend integration tests (4 files)
   - Frontend tests (5 files)
   - E2E tests (1 file)

10. **Performance considerations**:
    - Graph rendering targets: 2k hosts / 20k edges < 5s
    - Filter interactions < 200ms
    - Use streaming for large file uploads
    - Gzip over wire for graph JSON

---

## Quick Reference Commands

```bash
# Activate venv (ALWAYS DO THIS FIRST for Python work)
source /Users/johan/src/Splunk-autodoc/.venv/bin/activate

# Backend tests
cd /Users/johan/src/Splunk-autodoc/api
pytest                              # All tests
pytest -m unit                      # Unit tests only
pytest -m integration               # Integration tests only
pytest --cov=app                    # With coverage
pytest -k test_parser               # Specific test pattern
pytest -v -s                        # Verbose with print statements

# Frontend tests
cd /Users/johan/src/Splunk-autodoc/frontend
npm test                            # Interactive watch mode
npm run test:run                    # CI mode (run once)
npm run test:ui                     # Vitest UI
npm run test:coverage               # With coverage
npm run test:e2e                    # Playwright E2E

# Linting
cd /Users/johan/src/Splunk-autodoc/api && ruff check . && mypy app
cd /Users/johan/src/Splunk-autodoc/frontend && npm run lint

# Development servers
cd /Users/johan/src/Splunk-autodoc/api && uvicorn app.main:app --reload
cd /Users/johan/src/Splunk-autodoc/frontend && npm run dev

# Docker (all services)
cd /Users/johan/src/Splunk-autodoc/deploy && docker compose up --build
```

---

## Project Health Indicators

✅ **Healthy:**
- All backend core services implemented and tested
- All frontend pages and components implemented
- Database migrations in place
- CI/CD pipeline configured
- Docker deployment ready
- Comprehensive documentation

⚠️ **Needs Attention:**
- Backend integration tests: 4/5 files needed (80% complete)
- Frontend tests: 5 files skeleton only (0% implementation)
- E2E tests: 1 file needed (0% implementation)
- Overall test coverage: 55% (target: 90%+)

🎯 **Next Steps:**
1. Implement remaining 4 backend integration tests
2. Implement 5 frontend test files
3. Implement 1 Playwright E2E test
4. Achieve >90% test coverage
5. Performance testing for large graphs
6. Security audit before production deployment

---

**Last Updated**: 2025-11-15 (based on fix-test-errors branch status)
