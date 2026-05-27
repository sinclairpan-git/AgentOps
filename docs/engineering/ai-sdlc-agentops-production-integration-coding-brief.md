# AI-SDLC -> AgentOps Production Integration Coding Brief

**Audience**: Ai_AutoSDLC implementation team  
**Date**: 2026-05-26  
**Status**: Coding-ready handoff  
**AgentOps baseline**: PR #58 merged, commit `dd0b1b2`  
**AI-SDLC baseline**: PR #66 merged, commit `264deb6`  

## 1. Purpose

This document defines the remaining Ai_AutoSDLC work required to make the
AgentOps runtime bridge operational, not just contract-complete.

The current shared contract is already aligned:

- Ai_AutoSDLC produces `runtime.ingestion.v1` batches.
- Events use `event_envelope.v1` with `event_type=sdlc_trace_event` and
  `event_type_version=sdlc_trace_event.v1`.
- AgentOps consumes batches at `POST /v1/runtime/events`.
- AgentOps returns `runtime_outbox_receipt.v1`.
- `verified_loaded` is diagnostic-only and is not a code authorization, L5
  proof, reporter-active proof, or outbox-delivered proof.

The remaining gap is product integration: Ai_AutoSDLC must wire its existing
producer bridge into the `ai-sdlc run` lifecycle, route enterprise traffic
through an API Gateway, persist receipts, and expose operator status/retry
commands.

## 2. Source Of Truth

Use these AgentOps files as the canonical consumer references:

- Contract:
  `specs/056-sdlc-v0-7-18-executable-task-runtime-bridge/contracts/ai-sdlc-agentops-runtime-bridge-vnext.md`
- Cross-project mirror:
  `contracts/cross-project/ai-sdlc-agentops-runtime-bridge-vnext.md`
- Fixture:
  `contracts/cross-project/fixtures/ai_sdlc_executable_task_runtime_batch.v1.json`
- Production auth boundary:
  `specs/023-production-runtime-boundary/spec.md`
- AgentOps runtime endpoint manifest:
  `src/agentops/api/app.py`

Do not introduce a second schema, alternate field spelling, or alternate L5
readiness rule in Ai_AutoSDLC. If a field or rule is unclear, treat the AgentOps
AO56 contract as authoritative and open a contract mismatch issue before coding
a divergent behavior.

## 3. Architecture Decision

The production path is:

```text
Ai_AutoSDLC Reporter / Outbox
  -> API Gateway with Bearer token
  -> AgentOps API with upstream identity headers
  -> PostgreSQL-backed AgentOps facts / receipts / traces / evidence summaries
  -> AgentOps Console
```

Agent Store is not the mandatory runtime outbox relay. Store-mediated activation
remains supported for official installation and summary echo, but runtime facts
may use the ops-direct identity path.

## 4. Non-Goals

Ai_AutoSDLC must not implement:

- AgentOps actual L5 scoring.
- AgentOps policy decisions or grant issuing.
- AgentOps evidence vault storage.
- Agent Store installation facts in ops-direct mode.
- Direct injection of `X-AgentOps-*` production identity headers from a local
  user process.
- Raw payload upload to AgentOps for SDLC trace events.
- Any direct inference from `verified_loaded` to code authorization, outbox
  delivery, reporter health, or actual L5.

## 5. Required Configuration

Ai_AutoSDLC must support these configuration inputs.

