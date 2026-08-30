# SkyVanta AI — Disaster Recovery & Deterministic Rollback Specification (Phase D9)

## 1. Overview & Objectives

This document establishes the operational disaster recovery (DR) runbooks, fault recovery policies, and deterministic rollback procedures for **SkyVanta AI**.

The system is designed with a defense-in-depth safety philosophy:
1. **Safety Invariant Priority:** In any ambiguous or corrupt configuration state, the application **fails closed** (`RECOVERY = BLOCKED`).
2. **Deterministic Rollback:** Production rollbacks follow an exact manual/orchestrated operational checklist to restore a verified previous release without state contamination.
3. **Hardware Isolation Enforcement:** No recovery policy or automated retry mechanism is ever permitted to attempt hardware discovery or physical actuator initialization.

---

## 2. Failure Classification & Recovery Matrix

The runtime `RecoveryManager` classifies application faults into deterministic categories:

| Failure Category | Trigger Condition | Automated Action | Safety Invariant Impact |
|---|---|---|---|
| `NORMAL_RESTART` | Planned rolling restart or clean SIGTERM signal | `RESTART_ALLOWED` | Hardware access remains DISABLED |
| `TRANSIENT_FAILURE` | Temporary socket timeout or rate burst | `RETRY_WITH_BACKOFF` (max 3 retries, exponential backoff) | Hardware access remains DISABLED |
| `CONFIGURATION_FAILURE` | Invalid environment parameters, bad port/host | `BLOCK_RECOVERY` (Service halts safely) | Hardware access remains DISABLED |
| `DEPENDENCY_FAILURE` | Missing scenario catalog or corrupt models | `BLOCK_RECOVERY` (Service halts safely) | Hardware access remains DISABLED |
| `SAFETY_CONFIGURATION_FAILURE` | Attempt to set `allow_external=true` or enable hardware | `BLOCK_RECOVERY` (Hard lock) | **STRICT BLOCK:** Hardware access remains DISABLED |
| `UNKNOWN_FAILURE` | Unhandled runtime exception | `BLOCK_RECOVERY` (Safety shutdown) | Hardware access remains DISABLED |

> [!CAUTION]
> If a `SAFETY_CONFIGURATION_FAILURE` is triggered, automatic recovery is permanently locked. Operator intervention is required to audit environment variables and restore safe defaults.

---

## 3. Deterministic Rollback Procedure

When an unhealthy deployment, regression, or safety alert occurs post-promotion, operators execute the deterministic rollback workflow:

```text
       ┌──────────────────┐
       │  DETECT FAILURE  │ (Health check failure, error rate spike, safety alert)
       └────────┬─────────┘
                ▼
       ┌──────────────────┐
       │  STOP PROMOTION  │ (Freeze ingress traffic routing & halt container rollout)
       └────────┬─────────┘
                ▼
       ┌──────────────────┐
       │IDENTIFY PREVIOUS │ (Lookup previous verified release tag & Git SHA)
       │KNOWN-GOOD RELEASE│
       └────────┬─────────┘
                ▼
       ┌──────────────────┐
       │ REDEPLOY RELEASE │ (Deploy verified container image tag)
       └────────┬─────────┘
                ▼
       ┌──────────────────┐
       │   HEALTH CHECK   │ (Verify /health and /ready return 200 OK & healthy)
       └────────┬─────────┘
                ▼
       ┌──────────────────┐
       │ REST SMOKE TEST  │ (Test /api/v1/system/info, /api/v1/scenarios, /api/v1/release)
       └────────┬─────────┘
                ▼
       ┌──────────────────┐
       │ WS SMOKE TEST    │ (Validate /api/v1/telemetry/ws streaming connection)
       └────────┬─────────┘
                ▼
       ┌──────────────────┐
       │SECURITY & SAFETY │ (Verify auth enforcement & hardware_access == false)
       └────────┬─────────┘
                ▼
       ┌──────────────────┐
       │ROLLBACK CONFIRMED│ (Admit production traffic & file incident report)
       └──────────────────┘
```

---

## 4. Step-by-Step Operator Runbook

### Step 1: Detect Failure
Monitor alerts from:
* Endpoint `/health` returning non-200 or `status: "unhealthy"`
* High rate of 5xx errors on `/api/v1/scenarios/run`
* `StartupValidationError` logged during container boot

### Step 2: Stop Promotion
Halt automated deployment pipelines and prevent new container instances from entering the load balancer pool.

### Step 3: Identify Previous Known-Good Release
Query container registry or Git tags for the most recent accepted release (e.g., `skyvanta-ai:v0.1.0-b063285`).

### Step 4: Redeploy Previous Release
Update container orchestration (e.g., Docker Compose or cloud deployment config):
```bash
# Example Docker Compose rollback
docker compose down
docker compose up -d skyvanta-api
```

### Step 5: Execute Smoke Tests
Run pre-flight verification against the restored deployment:
```bash
# 1. Health Probe
curl -f http://localhost:8080/health

# 2. Readiness Probe
curl -f http://localhost:8080/ready

# 3. Release Endpoint
curl -H "Authorization: Bearer <READ_KEY>" http://localhost:8080/api/v1/release
```

### Step 6: Verify WebSocket Telemetry
Connect a test client to `ws://localhost:8080/api/v1/telemetry/ws?api_key=<STREAM_KEY>` and verify receipt of nominal 20 Hz telemetry frames.

### Step 7: Confirm Rollback Completion
Verify that the `release-manifest.json` matches the target fallback commit and restore production traffic.
