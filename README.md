# Splunk Event Flow Graph

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)

A comprehensive tool to visualize and analyze Splunk data flow from inputs through forwarders to indexes. Parse Splunk configuration snapshots and generate interactive topology graphs to identify routing issues, validate data flows, and understand your Splunk infrastructure.

## Overview

Splunk Event Flow Graph automates the analysis of complex Splunk deployments by:

- **Upload Configuration Snapshots**: Import diag/btool outputs from Universal Forwarders, Heavy Forwarders, and Indexers
- **Visualize Data Flow**: Generate interactive topology graphs showing inputs → forwarders → indexes
- **Identify Issues**: Automatically detect dangling outputs, unknown indexes, routing misconfigurations, and missing components
- **Export Diagrams**: Generate reports and diagrams for documentation and troubleshooting

### Architecture

Split architecture with REST API communication:

- **Frontend**: React 18 SPA with TypeScript, Tailwind CSS, and D3.js/Vis.js for graph visualization
- **Backend**: Python 3.11+ FastAPI service with SQLAlchemy ORM and PostgreSQL/SQLite database
- **Deployment**: Docker-based with docker-compose for development and Kubernetes-ready for production

## Technology Stack

### Frontend

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Graph Visualization**: D3.js / Vis.js
- **UI Components**: shadcn/ui (Radix UI primitives)
- **Icons**: lucide-react
- **Routing**: React Router v6

### Backend

- **Framework**: FastAPI
- **Language**: Python 3.11+
- **ORM**: SQLAlchemy 2.0
- **Database**: PostgreSQL (production) / SQLite (development)
- **Migrations**: Alembic
- **Server**: Uvicorn with ASGI
- **Validation**: Pydantic v2

### Deployment

- **Containerization**: Docker
- **Orchestration**: docker-compose / Kubernetes
- **Reverse Proxy**: Nginx (production)

## Docker Quick Start

The fastest way to get the application running is using Docker and docker-compose, which orchestrates all services (PostgreSQL, API, Frontend) in isolated containers.

### Prerequisites

- Docker 20.10+ installed
- docker-compose 2.0+ installed

### Setup Steps

1. **Clone the repository** (if not already done):

   ```bash
   git clone <repository-url>
   cd Splunk-autodoc
   ```

2. **(Optional) Configure environment variables**:

   ```bash
   cd deploy
   cp .env.example .env
   # Edit .env to customize database passwords, worker count, etc.
   ```

3. **Build and start all services**:

   ```bash
   cd deploy
   docker compose up --build
   ```

   This will:
   - Build the API Docker image (Python/FastAPI)
   - Build the Frontend Docker image (React/nginx)
   - Pull PostgreSQL 15 image
   - Create networks and volumes
   - Start all services with health checks

4. **Access the application**:
   - **Frontend**: <http://localhost:8080>
   - **API Documentation**: <http://localhost:8000/docs>
   - **API Health Check**: <http://localhost:8000/healthz>

5. **Stop services**:

   ```bash
   docker compose down
   # To also remove volumes (deletes all data):
   docker compose down -v
   ```

### Docker Development Workflow

**Rebuild a specific service** after code changes:

```bash
docker compose build api        # Rebuild API only
docker compose build frontend   # Rebuild frontend only
docker compose up -d api        # Restart API service
```

**View logs**:

```bash
docker compose logs -f          # All services
docker compose logs -f api      # API only
docker compose logs -f frontend # Frontend only
```

**Execute commands in running containers**:

```bash
# Run tests in API container
docker compose exec api pytest

# Access Python shell
docker compose exec api python

# Run database migrations
docker compose exec api alembic upgrade head
```

**Access the database**:

```bash
docker compose exec db psql -U flow -d flow
```

**Reset all data** (useful for testing):

```bash
docker compose down -v && docker compose up --build
```

**⚠️ Warning**: This deletes all database data and uploaded files.

### Docker Configuration

The Docker setup consists of three main components:

- **`api/Dockerfile`**: Multi-stage build for Python/FastAPI backend
  - Stage 1: Builds dependencies with gcc/libpq-dev
  - Stage 2: Minimal runtime with non-root user, gunicorn+uvicorn workers
  
- **`frontend/Dockerfile`**: Multi-stage build for React SPA
  - Stage 1: Node.js 20 builder compiling TypeScript and bundling with Vite
  - Stage 2: Nginx Alpine serving optimized static files (~25MB image)

- **`deploy/docker-compose.yml`**: Orchestrates all services
  - `db`: PostgreSQL 15 with persistent volume
  - `api`: FastAPI backend with `/data` volume for uploads/work/graphs/exports
  - `frontend`: Nginx serving React SPA
  - Health checks and restart policies for all services

**Volume Mounts**:

- `db-data`: PostgreSQL database files (persists across restarts)
- `api-data`: Application data (`/data/artifacts`, `/data/work`, `/data/graphs`, `/data/exports`)

**Configuration**: See `deploy/.env.example` for all available environment variables.

### SQLite Development Mode

For lightweight development without PostgreSQL:

**Option 1**: Modify `docker-compose.yml`:

```yaml
# Comment out the db service and its dependency
api:
  environment:
    DB_URL: sqlite:////data/flow.db
  # Remove: depends_on: db
```

**Option 2**: Run API locally without Docker:

```bash
cd api
pip install -e .
DB_URL=sqlite:///./flow.db uvicorn app.main:app --reload
```

## Quick Start

### Prerequisites

**Option 1: Docker (Recommended)**

- Docker 20.10+
- docker-compose 2.0+

