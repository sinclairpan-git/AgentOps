# AgentOps Access Readiness Gate

**Status**: AO57 closeout hardening  
**Audience**: AgentOps deployers, Ai_AutoSDLC integrators, release operators  

## Purpose

Access readiness is the deploy-time proof that Ai_AutoSDLC can report runtime
events to AgentOps through the intended production boundary. It is stricter than
contract tests because it runs against a real local compose stack or a managed
Gateway/API deployment.

The gate verifies:

- Gateway and API health are reachable.
- A valid producer token can POST the canonical
  `runtime.ingestion.v1` batch to `POST /v1/runtime/events`.
- AgentOps returns a `runtime_outbox_receipt.v1` summary with accepted or
  deduplicated events and no rejected/DLQ records.
- Trace and Evidence summary readback work from persisted AgentOps facts.
- Bad tokens are rejected by the Gateway.
- Direct raw API ingestion without trusted `X-AgentOps-*` identity is rejected.
- The Gateway route allowlist remains closed for producer tokens.

The gate does not print token material or raw event payloads.

## Local Command

Start AgentOps:

```bash
docker compose up --build
```

Run readiness:

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

Expected top-level result:

```json
{
  "schema_version": "agentops_access_readiness.v1",
  "overall": "pass"
}
```

## Staging Or Server Command

Run from a machine that can reach both the public Gateway and the private
AgentOps API readback path:

```bash
AGENTOPS_INGESTION_TOKEN=<producer-token> \
  uv run agentops-access-readiness \
    --gateway-base https://ops-gateway.example.com \
    --api-base http://127.0.0.1:8765 \
    --json
```

If only the Gateway is reachable, use `--no-api-base` or `--skip-api-readback`
only for preliminary diagnostics. A release-ready environment still needs the
full gate, including API readback and raw API bypass rejection, from an operator
or CI runner that has private network access.

## Ai_AutoSDLC Handoff

Once readiness passes, give SDLC users only the Gateway URL and producer token:

```bash
export AGENTOPS_INGESTION_ENDPOINT=https://ops-gateway.example.com
export AGENTOPS_INGESTION_TOKEN=<producer-token>
```

For local integration:

```bash
export AGENTOPS_INGESTION_ENDPOINT=http://127.0.0.1:8766
export AGENTOPS_INGESTION_TOKEN=local-agentops-gateway-token
```

Ai_AutoSDLC should then run:

```bash
ai-sdlc agentops doctor --json
ai-sdlc run
ai-sdlc agentops status --json
```

`ai-sdlc run --dry-run` is not a live delivery proof. It may generate local
outbox data, but current SDLC versions intentionally avoid external POST side
effects during dry-run.

## Evidence To Archive

For each local, staging, or production cutover, archive:

- AgentOps commit and Ai_AutoSDLC commit.
- Gateway base URL, with secrets redacted.
- `agentops_access_readiness.v1` JSON result.
- Ai_AutoSDLC doctor/status JSON summaries.
- Runtime receipt summary.
- Trace span count and Evidence raw access state.
- Console SDLC workbench readback result.

Do not archive producer tokens, raw payload bodies, source diffs, or file
contents as evidence.
