# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project configuration and source code
COPY pyproject.toml ./
COPY app/ ./app/

# Install dependencies and the application
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

# Create application and data directories
RUN mkdir -p /app /data && chown -R appuser:appuser /app /data

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application code
COPY --chown=appuser:appuser ./app /app
COPY --chown=appuser:appuser pyproject.toml /app/

WORKDIR /app

# Regenerate entry points for gunicorn and uvicorn using already-copied modules
RUN pip install --no-cache-dir --no-deps gunicorn uvicorn[standard]

# Install the application to generate proper entry points (using already built packages)
RUN pip install --no-cache-dir --no-deps .

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE 8000

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"

# Start application with gunicorn + uvicorn workers
# Use JSON array format with shell to allow WORKERS env variable expansion
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w ${WORKERS:-4} -b 0.0.0.0:8000"]
