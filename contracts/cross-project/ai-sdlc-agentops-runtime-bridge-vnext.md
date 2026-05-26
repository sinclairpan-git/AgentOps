# Ai_AutoSDLC -> AgentOps Runtime Bridge vNext Contract

Canonical copy: `specs/056-sdlc-v0-7-18-executable-task-runtime-bridge/contracts/ai-sdlc-agentops-runtime-bridge-vnext.md`.

This root-level copy is provided for cross-project discovery. The owning AgentOps work item is `056-sdlc-v0-7-18-executable-task-runtime-bridge`.

Key points:

- Ai_AutoSDLC produces executable-task-aware runtime facts.
- AgentOps consumes `runtime.ingestion.v1` at `POST /v1/runtime/events`.
- AgentOps returns `runtime_outbox_receipt.v1`.
- `verified_loaded` is adapter diagnostic only, not the main gate.
- Agent Store is not the required transit path for SDLC Outbox runtime facts.

See the canonical work-item contract for the full schema, readiness rules, Console mapping, and error codes.
