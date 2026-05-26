# AgentOps API Gateway Runtime Ingestion

**Status**: AO57 production boundary baseline  
**Audience**: AgentOps deployers and Ai_AutoSDLC integrators  

## Purpose

AgentOps production mode does not accept end-user supplied identity headers as
authority. Runtime producers, including Ai_AutoSDLC, call an API Gateway with a
Bearer token. The Gateway validates that token and then injects trusted upstream
identity headers when forwarding to AgentOps.

```text
Ai_AutoSDLC
  -> Authorization: Bearer <producer token>
  -> API Gateway
  -> X-AgentOps-* upstream identity headers
  -> AgentOps POST /v1/runtime/events
```

## Required Gateway Behavior

The Gateway must:

- validate the producer Bearer token;
- reject invalid, expired, or revoked tokens before forwarding;
- remove any inbound `X-AgentOps-*` headers from the client request;
- inject fresh `X-AgentOps-*` headers after successful token validation;
- forward only the allowed runtime ingestion route for producer tokens;
- enforce request size, timeout, and rate limits;
- log request id, audit id, producer principal, and outcome without logging token
  material or raw payload bodies.

## Forwarded Headers

Minimum headers for Ai_AutoSDLC runtime ingestion:

```http
X-AgentOps-Principal: producer.ai-sdlc.<id>
X-AgentOps-Roles: agentops-ingestor
X-AgentOps-Scopes: event.ingest
X-AgentOps-Request-Id: req_<gateway-generated>
X-AgentOps-Audit-Id: audit_<gateway-generated>
```

AgentOps authorizes `POST /v1/runtime/events` with the `event.ingest` scope.
`agentops-ingestor` includes that scope.

## Ai_AutoSDLC Request

Ai_AutoSDLC should call the Gateway endpoint:

```http
POST /v1/runtime/events
Authorization: Bearer <AGENTOPS_INGESTION_TOKEN>
Content-Type: application/json
Accept: application/json
```

The payload remains the AO56 canonical `runtime.ingestion.v1` batch. The token
must not be placed inside the JSON body.

## AgentOps Rejection Semantics

| Condition | AgentOps response | Retry guidance |
|---|---|---|
| Missing Gateway identity headers | `401 UPSTREAM_IDENTITY_REQUIRED` | Do not retry aggressively |
| Principal lacks `event.ingest` | `403 AGENTOPS_SCOPE_DENIED` | Fix token/scope |
| Schema invalid | `400 EVENT_SCHEMA_UNSUPPORTED` or specific error | Fix producer payload |
| Accepted or replayed batch | `202 runtime_outbox_receipt.v1` | Persist receipt |

AgentOps auth errors must not echo Bearer tokens, device keys, credential
secrets, raw payloads, diffs, or file contents.

## Deployment Notes

For local development only, AgentOps may run without `--require-auth` and
Ai_AutoSDLC may point directly at `http://127.0.0.1:8765`.

For production AgentOps API:

```bash
AGENTOPS_DATABASE_URL=postgresql://agentops:...@postgres:5432/agentops
AGENTOPS_POSTGRES_AUTO_MIGRATE=true
python -m agentops.api.server --host 0.0.0.0 --port 8765 --require-auth
```

For the included reference Gateway:

```bash
AGENTOPS_GATEWAY_TOKEN=<producer-token>
AGENTOPS_UPSTREAM_BASE=http://127.0.0.1:8765
AGENTOPS_GATEWAY_PRINCIPAL=producer.ai-sdlc.local
AGENTOPS_GATEWAY_ROLES=agentops-ingestor
AGENTOPS_GATEWAY_SCOPES=event.ingest
python -m agentops.api.gateway --host 0.0.0.0 --port 8766
```

The reference Gateway is intended for local and small-server smoke deployments.
Managed production environments may replace it with Nginx, Envoy, Cloudflare
Workers, or another API Gateway as long as the required behavior above remains
identical.

For local compose smoke, the reference Gateway also proxies
`GET /v1/console/snapshot` with operator read scopes. This lets the Console use
`VITE_AGENTOPS_API_BASE=http://127.0.0.1:8766` and still read real AgentOps API
snapshots. Production deployments should put that Console read path behind their
normal user-facing auth layer.

The public ingress should be the Gateway URL, not the raw AgentOps API URL.

## Pseudo Gateway Flow

```text
on request:
  require path == /v1/runtime/events
  require method == POST
  token = parse Authorization Bearer
  producer = validate token
  strip inbound X-AgentOps-* headers
  set X-AgentOps-Principal = producer.principal
  set X-AgentOps-Roles = agentops-ingestor
  set X-AgentOps-Scopes = event.ingest
  set X-AgentOps-Request-Id = generated request id
  set X-AgentOps-Audit-Id = generated audit id
  proxy to AgentOps internal API
```