| Config | Env alias | Required when | Meaning |
|---|---|---|---|
| `integration.mode` | `AI_SDLC_INTEGRATION_MODE` | enterprise reporting | `standalone`, `enterprise_managed`, or `custom_sink` |
| `reporter.sink` | `AI_SDLC_REPORTER_SINK` | enterprise reporting | `none`, `local_file`, `agentops`, or `custom` |
| `agentops.endpoint` | `AGENTOPS_INGESTION_ENDPOINT` | `reporter.sink=agentops` | API Gateway base URL, not raw AgentOps internal URL in production |
| `agentops.token` | `AGENTOPS_INGESTION_TOKEN` | production Gateway | Bearer token issued for this producer |
| `agentops.identity_mode` | `AGENTOPS_IDENTITY_MODE` | enterprise reporting | `ops_direct` or `store_mediated` |
| `agentops.producer_id` | `AGENTOPS_PRODUCER_ID` | ops-direct | Stable producer principal |
| `agentops.runtime_id` | `AGENTOPS_RUNTIME_ID` | ops-direct | Runtime instance identity |
| `agentops.credential_id` | `AGENTOPS_CREDENTIAL_ID` | enterprise reporting | Reporter credential id |
| `agentops.key_id` | `AGENTOPS_KEY_ID` | enterprise reporting | Signing key id |

`AGENTOPS_ENDPOINT` may be accepted as a backward-compatible local alias, but
new integrations should use `AGENTOPS_INGESTION_ENDPOINT` so runtime reporting
does not collide with unrelated AgentOps API configuration.

Behavior:

- Missing `agentops.endpoint` in standalone mode must not fail the local SDLC
  workflow.
- Missing `agentops.endpoint` with `reporter.sink=agentops` must degrade to
  local pending outbox and show an explicit diagnostic.
- Missing token in production mode must not attempt anonymous enterprise
  delivery.
- Local development may target `http://127.0.0.1:8765` without auth only when
  explicitly configured as a dev/local profile.

## 6. API Gateway Contract

Ai_AutoSDLC calls the Gateway with:

```http
POST {agentops.endpoint}/v1/runtime/events
Authorization: Bearer {AGENTOPS_INGESTION_TOKEN}
Content-Type: application/json
Accept: application/json
```

The Gateway validates the token and injects upstream identity headers when it
forwards to AgentOps:

```http
X-AgentOps-Principal: producer.ai-sdlc.<id>
X-AgentOps-Roles: agentops-ingestor
X-AgentOps-Scopes: event.ingest
X-AgentOps-Request-Id: req_<stable-or-generated>
X-AgentOps-Audit-Id: audit_<stable-or-generated>
```

Ai_AutoSDLC must not self-assert these `X-AgentOps-*` headers in production.
They are a trusted Gateway-to-AgentOps boundary.

Gateway failure handling expected by Ai_AutoSDLC:

| Gateway / AgentOps result | AI-SDLC action |
|---|---|
| HTTP 202 with `runtime_outbox_receipt.v1` | Persist receipt summary and mark outbox sent |
| HTTP 401 / `UPSTREAM_IDENTITY_REQUIRED` | Mark credential/auth diagnostic; do not retry aggressively |
| HTTP 403 / `AGENTOPS_SCOPE_DENIED` | Mark credential/scope diagnostic; do not retry aggressively |
| HTTP 400 schema rejection | Persist rejected receipt/error diagnostic; require code/config fix |
| HTTP 408/429/5xx or timeout | Keep outbox pending and retry with backoff |

## 7. Runtime Event Production

Ai_AutoSDLC already has producer helpers in `ai_sdlc.core.agentops_bridge`.
The coding task is to connect them to the real run lifecycle.

Required emitted facts for the minimum production path:

1. `executable_task` fact when a work item task is prepared.
2. `code_guard` fact when code-change authorization is evaluated.
3. `stage` facts for relevant SDLC stages.
4. `gate` facts for blocking and advisory gates.
5. `verification` facts for test/build/check commands.
6. `artifact` facts for generated or validated artifacts.
7. `violation` facts when guardrails block or detect violations.

Every enterprise event that can influence readiness must include:

- `workitem`
- `executable_task_id`
- `task_guard_state`
- `run_id`
- `trace_id`
- `attempt_no`
- `stage_name`
- `status`
- `payload_hash`
- `payload_ref`
- `data_classification=summary` or `metadata`
- `redaction_policy=summary_only`

Raw diff, raw PR body, raw file contents, secrets, tokens, device keys, and
credential secrets must not be sent in event payloads.

