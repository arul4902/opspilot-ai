# ==============================================================================
# OpsPilot AI – Autonomous E-Commerce Operations Platform
# Multi-Stage Production Container Build
# ==============================================================================

FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies for PostgreSQL and building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY backend /app/backend
COPY sample-data /app/sample-data
COPY scripts /app/scripts
COPY documentation /app/documentation

# Expose backend port
EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start production server
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

