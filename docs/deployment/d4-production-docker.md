# SKYVANTA AI — PRODUCTION DOCKER HARDENING
## PHASE D4 — CONTAINER SECURITY, MULTI-STAGE BUILD & RUNTIME SPECIFICATION

**Document ID**: `SKYVANTA-D4-PRODUCTION-DOCKER`  
**Date**: August 29, 2026  
**Status**: ACTIVE  
**Security Boundary**: SIMULATION-ONLY / HARDWARE-DISCONNECTED / NON-ROOT  

---

## 1. EXECUTIVE OVERVIEW

Phase D4 hardens the containerized deployment runtime of **SkyVanta AI** (`Dockerfile` and `compose.yaml`) for secure, deterministic production deployment.

Key Hardening Features:
- **Multi-Stage Build**: Isolates build-time dependencies (compilers, build-essential) in the `builder` stage, copying only pre-built wheels and application code to the `runtime` stage.
- **Unprivileged Non-Root Execution**: Runs as user `skyvanta:skyvanta` (`UID:GID 1000:1000`).
- **Signal Forwarding & PID 1**: Uses direct exec-form `CMD ["uvicorn", ...]` allowing `SIGTERM` and `SIGINT` signals to propagate cleanly for graceful FastAPI and WebSocket connection termination.
- **Strict Software Isolation**: Hardened container prevents physical hardware access, USB device access, serial port mapping, and live network model downloads.
- **Lightweight Built-In Healthcheck**: Evaluates service liveness and readiness via `HealthCheckService` directly in Python without requiring `curl` or external binary tools.

---

## 2. CONTAINER ARCHITECTURE & MULTI-STAGE DESIGN

```
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 1: BUILDER                             │
│  Base: python:3.11-slim                                         │
│  • Install build-essential                                      │
│  • Pre-install requirements.txt into /root/.local               │
└────────────────────────────────┼────────────────────────────────┘
                                 │
                     COPY /root/.local ──► /home/skyvanta/.local
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│                    STAGE 2: HARDENED RUNTIME                    │
│  Base: python:3.11-slim (minimal headless libraries)           │
│  • Minimal shared libraries (libgl1, libglib2.0-0)             │
│  • System User: skyvanta:skyvanta (1000:1000)                   │
│  • Clean Python environment: PYTHONDONTWRITEBYTECODE=1         │
│  • Expose Port: 8080                                            │
│  • Direct exec-form entrypoint: uvicorn (PID 1)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. CONTAINER BUILD & RUNTIME COMMANDS

### 1. Build Production Image
```bash
# Build minimal production multi-stage image
docker build -t skyvanta-ai:latest .
```

### 2. Run Container Standalone
```bash
# Run container with dropped capabilities and non-root user
docker run -p 8080:8080 \
  --name skyvanta-api \
  --security-opt no-new-privileges:true \
  --cap-drop ALL \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --rm skyvanta-ai:latest
```

### 3. Run with Docker Compose
```bash
# Launch via hardened compose specification
docker compose up -d
```

---

## 4. ENVIRONMENT CONFIGURATION

The container supports the following environment variables with safe production defaults:

| Variable | Default | Description |
|---|---|---|
| `SKYVANTA_ENV` | `production` | Active deployment environment tier (`development`, `testing`, `production`). |
| `SKYVANTA_HOST` | `0.0.0.0` | Bind host IP address inside the container network namespace. |
| `SKYVANTA_PORT` | `8080` | Bind port for HTTP and WebSocket API services. |
| `SKYVANTA_LOG_LEVEL` | `INFO` | Structured logging verbosity level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `SKYVANTA_TELEMETRY_RATE_HZ` | `20.0` | Real-time WebSocket streaming frequency in Hertz. |
| `SKYVANTA_ALLOW_EXTERNAL` | `false` | **Immutable Safety Invariant**: Physical drone hardware is strictly disabled. |
| `SKYVANTA_ALLOW_NETWORK_DOWNLOAD` | `false` | **Immutable Safety Invariant**: Runtime model downloads are strictly disabled. |

---

## 5. CONTAINER HEALTHCHECK

The container defines a built-in healthcheck:
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "from skyvanta.deployment import HealthCheckService; res = HealthCheckService().check_health(); exit(0 if res.status == 'healthy' else 1)"
```

- **Interval**: Evaluated every 30 seconds.
- **Timeout**: 5 seconds.
- **Start Period**: 5 seconds grace period for initial import and model initialization.
- **Retries**: 3 consecutive failures before marking container unhealthy.

---

## 6. RESOURCE RECOMMENDATIONS & BOUNDARIES

| Resource | Minimum | Recommended | Notes |
|---|---|---|---|
| **CPU** | 1 vCPU | 2 vCPUs | Sufficient for 20 Hz simulation + 50 concurrent WebSocket streams |
| **Memory (RAM)** | 512 MB | 1024 MB | Peak footprint is < 300 MB under full simulation workload |
| **Storage** | 1 GB | 2 GB | Minimal image size (~450 MB compressed) |

---

## 7. SECURITY & HARDWARE ISOLATION GUARANTEES

1. **Non-Privileged Execution**:
   - The container must never be run with `--privileged`.
   - Host device nodes (`/dev/tty*`, `/dev/bus/usb`, `/dev/i2c*`) are never mounted.
   - Host Docker socket (`/var/run/docker.sock`) is never mounted.
2. **Read-Only Root Compatibility**:
   - The runtime image can run with `--read-only` root filesystem when mounted with a writable `--tmpfs /tmp:rw,noexec,nosuid`.
3. **Secret & Artifact Exclusion**:
   - `.dockerignore` guarantees no `.env`, credentials, SSH keys, git histories, test suites, or development caches are baked into the image.
