export const routes = [
  { id: "overview", label: "Overview", icon: "⌂" },
  { id: "runs", label: "Runs", icon: "▶" },
  { id: "evidence", label: "Evidence Explorer", icon: "◇" },
  { id: "approvals", label: "Approval Center", icon: "✓" },
  { id: "policies", label: "Policy Center", icon: "!" },
  { id: "quality", label: "Quality Center", icon: "QC" },
  { id: "risks", label: "Risk Triage", icon: "△" },
  { id: "connectors", label: "Connector Status", icon: "∞" },
  { id: "sdlc-runs", label: "Ai_AutoSDLC Runs", icon: "SD" }
];

export const consoleData = {
  summary: {
    adapter: {
      status: "materialized",
      copy: "CLI dry-run passed; verified_loaded proof is still required.",
      proof_source: "AGENTS.md canonical path",
      captured_at: "2026-05-05T18:42:00-07:00"
    },
    metrics: [
      { label: "Runs Today", value: 42, status: "healthy", detail: "39 trusted, 3 need review" },
      { label: "Policy SLO", value: "P95 860ms", status: "degraded", detail: "High-risk actions require_online/block" },
      { label: "Approvals", value: 7, status: "pending", detail: "2 past SLA and escalated" },
      { label: "Evidence", value: "1 failed", status: "redaction_failed", detail: "Raw access is blocked" }
    ]
  },
  runs: [
    { run_id: "run_20260505_001", id: "run_20260505_001", agent: "release-agent", skill: "deploy", risk_level: "high", l5_state: "healthy", policy_state: "approval_required", evidence_state: "summary_only" },
    { run_id: "run_20260505_002", id: "run_20260505_002", agent: "qa-agent", skill: "test", risk_level: "medium", l5_state: "healthy", policy_state: "conditional_allow", evidence_state: "approved_limited" },
    { run_id: "run_20260505_003", id: "run_20260505_003", agent: "migration-agent", skill: "schema-change", risk_level: "high", l5_state: "degraded", policy_state: "block", evidence_state: "redaction_failed" },
    { run_id: "run_20260505_004", id: "run_20260505_004", agent: "store-agent", skill: "publish", risk_level: "low", l5_state: "unknown", policy_state: "warn", evidence_state: "summary_only" }
  ],
  evidence: [
    { evidence_id: "ev_001", id: "ev_001", run_id: "run_20260505_001", summary: "Deploy command summary with sensitive values removed.", payload_hash: "sha256:7a21...", raw_access_state: "summary_only", audit_id: "audit_ev_001", denied_scope: "" },
    { evidence_id: "ev_002", id: "ev_002", run_id: "run_20260505_002", summary: "Limited approval exists for a short review window.", payload_hash: "sha256:91be...", raw_access_state: "approved_limited", audit_id: "audit_ev_002", denied_scope: "" },
    { evidence_id: "ev_003", id: "ev_003", run_id: "run_20260505_003", summary: "Hash retained because redaction failed.", payload_hash: "sha256:ff03...", raw_access_state: "redaction_failed", audit_id: "audit_ev_003", denied_scope: "evidence.raw" },
    { evidence_id: "ev_004", id: "ev_004", run_id: "run_20260505_004", summary: "Permission boundary hides detail; request scoped access.", payload_hash: "sha256:a031...", raw_access_state: "permission_denied", audit_id: "audit_ev_004", denied_scope: "Evidence Explorer.stage2" }
  ],
  approvals: [
    { approval_id: "ap_001", id: "ap_001", requester: "release-agent", reason: "Production deploy needs short grant", affected_actions: "deploy:prod", sla_due_at: "2026-05-05 19:20", status: "pending", grant_status: "pending", audit_id: "audit_ap_001" },
    { approval_id: "ap_002", id: "ap_002", requester: "qa-agent", reason: "Review failed test artifact", affected_actions: "evidence.raw", sla_due_at: "2026-05-05 18:40", status: "escalated", grant_status: "expired", audit_id: "audit_ap_002" },
    { approval_id: "ap_003", id: "ap_003", requester: "migration-agent", reason: "Schema migration blocked by policy", affected_actions: "db.migrate", sla_due_at: "2026-05-05 20:00", status: "approved", grant_status: "active", audit_id: "audit_ap_003" },
    { approval_id: "ap_004", id: "ap_004", requester: "store-agent", reason: "Publish warning accepted", affected_actions: "store.publish", sla_due_at: "2026-05-05 19:10", status: "revoked", grant_status: "revoked", audit_id: "audit_ap_004" }
  ],
  policies: [
    { id: "pol_001", decision: "approval_required", action: "deploy:prod", fallback_action: "require_online", policy_version: "runtime-v2.3", grant_ttl: "15m", audit_id: "audit_pol_001" },
    { id: "pol_002", decision: "block", action: "db.migrate", fallback_action: "block", policy_version: "runtime-v2.3", grant_ttl: "none", audit_id: "audit_pol_002" },
    { id: "pol_003", decision: "conditional_allow", action: "test:run", fallback_action: "none", policy_version: "runtime-v2.2", grant_ttl: "10m", audit_id: "audit_pol_003" },
    { id: "pol_004", decision: "unknown", action: "store.publish", fallback_action: "warn", policy_version: "runtime-v2.1", grant_ttl: "none", audit_id: "req_policy_unknown" }
  ],
  risks: [
    { id: "risk_001", source: "Policy Center", severity: "critical", state: "block", owner_hint: "Security/IAM", primary_action: "Review deny priority", deep_link: "policies" },
    { id: "risk_002", source: "Approval Center", severity: "high", state: "escalated", owner_hint: "Release approver", primary_action: "Escalate approval", deep_link: "approvals" },
    { id: "risk_003", source: "Evidence Explorer", severity: "high", state: "redaction_failed", owner_hint: "Evidence owner", primary_action: "Inspect hash only", deep_link: "evidence" },
    { id: "risk_004", source: "Ai_AutoSDLC Runs", severity: "medium", state: "unverified", owner_hint: "SDLC owner", primary_action: "Load verified proof", deep_link: "sdlc-runs" }
  ],
  quality: [
    { id: "qs_001", signal_id: "qs_001", category: "Contract Tests", status: "healthy", score: "82/82", evidence_ref: "AO1/AO2 contract suite", owner_hint: "AgentOps backend", primary_action: "Keep baseline" },
    { id: "qs_002", signal_id: "qs_002", category: "Browser Gate", status: "degraded", score: "pending", evidence_ref: "AO3 browser matrix", owner_hint: "Frontend owner", primary_action: "Capture desktop/mobile" },
    { id: "qs_003", signal_id: "qs_003", category: "Evidence Completeness", status: "redaction_failed", score: "91%", evidence_ref: "ev_003 hash retained", owner_hint: "Evidence owner", primary_action: "Fix redaction" },
    { id: "qs_004", signal_id: "qs_004", category: "Policy Explainability", status: "unknown", score: "needs proof", evidence_ref: "policy req summary", owner_hint: "Security/IAM", primary_action: "Refresh SLO" }
  ],
  connectors: [
    { id: "conn_agent_store", name: "Agent Store", status: "healthy", last_seen_at: "2026-05-05 18:48", degrade_action: "none", request_id: "req_conn_agent_store" },
    { id: "conn_sdlc", name: "AI-SDLC", status: "materialized", last_seen_at: "2026-05-05 18:42", degrade_action: "Need verified_loaded evidence", request_id: "req_conn_sdlc" },
    { id: "conn_evidence", name: "Evidence Store", status: "degraded", last_seen_at: "2026-05-05 18:35", degrade_action: "Summary only", request_id: "req_conn_evidence" },
    { id: "conn_policy", name: "Policy Service", status: "degraded", last_seen_at: "2026-05-05 18:38", degrade_action: "High-risk require_online/block", request_id: "req_conn_policy" },
    { id: "conn_iam", name: "IAM/Security", status: "healthy", last_seen_at: "2026-05-05 18:49", degrade_action: "none", request_id: "req_conn_iam" }
  ],
  sdlcRuns: [
    { id: "sdlc_001", command: "ai-sdlc adapter status", adapter_status: "materialized", dry_run_status: "dry_run_passed", proof_source: "AGENTS.md", captured_at: "2026-05-05 18:42", verified_loaded: "unverified" },
    { id: "sdlc_002", command: "ai-sdlc run --dry-run", adapter_status: "materialized", dry_run_status: "dry_run_passed", proof_source: "CLI rehearsal", captured_at: "2026-05-05 18:43", verified_loaded: "unverified" },
    { id: "sdlc_003", command: "governance load probe", adapter_status: "verified_loaded", dry_run_status: "dry_run_passed", proof_source: "machine-verifiable adapter evidence", captured_at: "pending", verified_loaded: "verified_loaded" }
  ]
};