## 8. Run Lifecycle Integration

The `ai-sdlc run` flow must do the following when `reporter.sink=agentops` and
`integration.mode=enterprise_managed`:

1. Resolve enterprise AgentOps config.
2. Build an `AgentOpsRuntimeContext` for the run.
3. Resolve `AgentOpsIdentity` using either ops-direct or store-mediated mode.
4. Capture executable task and task guard facts before code-changing work.
5. Append subsequent stage/gate/verification/artifact/violation facts to a
   local outbox batch.
6. Persist the outbox batch before network delivery.
7. Send the batch to the Gateway endpoint.
8. Parse and persist `runtime_outbox_receipt.v1`.
9. Surface a concise operator status in CLI output.
10. Keep local SDLC usable if AgentOps delivery is unavailable, except where
    enterprise policy requires fail-closed behavior for high-risk actions.

## 9. Outbox Persistence

Ai_AutoSDLC must persist outbox batches locally before sending:

```text
.ai-sdlc/agentops/outbox/{outbox_id}.json
.ai-sdlc/agentops/receipts/{outbox_id}.summary.json
.ai-sdlc/agentops/diagnostics/{outbox_id}.json
```

Receipt summary must preserve:

- `batch_id`
- `outbox_id`
- `producer`
- `replay_reason`
- `outbox_state`
- `accepted_count`
- `deduplicated_count`
- `stale_count`
- `rejected_count`
- `dlq_count`
- item diagnostics for `stale`, `rejected`, and `dlq`
- `audit_id`

Never silently swallow rejected, stale, or DLQ results.

## 10. Retry Semantics

Retry rules:

- Retry network failures, timeouts, HTTP 408, HTTP 429, and HTTP 5xx.
- Do not automatically retry schema-invalid events without code/config change.
- Do not aggressively retry auth/scope failures.
- Use stable `outbox_id`, `batch_id`, `event_id`, `sequence_no`, and
  `idempotency_key` for replay.
- Set `replay_reason` to one of:
  - `initial_delivery`
  - `network_replay`
  - `credential_rotation_replay`
  - `manual_backend_replay`

Retry commands should not mutate event payloads except replay metadata that is
explicitly allowed by the contract.

## 11. CLI / Operator UX

Ai_AutoSDLC should expose these user-facing commands or equivalent surfaces:

```bash
ai-sdlc reporter status
ai-sdlc reporter retry
ai-sdlc reporter doctor
```

Minimum status output:

- current mode: standalone / enterprise_managed / custom_sink
- sink: none / local_file / agentops / custom
- endpoint configured: yes/no, host only
- credential state: configured / missing / rejected / scope_denied
- last outbox id
- last receipt state
- accepted / rejected / dlq counts
- last audit id
- next action

Do not print tokens, signatures, device private keys, or raw payload bodies.

## 12. Local Development Flow

AgentOps local API can run without production auth for development:

```bash
cd /Users/sinclairpan/project/AgentOps
uv run python -m agentops.api.server --host 127.0.0.1 --port 8765
```

Ai_AutoSDLC local development should allow:

```bash
export AI_SDLC_INTEGRATION_MODE=enterprise_managed
export AI_SDLC_REPORTER_SINK=agentops
export AGENTOPS_INGESTION_ENDPOINT=http://127.0.0.1:8766
export AGENTOPS_INGESTION_TOKEN=local-agentops-gateway-token
export AGENTOPS_IDENTITY_MODE=ops_direct
export AGENTOPS_PRODUCER_ID=producer.ai-sdlc.local
export AGENTOPS_RUNTIME_ID=runtime.ai-sdlc.local
export AGENTOPS_CREDENTIAL_ID=cred.ai-sdlc.local
export AGENTOPS_KEY_ID=key.ai-sdlc.local
ai-sdlc agentops doctor --json
ai-sdlc run
ai-sdlc agentops status --json
```

