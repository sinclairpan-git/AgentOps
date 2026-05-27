# Ai_AutoSDLC -> AgentOps E2E Smoke

This smoke validates the AO57 usable production path, not only the code contract:

```text
ai-sdlc run or controlled fixture
  -> AgentOps Gateway Bearer token
  -> AgentOps API upstream identity headers
  -> PostgreSQL persisted runtime facts
  -> Console SDLC workbench readback
```

## 1. Start AgentOps

From the AgentOps repository:

```bash
docker compose up --build
```

Wait for:

```bash
curl -sS http://127.0.0.1:8766/v1/health
curl -sS http://127.0.0.1:8765/v1/health
```

Both should return `status=healthy`.

## 2. Configure Ai_AutoSDLC

Use the Gateway as the sink endpoint:

```bash
export AGENTOPS_INGESTION_ENDPOINT=http://127.0.0.1:8766
export AGENTOPS_INGESTION_TOKEN=local-agentops-gateway-token
```

For older local SDLC checkouts that still read `AGENTOPS_ENDPOINT`, set it to
the same Gateway base URL. Newer SDLC runs should prefer
`AGENTOPS_INGESTION_ENDPOINT`.

Ai_AutoSDLC should send:

```http
POST /v1/runtime/events
Authorization: Bearer ${AGENTOPS_INGESTION_TOKEN}
Content-Type: application/json
```

Ai_AutoSDLC must not send `X-AgentOps-*` headers directly. Gateway owns those
headers and rebuilds them after token validation.

## 3. Run Producer Smoke

Preferred real run:

```bash
ai-sdlc agentops doctor --json
ai-sdlc run
ai-sdlc agentops status --json
```

`ai-sdlc run --dry-run` is safe for local planning and outbox generation, but it
must not be used as proof of live AgentOps delivery. The current SDLC runtime
bridge intentionally avoids external POST side effects during dry-run. To send
dry-run generated outbox data intentionally, use the SDLC retry command after
reviewing the generated outbox:

```bash
ai-sdlc agentops retry --json
```

If the project needs a controlled fixture before a full run, post the AO56
canonical batch through the Gateway:

```bash
curl -sS \
  -H "Authorization: Bearer ${AGENTOPS_INGESTION_TOKEN}" \
  -H 'Content-Type: application/json' \
  --data @contracts/cross-project/fixtures/ai_sdlc_executable_task_runtime_batch.v1.json \
  "${AGENTOPS_INGESTION_ENDPOINT}/v1/runtime/events"
```

Expected receipt:

- `schema_version=runtime_outbox_receipt.v1`
- `accepted_count > 0`
- `rejected_count=0`
- `dlq_count=0`
- `audit_id` present

## 3a. Run Ops Access Readiness

From the AgentOps repository, use the machine-readable readiness gate before or
after the SDLC producer smoke:

```bash
AGENTOPS_INGESTION_TOKEN=local-agentops-gateway-token \
  uv run agentops-access-readiness --json
```

Equivalent source checkout command:

```bash
python scripts/agentops-access-readiness.py \
  --token local-agentops-gateway-token \
  --json
```

Expected result:

- `schema_version=agentops_access_readiness.v1`
- `overall=pass`
- Gateway health and API health pass
- valid Gateway ingestion returns `runtime_outbox_receipt.v1`
- Trace and Evidence readback pass
- bad token, raw API bypass, and closed route allowlist negative checks pass

## 4. Verify AgentOps Readback

Trace:

```bash
curl -sS \
  -H 'X-AgentOps-Principal: ops.local' \
  -H 'X-AgentOps-Roles: agentops-operator' \
  http://127.0.0.1:8765/v1/runtime/runs/run_sdlc_001/trace
```

Evidence summary:

```bash
curl -sS \
  -H 'X-AgentOps-Principal: ops.local' \
  -H 'X-AgentOps-Roles: agentops-operator' \
  http://127.0.0.1:8765/v1/runtime/runs/run_sdlc_001/evidence-summary
```

Console:

```text
http://127.0.0.1:4173
```

The SDLC run workbench must show:

- task guard state and executable task id
- runtime outbox receipt
- evidence readiness
- adapter diagnostics where `verified_loaded` is diagnostic-only

## 5. Negative Cases

Bad token:

```bash
curl -sS \
  -H 'Authorization: Bearer bad-token' \
  -H 'Content-Type: application/json' \
  --data @contracts/cross-project/fixtures/ai_sdlc_executable_task_runtime_batch.v1.json \
  http://127.0.0.1:8766/v1/runtime/events
```

Expected: `401 GATEWAY_TOKEN_INVALID`, with no token echoed.

Missing AgentOps upstream identity on raw API:

```bash
curl -sS \
  -H 'Authorization: Bearer local-agentops-gateway-token' \
  -H 'Content-Type: application/json' \
  --data @contracts/cross-project/fixtures/ai_sdlc_executable_task_runtime_batch.v1.json \
  http://127.0.0.1:8765/v1/runtime/events
```

Expected: `401 UPSTREAM_IDENTITY_REQUIRED`.

Replay:

```bash
curl -sS \
  -H "Authorization: Bearer ${AGENTOPS_INGESTION_TOKEN}" \
  -H 'Content-Type: application/json' \
  --data @contracts/cross-project/fixtures/ai_sdlc_executable_task_runtime_batch.v1.json \
  "${AGENTOPS_INGESTION_ENDPOINT}/v1/runtime/events"
```

Expected: `deduplicated_count > 0`, no duplicate TraceSpan records.

Schema invalid:

```bash
printf '{"schema_version":"runtime.ingestion.v1","batch_id":"bad","events":[{}]}' \
  | curl -sS \
      -H "Authorization: Bearer ${AGENTOPS_INGESTION_TOKEN}" \
      -H 'Content-Type: application/json' \
      --data-binary @- \
      "${AGENTOPS_INGESTION_ENDPOINT}/v1/runtime/events"
```

Expected: receipt contains rejected item results and summary-only DLQ diagnostics.

## 6. Evidence To Archive

Record the following in the AgentOps task execution log when the smoke is run:

- AgentOps commit and Ai_AutoSDLC commit
- Gateway endpoint used
- receipt summary
- trace span count
- evidence summary raw access state
- Console SDLC workbench readback result
- negative case results
- `agentops_access_readiness.v1` JSON result