**Option 2: Local Development**

- Node.js 20+
- Python 3.11+
- PostgreSQL 14+ (or use SQLite for testing)

### Docker Setup

```bash
cd deploy
docker compose up
```

Access the application:

- **Frontend**: <http://localhost:8080>
- **API Documentation**: <http://localhost:8000/docs>
- **API**: <http://localhost:8000/api/v1>

## Local Development Setup

**Note**: For Docker-based development, see [Docker Quick Start](#docker-quick-start) above. The following instructions are for local development without Docker.

### Local Prerequisites

**Requirements for Local Development:**

- Node.js 20+
- Python 3.11+
- PostgreSQL 14+ (or use SQLite for testing)

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at <http://localhost:5173>

### Backend Development

```bash
cd api
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run development server
uvicorn app.main:app --reload --port 8000
```

API will be available at <http://localhost:8000>

### Local Database Setup

**PostgreSQL (recommended for production-like dev):**

```bash
# Start PostgreSQL via Docker
docker run -d \
  --name splunk-flow-db \
  -e POSTGRES_DB=splunk_flow \
  -e POSTGRES_USER=splunk \
  -e POSTGRES_PASSWORD=splunk \
  -p 5432:5432 \
  postgres:15

# Set environment variable
export DATABASE_URL="postgresql://splunk:splunk@localhost:5432/splunk_flow"

# Run migrations
cd api
alembic upgrade head
```

**SQLite (for quick local testing):**

```bash
export DATABASE_URL="sqlite:///./splunk_flow.db"
cd api
alembic upgrade head
```

## Project Structure

```
/
├── frontend/              # React/TypeScript SPA
│   ├── src/              # Source code (components, views, state)
│   ├── public/           # Static assets
│   └── package.json      # Node dependencies
│
├── api/                  # Python/FastAPI backend
│   ├── app/
│   │   ├── routers/      # API endpoints (projects, uploads, jobs, graphs)
│   │   ├── services/     # Business logic (parser, resolver, validator)
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── migrations/   # Alembic database migrations
│   │   └── utils/        # Shared utilities
│   └── pyproject.toml    # Python dependencies and config
│
├── deploy/               # Deployment configurations
│   ├── docker-compose.yml
│   └── k8s/             # Kubernetes manifests
│
├── samples/             # Example Splunk configurations for testing
│
├── docs/                # Additional documentation
│
└── Specs/
    └── Spec.md          # Detailed system specification
```

## Documentation

- **Detailed Specification**: See [/Specs/Spec.md](/Specs/Spec.md) for comprehensive system design, API contracts, data models, and algorithm details
- **API Documentation**: Interactive API docs available at `/docs` endpoint when backend is running
- **Sample Configurations**: See [/samples](/samples) directory for example Splunk configuration snapshots

## Development

### Code Style

- **Python**: Formatted with `ruff` (configured in `pyproject.toml`)
- **TypeScript**: ESLint with TypeScript rules (configured in `frontend/`)

### Testing

**Backend:**

```bash
cd api
pytest
```

**Frontend:**

```bash
cd frontend
npm test
```

### Linting

**Backend:**

```bash
cd api
ruff check .
mypy .
```

**Frontend:**

```bash
cd frontend
npm run lint
```

## Contributing

1. Follow the code style guidelines (ruff for Python, ESLint for TypeScript)
2. Write tests for new features
3. Update documentation as needed
4. Ensure all tests pass before submitting

## Production Deployment

### Image Registry

For production deployment, push built images to a container registry:

```bash
# Build and tag images
docker compose build
docker tag splunk-flow-api:latest ghcr.io/your-org/splunk-flow-api:v2.0.0
docker tag splunk-flow-frontend:latest ghcr.io/your-org/splunk-flow-frontend:v2.0.0

# Push to registry
docker push ghcr.io/your-org/splunk-flow-api:v2.0.0
docker push ghcr.io/your-org/splunk-flow-frontend:v2.0.0
```

### Kubernetes Deployment

For Kubernetes deployment, see the manifests in `/deploy/k8s/` (detailed in section 7.3 of the spec):

- Deployments for API and Frontend
- StatefulSet for PostgreSQL
- Services for internal communication
- Ingress for external access
- PersistentVolumeClaims for data persistence

### Security Checklist

**Before deploying to production:**

1. **Secrets Management**: Use Docker secrets, Kubernetes secrets, or external secret management (HashiCorp Vault, AWS Secrets Manager) instead of environment variables
2. **TLS/SSL**: Enable HTTPS with valid certificates at load balancer or ingress controller
3. **CORS Configuration**: Restrict `ALLOW_ORIGINS` to production domain only (remove localhost)
4. **Database Credentials**: Use strong, randomly generated passwords
5. **JWT Configuration**: Generate secure random keys using `openssl rand -hex 32` and rotate periodically
6. **Logging**: Set `LOG_LEVEL=warning` or `error` in production
7. **Resource Limits**: Configure CPU and memory limits for containers
8. **Network Policies**: Restrict inter-service communication to required paths only
9. **Health Checks**: Monitor `/healthz` endpoint for readiness probes
10. **Backup Strategy**: Implement automated backups for PostgreSQL and application data volumes

### Healthcheck Endpoints

The API provides health check endpoints for monitoring and load balancer probes:

- **`GET /healthz`**: Simple health check (returns 200 OK if service is running)
- **`GET /readyz`**: Readiness check (returns 200 OK if service can accept traffic, including database connectivity)

Configure your load balancer or Kubernetes probes to use these endpoints.

## License

[Specify license or mark as proprietary]
