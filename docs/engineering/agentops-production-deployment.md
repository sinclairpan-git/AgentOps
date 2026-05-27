# AgentOps Production Runtime Deployment

This guide covers the AO57 production runtime path:

```text
Ai_AutoSDLC
  -> API Gateway with Bearer token
  -> AgentOps API with X-AgentOps-* upstream identity headers
  -> PostgreSQL canonical runtime facts
  -> AgentOps Console readback
```

## Local Compose

Start the deployable stack:

```bash
docker compose up --build
```

Services:

| Service | URL | Purpose |
|---|---|---|
| PostgreSQL | `localhost:5432` | Canonical runtime facts, receipts, DLQ, audit records |
| AgentOps API | `http://127.0.0.1:8765` | Internal API, production auth enabled |
| Runtime Gateway | `http://127.0.0.1:8766` | Public ingestion endpoint for Ai_AutoSDLC and local Console snapshot proxy |
| Console | `http://127.0.0.1:4173` | Operator UI, compiled with `VITE_AGENTOPS_API_BASE=http://127.0.0.1:8766` |

The API container runs with:

```bash
AGENTOPS_DATABASE_URL=postgresql://agentops:agentops@postgres:5432/agentops
AGENTOPS_POSTGRES_AUTO_MIGRATE=true
AGENTOPS_ALLOWED_ORIGINS=http://127.0.0.1:4173,http://localhost:4173
python -m agentops.api.server --host 0.0.0.0 --port 8765 --require-auth
```

The reference Gateway runs with:

```bash
AGENTOPS_GATEWAY_TOKEN=local-agentops-gateway-token
AGENTOPS_UPSTREAM_BASE=http://api:8765
AGENTOPS_GATEWAY_ROLES=agentops-ingestor
AGENTOPS_GATEWAY_SCOPES=event.ingest
AGENTOPS_GATEWAY_MAX_BODY_BYTES=1048576
AGENTOPS_GATEWAY_UPSTREAM_TIMEOUT_SECONDS=10
AGENTOPS_GATEWAY_RATE_LIMIT_PER_MINUTE=600
AGENTOPS_GATEWAY_AUDIT_LOG=/var/log/agentops/gateway-audit.jsonl
python -m agentops.api.gateway --host 0.0.0.0 --port 8766
```

For local smoke deployments, the reference Gateway also proxies
`GET /v1/console/snapshot` to the internal AgentOps API with operator read
scopes so the Console can read real snapshots from the compose stack. Managed
production deployments should protect the Console path with their normal user
auth layer.

## Smoke Check

Before handing the endpoint to Ai_AutoSDLC, run the access readiness gate from
the AgentOps checkout:

```bash
AGENTOPS_INGESTION_TOKEN=local-agentops-gateway-token \
  uv run agentops-access-readiness --json
```

For staging or server deployments, pass the public Gateway base URL and an API
base reachable from the operator shell:

```bash
AGENTOPS_INGESTION_TOKEN=<producer-token> \
  uv run agentops-access-readiness \
    --gateway-base https://ops-gateway.example.com \
    --api-base http://127.0.0.1:8765 \
    --json
```

If the raw AgentOps API is private and not reachable from the machine running
the check, run the command from a server shell or VPN path that can reach it.
Skipping API readback is only acceptable for preliminary Gateway checks, not
release readiness.

Post a canonical AO56 runtime batch through the Gateway:

```bash
curl -sS \
  -H 'Authorization: Bearer local-agentops-gateway-token' \
  -H 'Content-Type: application/json' \
  --data @contracts/cross-project/fixtures/ai_sdlc_executable_task_runtime_batch.v1.json \
  http://127.0.0.1:8766/v1/runtime/events
```

Expected receipt summary:

- `schema_version=runtime_outbox_receipt.v1`
- `producer=Ai_AutoSDLC`
- `accepted_count=2`
- `rejected_count=0`
- `dlq_count=0`

Read persisted trace and evidence summary from the internal API:

```bash
curl -sS \
  -H 'X-AgentOps-Principal: ops.local' \
  -H 'X-AgentOps-Roles: agentops-operator' \
  http://127.0.0.1:8765/v1/runtime/runs/run_sdlc_001/trace

curl -sS \
  -H 'X-AgentOps-Principal: ops.local' \
  -H 'X-AgentOps-Roles: agentops-operator' \
  http://127.0.0.1:8765/v1/runtime/runs/run_sdlc_001/evidence-summary
```

Open the Console at `http://127.0.0.1:4173` and verify the SDLC run workbench
shows task guard, outbox receipt, evidence readiness, and adapter diagnostics.

## Server Deployment Notes

Use the same service split on a server:

- PostgreSQL is the canonical store. Back it up and monitor connection capacity.
- The public ingress should be the API Gateway, not the raw AgentOps API.
- Gateway must validate producer Bearer tokens and strip inbound `X-AgentOps-*`
  headers before injecting trusted upstream identity headers.
- Gateway must keep a closed route allowlist for producer tokens, reject revoked
  tokens, enforce bounded request size/upstream timeout/rate limit, and write a
  redacted audit record without token or raw payload material.
- `AGENTOPS_POSTGRES_AUTO_MIGRATE=true` is acceptable for controlled single-node
  deploys. For multi-node deploys, run migrations once during release and start
  API nodes with auto migration disabled.
- Console must be built with `VITE_AGENTOPS_API_BASE` pointing at the public
  Gateway or another trusted API base that can supply the required upstream auth.

Redis is not required for AO57. It may be added later for cache, push, queue, or
low-latency operator feedback, but PostgreSQL remains the only canonical runtime
facts and audit source.
