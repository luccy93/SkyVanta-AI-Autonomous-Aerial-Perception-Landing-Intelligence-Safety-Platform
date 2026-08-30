# SkyVanta AI — Production Security, Authentication & API Protection Specification
## Document Identifier: `D8-SECURITY-SPEC-2026`

---

## 1. Executive Security Summary & Boundaries

SkyVanta AI operates as an offline, simulation-first autonomous landing verification platform. The security boundary hardens the public REST API and WebSocket streaming interface without altering the frozen V1–V9 robotics core algorithms, 15-state ESEKF estimators, PnP geometry, or internal safety supervisory state machines.

```
+---------------------------------------------------------------------------------------------------+
|                                  PUBLIC INTERNET / CLIENT INGRESS                                 |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
                               [ TLS 1.3 / HTTPS / WSS Boundary ]
                                                  │
                                                  ▼
                        [ Security Headers & Explicit Production CORS ]
                                                  │
                                                  ▼
                          [ Payload & Header Size Limit Middleware ]
                                                  │
                                                  ▼
                        [ Tiered Token-Bucket Rate Limiter (IP/Key) ]
                                                  │
                                                  ▼
                     [ API Key Authentication & Scope Authorization ]
                                      │                        │
               Public Endpoints       │                        │ Protected Endpoints
             (/health, /ready)        │                        │ (Require READ / EXECUTE)
                      │               │                        │
                      ▼               ▼                        ▼
               +─────────────+  +─────────────+          +─────────────────────────────+
               |  Health &   |  |   Security  |          |       Protected APIs        |
               |  Readiness  |  | Audit Trail |          | /api/v1/system/info (READ)  |
               |   Probes    |  |  (Scrubbed) |          | /api/v1/scenarios   (READ)  |
               +─────────────+  +─────────────+          | /api/v1/metrics     (READ)  |
                                                         | /api/v1/scenarios/run (EXEC)|
                                                         | /api/v1/telemetry/ws (READ) |
                                                         +─────────────────────────────+
                                                                        │
                                                                        ▼
                                                         +─────────────────────────────+
                                                         | FROZEN ROBOTICS CORE (V1-V9)|
                                                         |  - 6-DoF Digital Twin       |
                                                         |  - 15-State ESEKF Fusion    |
                                                         |  - 12-State Safety FSM      |
                                                         |  - Invariant Gatekeepers    |
                                                         |  * NO PHYSICAL HARDWARE     |
                                                         |  * NO MODEL DOWNLOADS       |
                                                         +─────────────────────────────+
```

---

## 2. Authentication & API Key Lifecycle

### 2.1 Cryptographic Storage & Comparison
- **Key Format**: `sk_live_<key_id>_<secret>` or `sk_test_<key_id>_<secret>` (cryptographically generated using `secrets.token_urlsafe(32)`).
- **One-Way Hash Storage**: Plaintext keys are never stored in memory or persisted to disk. Only standard SHA-256 digests (`hash_key_secret`) are retained.
- **Timing Leak Prevention**: Key hash validation utilizes constant-time comparison via `hmac.compare_digest`.
- **Immediate Revocation**: Keys can be deactivated instantaneously via `api_key_manager.revoke_key(key_id)`.
- **Expiration Enforcement**: Optional `expires_at` timestamps invalidate stale credentials automatically.

### 2.2 Client Header Ingress
Protected endpoints accept authentication credentials via either:
1. **Standard Bearer Header**: `Authorization: Bearer <api_key>`
2. **Dedicated API Key Header**: `X-API-Key: <api_key>`
3. **WebSocket Subprotocol Header**: `Sec-WebSocket-Protocol: bearer.<api_key>`

---

## 3. Authorization Policy & Scope Hierarchy

