# ==============================================================================
# SkyVanta AI — Production & Simulation Deployment Container
# Hardened Multi-Stage Non-Root Minimal Simulation Runtime
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build & Dependency Wheel Cache
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Disable bytecode generation & interactive prompts
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /build

# Install build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and pre-install dependencies into local user directory
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Hardened Runtime Container
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# OpenContainers Image Metadata
LABEL org.opencontainers.image.title="SkyVanta AI" \
      org.opencontainers.image.description="Autonomous Aerial Perception, Landing Intelligence & Digital Twin Simulation Platform" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="SkyVanta-AI" \
      org.opencontainers.image.authors="SkyVanta-AI / Devendraprasad"

# Set runtime security & environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/skyvanta/.local/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH" \
    SKYVANTA_ENV=production \
    SKYVANTA_HOST=0.0.0.0 \
    SKYVANTA_PORT=8080 \
    SKYVANTA_ALLOW_EXTERNAL=false \
    SKYVANTA_ALLOW_NETWORK_DOWNLOAD=false

# Install minimal headless OpenCV shared runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged system user and group (UID/GID 1000)
RUN groupadd -g 1000 skyvanta && \
    useradd -m -u 1000 -g skyvanta -s /bin/bash skyvanta

# Set up working directory
WORKDIR /app

# Copy pre-installed Python packages from builder stage
COPY --from=builder --chown=skyvanta:skyvanta /root/.local /home/skyvanta/.local

# Copy application source code and metadata with non-root ownership
COPY --chown=skyvanta:skyvanta skyvanta/ /app/skyvanta/
COPY --chown=skyvanta:skyvanta config/ /app/config/
COPY --chown=skyvanta:skyvanta pyproject.toml README.md /app/

# Install SkyVanta package in isolated mode
RUN pip install --no-cache-dir --no-deps --user -e /app

# Switch to non-root user
USER skyvanta:skyvanta

# Expose API and WebSocket service port
EXPOSE 8080

# Built-in lightweight health check using HealthCheckService (no curl required)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "from skyvanta.deployment import HealthCheckService; res = HealthCheckService().check_health(); exit(0 if res.status == 'healthy' else 1)"

# Production Entrypoint: Direct exec-form execution for PID 1 signal propagation
CMD ["uvicorn", "skyvanta.deployment.api.app:app", "--host", "0.0.0.0", "--port", "8080"]
