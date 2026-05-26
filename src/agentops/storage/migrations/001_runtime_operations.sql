-- AgentOps AO57 runtime operations persistence baseline.
-- PostgreSQL is the canonical store for runtime facts, receipts, DLQ, and audit.

CREATE TABLE IF NOT EXISTS agentops_runtime_idempotency (
  idempotency_key TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agentops_runtime_runs (
  run_id TEXT NOT NULL,
  attempt_no_identity TEXT NOT NULL,
  event_id TEXT NOT NULL,
  trace_id TEXT NOT NULL DEFAULT '',
  agent_id TEXT NOT NULL DEFAULT '',
  version TEXT NOT NULL DEFAULT '',
  sequence_no DOUBLE PRECISION NOT NULL DEFAULT 0,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  record JSONB NOT NULL,
  PRIMARY KEY (run_id, attempt_no_identity)
);

CREATE INDEX IF NOT EXISTS idx_agentops_runtime_runs_agent_version
  ON agentops_runtime_runs (agent_id, version, received_at DESC);

CREATE TABLE IF NOT EXISTS agentops_trace_spans (
  run_id TEXT NOT NULL,
  trace_id TEXT NOT NULL,
  attempt_no_identity TEXT NOT NULL,
  span_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  sequence_no DOUBLE PRECISION NOT NULL DEFAULT 0,
  start_time TEXT NOT NULL DEFAULT '',
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  record JSONB NOT NULL,
  PRIMARY KEY (run_id, trace_id, attempt_no_identity, span_id)
);

CREATE INDEX IF NOT EXISTS idx_agentops_trace_spans_run_time
  ON agentops_trace_spans (run_id, start_time, span_id);

CREATE INDEX IF NOT EXISTS idx_agentops_trace_spans_trace
  ON agentops_trace_spans (trace_id);

CREATE TABLE IF NOT EXISTS agentops_guardrail_results (
  run_id TEXT NOT NULL,
  attempt_no_identity TEXT NOT NULL,
  guardrail_result_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  sequence_no DOUBLE PRECISION NOT NULL DEFAULT 0,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  record JSONB NOT NULL,
  PRIMARY KEY (run_id, attempt_no_identity, guardrail_result_id)
);

CREATE TABLE IF NOT EXISTS agentops_runtime_dlq (
  event_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL DEFAULT '',
  agent_id TEXT NOT NULL DEFAULT '',
  version TEXT NOT NULL DEFAULT '',
  event_type TEXT NOT NULL DEFAULT '',
  event_type_version TEXT NOT NULL DEFAULT '',
  schema_version TEXT NOT NULL DEFAULT '',
  sequence_no DOUBLE PRECISION,
  idempotency_key TEXT NOT NULL DEFAULT '',
  payload_hash TEXT NOT NULL DEFAULT '',
  payload_ref TEXT NOT NULL DEFAULT '',
  source_trust TEXT NOT NULL DEFAULT '',
  integration_mode TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,
  state TEXT NOT NULL,
  error_code TEXT NOT NULL,
  message TEXT NOT NULL,
  retryable BOOLEAN NOT NULL DEFAULT true,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  record JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agentops_runtime_dlq_agent_version
  ON agentops_runtime_dlq (agent_id, version, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_agentops_runtime_dlq_run
  ON agentops_runtime_dlq (run_id, received_at DESC);

CREATE TABLE IF NOT EXISTS agentops_runtime_outbox_receipts (
  receipt_id TEXT PRIMARY KEY,
  batch_id TEXT NOT NULL,
  outbox_id TEXT NOT NULL,
  producer TEXT NOT NULL DEFAULT '',
  replay_reason TEXT NOT NULL DEFAULT '',
  outbox_state TEXT NOT NULL,
  accepted_count INTEGER NOT NULL DEFAULT 0,
  deduplicated_count INTEGER NOT NULL DEFAULT 0,
  stale_count INTEGER NOT NULL DEFAULT 0,
  rejected_count INTEGER NOT NULL DEFAULT 0,
  dlq_count INTEGER NOT NULL DEFAULT 0,
  audit_id TEXT NOT NULL DEFAULT '',
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  record JSONB NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_agentops_runtime_outbox_receipts_batch
  ON agentops_runtime_outbox_receipts (batch_id);

CREATE INDEX IF NOT EXISTS idx_agentops_runtime_outbox_receipts_outbox
  ON agentops_runtime_outbox_receipts (outbox_id);

CREATE TABLE IF NOT EXISTS agentops_audit_records (
  audit_id TEXT NOT NULL,
  request_id TEXT NOT NULL,
  action TEXT NOT NULL,
  outcome TEXT NOT NULL,
  principal TEXT NOT NULL DEFAULT '',
  roles JSONB NOT NULL DEFAULT '[]'::jsonb,
  scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
  resource TEXT NOT NULL DEFAULT '',
  denied_scope TEXT NOT NULL DEFAULT '',
  error_code TEXT NOT NULL DEFAULT '',
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  record JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agentops_audit_records_lookup
  ON agentops_audit_records (audit_id, request_id, recorded_at DESC);