| Scope | Granted Capabilities | Protected Endpoints |
| :--- | :--- | :--- |
| `Scope.READ` | Read-only inspection of metadata, catalog, and metrics. | `GET /api/v1/system/info`<br>`GET /api/v1/scenarios`<br>`GET /api/v1/scenarios/{name}`<br>`GET /api/v1/metrics`<br>`WS /api/v1/telemetry/ws` |
| `Scope.EXECUTE` | Execution of 6-DoF closed-loop simulation benchmark scenarios (inherits `READ`). | `POST /api/v1/scenarios/run` |
| `Scope.ADMIN` | Full administrative control, key lifecycle, and telemetry configuration (inherits all). | All endpoints |

---

## 4. Public vs Protected Endpoints

### 4.1 Public Endpoints
- `GET /health` — Liveness check verifying process health and immutable safety locks.
- `GET /ready` — Readiness check verifying scenario catalog load and engine state before routing traffic.

### 4.2 Protected Endpoints
- `GET /api/v1/system/info` — Requires `Scope.READ`
- `GET /api/v1/scenarios` — Requires `Scope.READ`
- `GET /api/v1/scenarios/{scenario_name}` — Requires `Scope.READ`
- `GET /api/v1/metrics` — Requires `Scope.READ`
- `POST /api/v1/scenarios/run` — Requires `Scope.EXECUTE`
- `WS /api/v1/telemetry/ws` — Requires `Scope.READ`

---

## 5. WebSocket Handshake Security

WebSocket telemetry subscriptions at `/api/v1/telemetry/ws` enforce strict handshake admission:
1. Validates `Authorization`, `X-API-Key`, or `Sec-WebSocket-Protocol` token before accepting socket or spawning background streaming loops.
2. Rejects unauthorized, revoked, or expired tokens with close code `1008 Policy Violation`.
3. Does not spawn background simulation worker threads for unauthorized connection attempts.
4. Preserves backpressure (`asyncio.Queue(maxsize=50)`), max client limit (`max_ws_clients=50`), and `ping`/`pong` keepalive.

---

## 6. Tiered Rate Limiting & Resource Protection

Application-level Token Bucket rate limiting protects compute resources across three independent tiers:

| Tier | Default Rate (Req/Min) | Burst Allowance | Target Endpoints |
| :--- | :--- | :--- | :--- |
| **Read Tier** | 120 req/min | 30 tokens | System metadata, scenario catalog |
| **Execute Tier** | 30 req/min | 10 tokens | `POST /api/v1/scenarios/run` |
| **Metrics Tier** | 60 req/min | 20 tokens | `GET /api/v1/metrics` |

Breached rate limits return `429 Too Many Requests` with a structured error body and `Retry-After` header.

---

## 7. Request Payload Size Limits

- **Maximum Request Body**: $64\text{ KB}$ default (`max_request_body_bytes=65536`). Oversized POST bodies return `413 Payload Too Large`.
- **Maximum Request Headers**: $16\text{ KB}$ default (`max_request_header_bytes=16384`). Oversized headers return `431 Request Header Fields Too Large`.

---

## 8. Defensive HTTP Security Headers & Production CORS

All HTTP responses incorporate hardened headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (HTTPS)
- **CORS Policy**: Strictly explicit allowed origins. Wildcard `*` is prohibited in production.

---

## 9. Security Audit Logging & Credential Redaction

Security events are emitted to structured stdout JSON streams:
- `AUTH_SUCCESS` — Successful identity verification.
- `AUTH_FAILURE` — Missing API key.
- `AUTH_REJECTED` — Invalid, revoked, or expired API key.
- `KEY_REVOKED` — Explicit key deactivation.
- `RATE_LIMITED` — Token bucket threshold exceeded.
- `FORBIDDEN` — Insufficient authorization scope.
- `INVALID_REQUEST` — Oversized body/headers or malformed parameters.
- `WEBSOCKET_AUTH_FAILURE` — Unauthorized WebSocket connection handshake.

All event payloads pass through `sanitize_payload()` and `mask_api_key()` to guarantee zero plaintext credential leakage in logs or monitoring metrics.
