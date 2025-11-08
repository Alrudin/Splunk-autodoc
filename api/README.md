# Splunk Event Flow Graph - Backend API

FastAPI backend for parsing Splunk configurations and generating event flow graphs.

## Technology Stack

- **Python 3.11+** - Core language
- **FastAPI** - Modern web framework for building APIs
- **SQLAlchemy 2.0** - SQL toolkit and ORM
- **Alembic** - Database migration tool
- **PostgreSQL** (production) / **SQLite** (development) - Database engines
- **Pydantic** - Data validation using Python type annotations

## Development Setup

### Prerequisites

- Python 3.11 or higher
- PostgreSQL (optional, can use SQLite for development)

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

### Configuration

Copy `.env.example` from the deploy directory or set environment variables:

```bash
# Database connection string (use DB_URL, DATABASE_URL, or database_url)
DB_URL=sqlite:///./flow.db
# Or for PostgreSQL:
# DB_URL=postgresql+psycopg://user:password@localhost:5432/splunk_flow
# DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/splunk_flow

# Base path for file storage
STORAGE_ROOT=/data

# Logging level
LOG_LEVEL=info

# CORS allowed origins (comma-separated)
ALLOW_ORIGINS=http://localhost:5173,http://localhost:3000

# Enable SQL query logging (for debugging)
ECHO_SQL=false
```

**Note:** The database URL can be set using any of these environment variables (checked in order):

- `DB_URL` (recommended, used in documentation)
- `DATABASE_URL` (common convention)
- `database_url` (lowercase variant)

### Database Setup

```bash
# Run migrations to create tables
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description of changes"

# View migration history
alembic history
```

### Running the API

#### Development Server (with auto-reload)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Production Server (with Gunicorn)

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000
```

## Testing

```bash
# Run tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html
coverage report

# Linting
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Type checking
mypy app/
```

## API Documentation

Once the server is running, access:

- **Interactive API docs (Swagger UI)**: <http://localhost:8000/docs>
- **Alternative API docs (ReDoc)**: <http://localhost:8000/redoc>
- **OpenAPI specification**: <http://localhost:8000/openapi.json>
- **Health check endpoint**: <http://localhost:8000/healthz>

## Project Structure

```text
app/
├── models/          # SQLAlchemy ORM models
│   ├── base.py      # Declarative base and utilities
│   ├── project.py   # Project model
│   ├── upload.py    # Upload model
│   ├── job.py       # Job model
│   ├── graph.py     # Graph model
│   └── finding.py   # Finding model
├── schemas/         # Pydantic schemas (future)
├── routers/         # FastAPI route handlers (future)
├── services/        # Business logic (future)
├── utils/           # Utility functions (future)
├── migrations/      # Alembic database migrations
│   ├── versions/    # Generated migration files
│   └── env.py       # Alembic environment
├── config.py        # Configuration management
├── database.py      # Database connection and session management
├── healthcheck.py   # Health check endpoints
└── main.py          # FastAPI application (future)
```

## Database Models

The application uses the following core domain models:

### Project

Container for uploads and graphs. Supports labeling for organization (e.g., environment, site).

**Fields**: `id`, `name`, `labels` (JSON array), `created_at`, `updated_at`

### Upload

Uploaded Splunk configuration archive (zip/tar).

**Fields**: `id`, `project_id`, `filename`, `size`, `status`, `storage_uri`, `created_at`, `updated_at`

**Statuses**: `pending`, `processing`, `completed`, `failed`

### Job

Parse/resolve job execution. Processes an upload to generate a graph.

**Fields**: `id`, `upload_id`, `status`, `log`, `started_at`, `finished_at`, `created_at`, `updated_at`

**Statuses**: `pending`, `running`, `finished`, `failed`

### Graph

Generated event flow graph with nodes (inputs/outputs) and edges (pipes).

**Fields**: `id`, `project_id`, `job_id`, `version`, `json_blob`, `meta` (JSON), `created_at`

### Finding

Validation issues discovered during graph analysis.

**Fields**: `id`, `graph_id`, `severity`, `code`, `message`, `context` (JSON), `created_at`

**Severities**: `error`, `warning`, `info`

**Codes**: `DANGLING_OUTPUT`, `UNKNOWN_INDEX`, `UNSECURED_PIPE`, `DROP_PATH`, `AMBIGUOUS_GROUP`

## Docker

Build and run using Docker:

```bash
# Build image
docker build -t splunk-flow-api .

# Run container
docker run -p 8000:8000 -e DB_URL=sqlite:///./flow.db splunk-flow-api

# Or use docker-compose
cd ../deploy
docker-compose up
```

## Documentation

Refer to the main project [README](../README.md) and [specification document](../Specs/Spec.md) for comprehensive documentation on architecture, API design, and features.
