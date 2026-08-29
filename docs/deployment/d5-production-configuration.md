# SKYVANTA AI — PRODUCTION CONFIGURATION & ENVIRONMENT MANAGEMENT
## PHASE D5 — ENVIRONMENT PROFILES, VALIDATION & RUNTIME HARDENING SPECIFICATION

**Document ID**: `SKYVANTA-D5-PRODUCTION-CONFIGURATION`  
**Date**: August 29, 2026  
**Status**: ACTIVE  
**Security Boundary**: SIMULATION-ONLY / HARDWARE-DISCONNECTED / FAIL-FAST CONFIGURATION  

---

## 1. EXECUTIVE OVERVIEW

Phase D5 implements a fail-fast, type-safe, and production-hardened **Configuration and Environment Management Layer** (`skyvanta.deployment.config.DeploymentConfig`) preparing SkyVanta AI for enterprise cloud and container execution.

Core Pillars:
- **Environment Tiers**: Structured profiles for `development`, `testing`, and `production`.
- **Fail-Fast Pydantic Validation**: Strict numeric bounds, port verification, log level checks, and rejection of malformed or unsafe inputs (NaN, infinite rates, negative bounds).
- **Hardened Production Defaults**: Production profile enforces disabled debug mode, strict non-wildcard CORS, structured JSON logging, and connection limiting.
- **Immutable Safety Invariants**: `allow_external = false`, `allow_network_download = false`, and `hardware_disconnected = true` remain strictly non-overridable across all environments.
- **Defensive HTTP Security Headers**: Automatic attachment of standard security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `X-XSS-Protection`).

---

## 2. CONFIGURATION HIERARCHY & FLOW

```
┌─────────────────────────────────────────────────────────────────┐
│                    Environment Variables                        │
│   (SKYVANTA_ENV, SKYVANTA_PORT, SKYVANTA_CORS_ORIGINS, etc.)   │
└────────────────────────────────┼────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DeploymentConfig.from_env()                  │
│       • Pydantic Schema & Bounds Validation                     │
│       • Safe Fallbacks & Non-Empty Sanitization                 │
│       • Production Invariant Enforcement                        │
└────────────────────────────────┼────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application Layer                    │
│   • Attached to app.state.config                                │
│   • Injected into Route Handlers & Telemetry Service            │
│   • Configures CORSMiddleware & SecurityHeadersMiddleware       │
└────────────────────────────────┼────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│               Frozen V1–V9 Simulation Subsystems                │
│   • Offline 6-DoF Digital Twin, ESEKF, FSM, Safety Supervisor   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. ENVIRONMENT PROFILES

| Profile | Environment Name | Characteristics |
|---|---|---|
| **Development** | `development` | Localhost CORS enabled (`localhost:3000`, `127.0.0.1:3000`), human-readable logging, 20 Hz default stream rate. |
| **Testing** | `testing` | Deterministic unit/integration testing configuration, lightweight timeouts. |
| **Production** | `production` | Strict explicit CORS, structured JSON logging, debug disabled, connection limiting. |

---

## 4. ENVIRONMENT VARIABLES REFERENCE

| Variable | Type | Default | Valid Range / Allowed Values | Description |
|---|---|---|---|---|
| `SKYVANTA_ENV` | String | `development` | `development`, `testing`, `production` | Active deployment environment profile tier. |
| `SKYVANTA_HOST` | String | `0.0.0.0` | Valid IPv4 / hostname | Bind IP address for API and WebSocket server. |
| `SKYVANTA_PORT` | Integer | `8080` | `1` – `65535` | Bind port for incoming HTTP/WebSocket traffic. |
| `SKYVANTA_LOG_LEVEL` | String | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | Structured deployment logging verbosity level. |
| `SKYVANTA_CORS_ORIGINS` | String | *(profile-based)* | Comma-separated HTTP/HTTPS URLs (no `*` in prod) | Allowed CORS origin URLs. |
| `SKYVANTA_TELEMETRY_RATE_HZ` | Float | `20.0` | `1.0` – `100.0` | Streaming frequency for WebSocket telemetry broadcast. |
| `SKYVANTA_MAX_WS_CLIENTS` | Integer | `50` | `1` – `1000` | Maximum simultaneous concurrent WebSocket clients. |
| `SKYVANTA_REQUEST_TIMEOUT_SEC` | Float | `60.0` | `1.0` – `600.0` | HTTP request processing timeout in seconds. |
| `SKYVANTA_WS_IDLE_TIMEOUT_SEC` | Float | `300.0` | `5.0` – `3600.0` | WebSocket idle connection timeout in seconds. |
| `SKYVANTA_ENABLE_METRICS` | Boolean | `true` | `true`, `false` | Enable/disable operational telemetry metrics. |
| `SKYVANTA_ENABLE_SECURITY_HEADERS` | Boolean | `true` | `true`, `false` | Enable/disable defensive HTTP security headers. |
| `SKYVANTA_DEBUG` | Boolean | `false` | `true`, `false` (must be `false` in prod) | Diagnostic debug mode. |
| `SKYVANTA_ALLOW_EXTERNAL` | Boolean | `false` | `false` (Immutable) | Physical drone hardware access invariant. |
| `SKYVANTA_ALLOW_NETWORK_DOWNLOAD` | Boolean | `false` | `false` (Immutable) | Runtime network weight download invariant. |

---

## 5. DEFENSIVE HTTP SECURITY HEADERS

When `enable_security_headers: true`, the API attaches the following standard headers to all HTTP responses:
- `X-Content-Type-Options: nosniff` — Prevents MIME-sniffing attacks.
- `X-Frame-Options: DENY` — Mitigates clickjacking attacks.
- `Referrer-Policy: strict-origin-when-cross-origin` — Protects cross-origin metadata leakage.
- `X-XSS-Protection: 1; mode=block` — Enforces legacy browser XSS filters.

---

## 6. CONFIGURATION VS. SECRETS

SkyVanta AI maintains a strict boundary between operational configuration and security credentials:
- **Configuration** (`SKYVANTA_PORT`, `SKYVANTA_ENV`, `SKYVANTA_TELEMETRY_RATE_HZ`): Non-sensitive runtime settings managed via `.env` or container environment parameters.
- **Secrets & Credentials**: SkyVanta AI is an offline simulation-only platform with zero baked-in secrets, API keys, or private certificates. All `.env*` files, key files, and credentials are unconditionally ignored by Git and Docker context.
