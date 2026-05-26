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
| Runtime Gateway | `http://127.0.0.1:8766` | Public ingestion endpoint for Ai_AutoSDLC |
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
python -m agentops.api.gateway --host 0.0.0.0 --port 8766
```

## Smoke Check

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
- `AGENTOPS_POSTGRES_AUTO_MIGRATE=true` is acceptable for controlled single-node
  deploys. For multi-node deploys, run migrations once during release and start
  API nodes with auto migration disabled.
- Console must be built with `VITE_AGENTOPS_API_BASE` pointing at the public
  Gateway or another trusted API base that can supply the required upstream auth.

Redis is not required for AO57. It may be added later for cache, push, queue, or
low-latency operator feedback, but PostgreSQL remains the only canonical runtime
facts and audit source.