Production must use the Gateway endpoint and Bearer token.

## 13. Acceptance Tests Required In Ai_AutoSDLC

Add tests for these cases before marking the work complete.

### Producer batch and event shape

- Builds `runtime.ingestion.v1` with `producer=Ai_AutoSDLC`.
- Every enterprise event uses `event_envelope.v1`.
- Every SDLC trace event uses `event_type=sdlc_trace_event` and
  `event_type_version=sdlc_trace_event.v1`.
- Ops-direct identity does not include fake `installation_id`.
- Store-mediated identity includes installation/device fields when configured.

### Main flow integration

- `ai-sdlc run` with `reporter.sink=agentops` creates an outbox batch.
- Executable task and code guard facts are included before code-changing events.
- Missing executable task blocks code-change facts with
  `CODE_CHANGE_TASK_REQUIRED`.
- `verified_loaded` without executable task does not mark readiness.

### Gateway delivery

- Bearer token is sent to Gateway.
- `X-AgentOps-*` headers are not locally self-asserted in production mode.
- HTTP 202 receipt is parsed and persisted.
- HTTP 401/403 creates a non-retry-aggressive credential diagnostic.
- HTTP 5xx or timeout leaves outbox pending and retryable.

### Receipt persistence

- Accepted receipt persists summary.
- Rejected/stale/DLQ item results persist diagnostics.
- Receipt summary includes `audit_id`.

### End-to-end fixture compatibility

Use AgentOps fixture as a stable reference:

```text
contracts/cross-project/fixtures/ai_sdlc_executable_task_runtime_batch.v1.json
```

The Ai_AutoSDLC generated happy-path batch must be semantically equivalent to
the fixture:

- same schema versions
- same envelope identity mode semantics
- same SDLC event type vocabulary
- same receipt parser expectations

## 14. Cross-Project Smoke Test

The final joint smoke test should prove this full path:

1. Start AgentOps API.
2. Start API Gateway.
3. Configure Ai_AutoSDLC with Gateway endpoint and token.
4. Run `ai-sdlc run` or intentionally retry a reviewed local outbox.
5. Confirm Ai_AutoSDLC persisted outbox and receipt summary.
6. Confirm AgentOps returns `accepted_count > 0`.
7. Confirm AgentOps `GET /v1/runtime/runs/{run_id}/trace` returns spans.
8. Confirm AgentOps `GET /v1/runtime/runs/{run_id}/evidence-summary` returns
   summary-only evidence.
9. Confirm AgentOps Console snapshot includes SDLC task guard, outbox receipt,
   evidence readiness, and adapter diagnostics.
10. Confirm invalid token, missing scope, schema-invalid event, and AgentOps
    unavailable scenarios produce the expected diagnostics.

## 15. Done Definition

The Ai_AutoSDLC work is done only when all are true:

- `ai-sdlc run` can automatically produce and send AgentOps outbox data when
  configured.
- No AgentOps-specific code path is required for standalone users.
- Gateway Bearer token mode is supported.
- Receipt summaries and diagnostics are persisted locally.
- Retry is available for pending outbox batches.
- `verified_loaded` remains diagnostic-only.
- AgentOps Console can display a real Ai_AutoSDLC run produced by the CLI main
  flow, not only by a unit-test helper or static fixture.

## 16. Implementation Order

Recommended order for Ai_AutoSDLC:

1. Add config resolution for AgentOps reporter mode.
2. Wire producer bridge into `ai-sdlc run` lifecycle.
3. Persist outbox before delivery.
4. Add Gateway Bearer delivery path.
5. Persist receipt summaries and diagnostics.
6. Add reporter status / retry / doctor commands.
7. Add end-to-end local smoke script against AgentOps.
8. Run cross-project validation with AgentOps AO56 fixture and live endpoint.

Do not start with Console-specific assumptions. Console readiness is a consumer
projection owned by AgentOps and must be derived from receipt, trace, evidence,
policy, freshness, and task guard facts.
