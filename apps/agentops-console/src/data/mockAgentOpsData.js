export const routes = [
  { id: "overview", label: "总览", icon: "⌂" },
  { id: "runs", label: "运行记录", icon: "▶" },
  { id: "evidence", label: "证据检索", icon: "◇" },
  { id: "approvals", label: "审批中心", icon: "✓" },
  { id: "policies", label: "策略中心", icon: "!" },
  { id: "quality", label: "质量中心", icon: "质" },
  { id: "risks", label: "风险处置", icon: "△" },
  { id: "agent-store-audit", label: "Agent Store 审计", icon: "AS" },
  { id: "connectors", label: "连接器状态", icon: "∞" },
  { id: "sdlc-runs", label: "Ai_AutoSDLC 运行", icon: "SD" }
];

export const consoleData = {
  summary: {
    adapter: {
      status: "materialized",
      copy: "CLI dry-run 已通过；仍需 verified_loaded 机器证明。",
      proof_source: "AGENTS.md 规范路径",
      captured_at: "2026-05-05T18:42:00-07:00"
    },
    metrics: [
      { label: "今日运行", value: 42, status: "healthy", detail: "39 条可信，3 条需复核" },
      { label: "Policy SLO", value: "P95 860ms", status: "degraded", detail: "高风险动作需在线校验/阻断（require_online/block）" },
      { label: "审批待办", value: 7, status: "pending", detail: "2 条超过 SLA 并已升级" },
      { label: "证据状态", value: "1 条失败", status: "redaction_failed", detail: "原文访问已阻断" }
    ]
  },
  runs: [
    { run_id: "run_20260505_001", id: "run_20260505_001", agent: "发布 Agent", skill: "生产部署", risk_level: "高", l5_state: "healthy", policy_state: "approval_required", evidence_state: "summary_only" },
    { run_id: "run_20260505_002", id: "run_20260505_002", agent: "质检 Agent", skill: "测试执行", risk_level: "中", l5_state: "healthy", policy_state: "conditional_allow", evidence_state: "approved_limited" },
    { run_id: "run_20260505_003", id: "run_20260505_003", agent: "迁移 Agent", skill: "结构变更", risk_level: "高", l5_state: "degraded", policy_state: "block", evidence_state: "redaction_failed" },
    { run_id: "run_20260505_004", id: "run_20260505_004", agent: "商店 Agent", skill: "发布上架", risk_level: "低", l5_state: "unknown", policy_state: "warn", evidence_state: "summary_only" }
  ],
  evidence: [
    { evidence_id: "ev_001", id: "ev_001", run_id: "run_20260505_001", summary: "部署命令摘要已移除敏感值。", payload_hash: "sha256:7a21...", raw_access_state: "summary_only", audit_id: "audit_ev_001", denied_scope: "" },
    { evidence_id: "ev_002", id: "ev_002", run_id: "run_20260505_002", summary: "已获得短时复核窗口的限时授权。", payload_hash: "sha256:91be...", raw_access_state: "approved_limited", audit_id: "audit_ev_002", denied_scope: "" },
    { evidence_id: "ev_003", id: "ev_003", run_id: "run_20260505_003", summary: "脱敏失败，仅保留哈希和告警。", payload_hash: "sha256:ff03...", raw_access_state: "redaction_failed", audit_id: "audit_ev_003", denied_scope: "evidence.raw" },
    { evidence_id: "ev_004", id: "ev_004", run_id: "run_20260505_004", summary: "权限边界隐藏详情，可申请限定范围访问。", payload_hash: "sha256:a031...", raw_access_state: "permission_denied", audit_id: "audit_ev_004", denied_scope: "证据检索.阶段2" }
  ],
  approvals: [
    { approval_id: "ap_001", id: "ap_001", requester: "发布 Agent", reason: "生产部署需要短期 Grant", affected_actions: "deploy:prod", sla_due_at: "2026-05-05 19:20", status: "pending", grant_status: "pending", audit_id: "audit_ap_001" },
    { approval_id: "ap_002", id: "ap_002", requester: "质检 Agent", reason: "复核失败的测试证据", affected_actions: "evidence.raw", sla_due_at: "2026-05-05 18:40", status: "escalated", grant_status: "expired", audit_id: "audit_ap_002" },
    { approval_id: "ap_003", id: "ap_003", requester: "迁移 Agent", reason: "结构迁移被策略阻断", affected_actions: "db.migrate", sla_due_at: "2026-05-05 20:00", status: "approved", grant_status: "active", audit_id: "audit_ap_003" },
    { approval_id: "ap_004", id: "ap_004", requester: "商店 Agent", reason: "已接受发布风险提示", affected_actions: "store.publish", sla_due_at: "2026-05-05 19:10", status: "revoked", grant_status: "revoked", audit_id: "audit_ap_004" }
  ],
  policies: [
    { id: "pol_001", decision: "approval_required", action: "deploy:prod", fallback_action: "require_online", policy_version: "runtime-v2.3", grant_ttl: "15 分钟", audit_id: "audit_pol_001" },
    { id: "pol_002", decision: "block", action: "db.migrate", fallback_action: "block", policy_version: "runtime-v2.3", grant_ttl: "无", audit_id: "audit_pol_002" },
    { id: "pol_003", decision: "conditional_allow", action: "test:run", fallback_action: "无", policy_version: "runtime-v2.2", grant_ttl: "10 分钟", audit_id: "audit_pol_003" },
    { id: "pol_004", decision: "unknown", action: "store.publish", fallback_action: "警告", policy_version: "runtime-v2.1", grant_ttl: "无", audit_id: "req_policy_unknown" }
  ],
  risks: [
    { id: "risk_001", source: "策略中心", severity: "严重", state: "block", owner_hint: "安全/IAM", primary_action: "复核拒绝优先级（deny）", deep_link: "policies" },
    { id: "risk_002", source: "审批中心", severity: "高", state: "escalated", owner_hint: "发布审批人", primary_action: "升级审批", deep_link: "approvals" },
    { id: "risk_003", source: "证据检索", severity: "高", state: "redaction_failed", owner_hint: "证据负责人", primary_action: "仅检查哈希", deep_link: "evidence" },
    { id: "risk_004", source: "Ai_AutoSDLC 运行", severity: "中", state: "unverified", owner_hint: "SDLC 负责人", primary_action: "加载验证证明", deep_link: "sdlc-runs" }
  ],
  quality: [
    { id: "qs_001", signal_id: "qs_001", category: "契约测试", status: "healthy", score: "82/82", evidence_ref: "AO1/AO2 契约套件", owner_hint: "AgentOps 后端", primary_action: "保持基线" },
    { id: "qs_002", signal_id: "qs_002", category: "Browser Gate", status: "degraded", score: "待补充", evidence_ref: "AO3 浏览器矩阵", owner_hint: "前端负责人", primary_action: "采集桌面/移动证据" },
    { id: "qs_003", signal_id: "qs_003", category: "证据完整性", status: "redaction_failed", score: "91%", evidence_ref: "ev_003 已保留哈希", owner_hint: "证据负责人", primary_action: "修复脱敏" },
    { id: "qs_004", signal_id: "qs_004", category: "策略可解释性", status: "unknown", score: "需证明", evidence_ref: "策略要求摘要", owner_hint: "安全/IAM", primary_action: "刷新 SLO" }
  ],
  agentStore: {
    discoveryGaps: [
      { id: "gap_agent_agent_store_0_1_0", gap_id: "gap_agent_agent_store_0_1_0", gap_type: "agent_unregistered", agent_id: "agent.store", version: "0.1.0", skill_id: "", state: "suspected", severity: "高", affected_runs: ["run_20260505_004"], owner_hint: "Agent 负责人", primary_action: "通知负责人补齐 Agent Store 注册事实", audit_id: "audit_gap_agent_agent_store_0_1_0" }
    ],
    runAudits: [
      { id: "audit_run_run_20260505_004", audit_id: "audit_run_run_20260505_004", run_id: "run_20260505_004", agent_id: "agent.store", version: "0.1.0", registration_state: "suspected", event_count: 3, raw_access_state: "summary_only", discovery_gap_ids: ["gap_agent_agent_store_0_1_0"], related_agent_versions: ["agent.store@0.1.0"], deep_links: { agent_id: "agent.store", version: "0.1.0", session_id: "sess_store_004", run_id: "run_20260505_004", installation_id: "inst_store", trace_id: "trace_store_004", audit_id: "audit_run_run_20260505_004", return_url: "/agent-store/agents/agent.store/runs/run_20260505_004" } }
    ],
    storeSummaries: [
      { id: "agent.store@0.1.0:audit_run_run_20260505_004", agent_id: "agent.store", agent_version: "0.1.0", metadata_state: "unregistered", registry_fact_owner: "Agent Store", risk_state: "warning", evidence_level: "L3", confidence: 0.6, missing_evidence: ["l5_eligibility_input"], policy_requirement: { required_by: "AgentOps", source: "runtime_policy", issuer: "AgentOps Policy Service", policy_owner: "安全/IAM", policy_version: "runtime-v2", can_ignore: false, affected_actions: ["运行审计", "高风险 Skill 调用"] }, discovery_gap_ids: ["gap_agent_agent_store_0_1_0"], run_audit: { audit_id: "audit_run_run_20260505_004", registration_state: "suspected", event_count: 3 }, calculated_at: "2026-05-05T18:48:00-07:00", valid_until: "2026-06-04T18:48:00-07:00" }
    ],
    registryMap: [
      { id: "agent.publisher@1.0.0", agent_id: "agent.publisher", version: "1.0.0", metadata_state: "consumed", fact_owner: "Agent Store", skill_count: 2, synced_at: "2026-05-05T18:48:00-07:00" }
    ]
  },
  connectors: [
    { id: "conn_agent_store", name: "Agent Store", status: "healthy", last_seen_at: "2026-05-05 18:48", degrade_action: "无", request_id: "req_conn_agent_store" },
    { id: "conn_sdlc", name: "Ai_AutoSDLC", status: "materialized", last_seen_at: "2026-05-05 18:42", degrade_action: "需要 verified_loaded 证明", request_id: "req_conn_sdlc" },
    { id: "conn_evidence", name: "证据存储", status: "degraded", last_seen_at: "2026-05-05 18:35", degrade_action: "仅展示摘要", request_id: "req_conn_evidence" },
    { id: "conn_policy", name: "策略服务", status: "degraded", last_seen_at: "2026-05-05 18:38", degrade_action: "高风险需在线校验/阻断（require_online/block）", request_id: "req_conn_policy" },
    { id: "conn_iam", name: "IAM/安全", status: "healthy", last_seen_at: "2026-05-05 18:49", degrade_action: "无", request_id: "req_conn_iam" }
  ],
  sdlcRuns: [
    { id: "sdlc_001", command: "ai-sdlc adapter status", adapter_status: "materialized", dry_run_status: "dry_run_passed", proof_source: "AGENTS.md", captured_at: "2026-05-05 18:42", verified_loaded: "unverified" },
    { id: "sdlc_002", command: "ai-sdlc run --dry-run", adapter_status: "materialized", dry_run_status: "dry_run_passed", proof_source: "CLI 预演", captured_at: "2026-05-05 18:43", verified_loaded: "unverified" },
    { id: "sdlc_003", command: "governance load probe", adapter_status: "materialized", dry_run_status: "dry_run_passed", proof_source: "待接入治理加载探针", captured_at: "待采集", verified_loaded: "unverified" }
  ]
};
