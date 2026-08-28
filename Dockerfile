# ==============================================================================
# SkyVanta AI — Production & Simulation Deployment Container
# Multi-stage, non-root, minimal simulation runtime
# ==============================================================================

FROM python:3.11-slim AS runtime

# Set security & runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SKYVANTA_ENV=production \
    SKYVANTA_HOST=0.0.0.0 \
    SKYVANTA_PORT=8080 \
    SKYVANTA_ALLOW_EXTERNAL=false \
    SKYVANTA_ALLOW_NETWORK_DOWNLOAD=false

# Install minimal OS runtime libraries for headless OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged system user for secure container execution
RUN useradd -m -u 1000 -s /bin/bash skyvanta

# Set up working directory
WORKDIR /app

# Install Python package dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy package source code and metadata
COPY skyvanta/ skyvanta/
COPY config/ config/
COPY pyproject.toml README.md ./

# Install SkyVanta package in production mode
RUN pip install --no-cache-dir --no-deps -e .

# Transfer ownership to unprivileged user
RUN chown -R skyvanta:skyvanta /app

# Switch to non-root user
USER skyvanta

# Expose API and WebSocket service port
EXPOSE 8080

# Built-in container health check using HealthCheckService
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "from skyvanta.deployment import HealthCheckService; res = HealthCheckService().check_health(); exit(0 if res.status == 'healthy' else 1)"

# Default entrypoint: Start FastAPI application server
CMD ["uvicorn", "skyvanta.deployment.api.app:app", "--host", "0.0.0.0", "--port", "8080"]
