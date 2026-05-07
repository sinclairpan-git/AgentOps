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
  operationCenter: {
    notifications: [
      { id: "notif_ap_001", title: "审批待处理", body: "发布 Agent：生产部署需要短期 Grant", status: "pending", route: "approvals", ref: "audit_ap_001", action_id: "action_approval_ap_001" },
      { id: "notif_ev_003", title: "证据需要关注", body: "脱敏失败，仅保留哈希和告警。", status: "redaction_failed", route: "evidence", ref: "audit_ev_003", action_id: "action_evidence_ev_003" },
      { id: "notif_risk_004", title: "Ai_AutoSDLC 运行风险", body: "加载验证证明", status: "unverified", route: "sdlc-runs", ref: "risk_004", action_id: "action_risk_risk_004" }
    ],
    todos: [
      { id: "todo_ap_001", title: "处理审批", body: "生产部署需要短期 Grant", owner: "审批负责人", status: "pending", route: "approvals", due: "2026-05-05 19:20", action_id: "action_approval_ap_001" },
      { id: "todo_ev_003", title: "处理证据访问", body: "脱敏失败，仅保留哈希和告警。", owner: "证据负责人", status: "redaction_failed", route: "evidence", due: "需复核", action_id: "action_evidence_ev_003" },
      { id: "todo_gap_agent_agent_store_0_1_0", title: "补齐 Agent Store 注册事实", body: "agent.store / 0.1.0", owner: "Agent 负责人", status: "suspected", route: "agent-store-audit", due: "待排期", action_id: "action_gap_gap_agent_agent_store_0_1_0" }
    ],
    searchIndex: [
      { id: "run_20260505_001", kind: "运行记录", title: "发布 Agent / 生产部署", route: "runs", status: "healthy" },
      { id: "ev_003", kind: "证据检索", title: "脱敏失败，仅保留哈希和告警。", route: "evidence", status: "redaction_failed", action_id: "action_evidence_ev_003" },
      { id: "ap_001", kind: "审批中心", title: "生产部署需要短期 Grant", route: "approvals", status: "pending", action_id: "action_approval_ap_001" },
      { id: "gap_agent_agent_store_0_1_0", kind: "Agent Store 审计", title: "通知负责人补齐 Agent Store 注册事实", route: "agent-store-audit", status: "suspected", action_id: "action_gap_gap_agent_agent_store_0_1_0" }
    ]
  },
  actionWorkbench: {
    details: [
      { id: "action_approval_ap_001", title: "审批处置", summary: "生产部署需要短期 Grant", status: "pending", route: "approvals", owner: "审批负责人", primary_action: "处理审批", secondary_action: "补充材料或转交审批", close_condition: "SLA 重置或审批状态更新为完成态。", audit_ref: "audit_ap_001", evidence_ref: "", related_ref: "ap_001", safety_note: "当前为只读处置预案，不执行生产写操作。" },
      { id: "action_approval_ap_002", title: "审批处置", summary: "复核失败的测试证据", status: "escalated", route: "approvals", owner: "审批负责人", primary_action: "处理审批", secondary_action: "补充材料或转交审批", close_condition: "SLA 重置或审批状态更新为完成态。", audit_ref: "audit_ap_002", evidence_ref: "", related_ref: "ap_002", safety_note: "当前为只读处置预案，不执行生产写操作。" },
      { id: "action_approval_ap_003", title: "审批处置", summary: "结构迁移被策略阻断", status: "approved", route: "approvals", owner: "审批负责人", primary_action: "查看审批记录", secondary_action: "查看 Grant 状态", close_condition: "SLA 重置或审批状态更新为完成态。", audit_ref: "audit_ap_003", evidence_ref: "", related_ref: "ap_003", safety_note: "当前为只读处置预案，不执行生产写操作。" },
      { id: "action_approval_ap_004", title: "审批处置", summary: "已接受发布风险提示", status: "revoked", route: "approvals", owner: "审批负责人", primary_action: "查看撤销原因", secondary_action: "通知申请方", close_condition: "SLA 重置或审批状态更新为完成态。", audit_ref: "audit_ap_004", evidence_ref: "", related_ref: "ap_004", safety_note: "当前为只读处置预案，不执行生产写操作。" },
      { id: "action_evidence_ev_001", title: "证据处置", summary: "部署命令摘要已移除敏感值。", status: "summary_only", route: "evidence", owner: "证据负责人", primary_action: "查看安全摘要", secondary_action: "申请限定范围访问", close_condition: "安全摘要可解释、哈希可追溯，且无需查看原文。", audit_ref: "audit_ev_001", evidence_ref: "ev_001", related_ref: "run_20260505_001", safety_note: "当前为只读处置预案，不执行生产写操作。" },
      { id: "action_evidence_ev_002", title: "证据处置", summary: "已获得短时复核窗口的限时授权。", status: "approved_limited", route: "evidence", owner: "证据负责人", primary_action: "查看授权记录", secondary_action: "查看到期时间", close_condition: "限定范围授权仍在有效期内，审计引用可追溯。", audit_ref: "audit_ev_002", evidence_ref: "ev_002", related_ref: "run_20260505_002", safety_note: "当前为只读处置预案，不执行生产写操作。" },
      { id: "action_evidence_ev_003", title: "证据处置", summary: "脱敏失败，仅保留哈希和告警。", status: "redaction_failed", route: "evidence", owner: "证据负责人", primary_action: "查看安全摘要", secondary_action: "申请限定范围访问", close_condition: "脱敏摘要可解释、哈希可追溯，且原文访问已审批或明确拒绝。", audit_ref: "audit_ev_003", evidence_ref: "ev_003", related_ref: "run_20260505_003", safety_note: "当前为只读处置预案，不执行生产写操作。" },
      { id: "action_evidence_ev_004", title: "证据处置", summary: "权限边界隐藏详情，可申请限定范围访问。", status: "permission_denied", route: "evidence", owner: "证据负责人", primary_action: "查看申请预案", secondary_action: "补充申请理由", close_condition: "脱敏摘要可解释、哈希可追溯，且原文访问已审批或明确拒绝。", audit_ref: "audit_ev_004", evidence_ref: "ev_004", related_ref: "run_20260505_004", safety_note: "当前为只读处置预案，不执行生产写操作。" },
      { id: "action_risk_risk_001", title: "策略中心 风险处置", summary: "策略中心 / 严重 / 复核拒绝优先级（deny）", status: "block", route: "policies", owner: "安全/IAM", primary_action: "复核拒绝优先级（deny）", secondary_action: "转交负责人", close_condition: "处置动作完成，审计引用可追溯，风险状态不再阻塞当前队列。", audit_ref: "risk_001", evidence_ref: "", related_ref: "策略中心", safety_note: "当前为只读处置预案，不执行生产写操作。" },
      { id: "action_risk_risk_002", title: "审批中心 风险处置", summary: "审批中心 / 高 / 升级审批", status: "escalated", route: "approvals", owner: "发布审批人", primary_action: "升级审批", secondary_action: "转交负责人", close_condition: "SLA 重置或审批完成，且 Grant 状态完成同步。", audit_ref: "risk_002", evidence_ref: "", related_ref: "审批中心", safety_note: "当前为只读处置预案，不执行生产写操作。" },
      { id: "action_risk_risk_003", title: "证据检索 风险处置", summary: "证据检索 / 高 / 仅检查哈希", status: "redaction_failed", route: "evidence", owner: "证据负责人", primary_action: "仅检查哈希", secondary_action: "转交负责人", close_condition: "证据摘要可解释，脱敏失败或拒绝范围已有审计说明。", audit_ref: "risk_003", evidence_ref: "", related_ref: "证据检索", safety_note: "当前为只读处置预案，不执行生产写操作。" },
      { id: "action_risk_risk_004", title: "Ai_AutoSDLC 运行风险处置", summary: "Ai_AutoSDLC 运行 / 中 / 加载验证证明", status: "unverified", route: "sdlc-runs", owner: "SDLC 负责人", primary_action: "加载验证证明", secondary_action: "转交负责人", close_condition: "adapter 证明状态明确，不能将 materialized/unverified 误判为 verified_loaded。", audit_ref: "risk_004", evidence_ref: "", related_ref: "Ai_AutoSDLC 运行", safety_note: "当前为只读处置预案，不执行生产写操作。" },
      { id: "action_gap_gap_agent_agent_store_0_1_0", title: "Agent Store 注册事实处置", summary: "发现 Agent 未注册，需要回到 Agent Store 补齐注册事实。", status: "suspected", route: "agent-store-audit", owner: "Agent 负责人", primary_action: "通知负责人补齐 Agent Store 注册事实", secondary_action: "转交 Agent 负责人", close_condition: "Agent Store 注册事实已同步为已治理、已忽略或已阻断，且影响运行已完成审计回显。", audit_ref: "audit_gap_agent_agent_store_0_1_0", evidence_ref: "", related_ref: "run_20260505_004", safety_note: "当前为只读处置预案，不执行生产写操作。" }
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

const slug = (value) => String(value).replace(/[^a-zA-Z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "unknown";

const echoTargets = (actionId) => {
  if (actionId.startsWith("action_gap_")) {
    return ["Agent Store 审计", "风险处置", "通知中心"];
  }
  if (actionId.startsWith("action_approval_")) {
    return ["审批中心", "待办中心", "审计详情"];
  }
  if (actionId.startsWith("action_evidence_")) {
    return ["证据检索", "风险处置", "审计详情"];
  }
  return ["风险处置", "通知中心", "审计详情"];
};

const timelineFor = (detail) => [
  {
    id: `tl_${slug(detail.id)}_detected`,
    stage: "发现",
    occurred_at: "快照生成时",
    title: "治理信号进入处置队列",
    body: detail.summary,
    owner: detail.owner,
    status: detail.status
  },
  {
    id: `tl_${slug(detail.id)}_triage`,
    stage: "研判",
    occurred_at: "快照生成时",
    title: "已生成建议动作",
    body: `建议动作：${detail.primary_action}。`,
    owner: detail.owner,
    status: detail.status
  },
  {
    id: `tl_${slug(detail.id)}_close`,
    stage: "关闭",
    occurred_at: "待完成",
    title: "等待关闭证明",
    body: detail.close_condition,
    owner: detail.owner,
    status: "pending"
  }
];

const auditPacketFor = (detail) => ({
  packet_id: `packet_${slug(detail.id)}`,
  summary: `只读复核包：${detail.title}。${detail.summary}`,
  export_state: "只读摘要已生成",
  evidence_refs: [detail.audit_ref, detail.evidence_ref, detail.related_ref].filter(Boolean),
  echo_targets: echoTargets(detail.id),
  retention_policy: "仅保留摘要、哈希和审计引用；不包含 Evidence Vault 原文。",
  safety_note: "只读复核包仅用于审计复核，不提供原文下载或生产写操作。"
});

consoleData.actionWorkbench.details = consoleData.actionWorkbench.details.map((detail) => ({
  ...detail,
  timeline: timelineFor(detail),
  audit_packet: auditPacketFor(detail)
}));

const adoptionMissingEvidence = (item) => {
  const missing = [];
  if (["unknown", "degraded", "redaction_failed", "pending"].includes(item.status)) {
    missing.push("可验证质量证据");
  }
  if (!item.evidence_ref || item.evidence_ref.includes("待")) {
    missing.push("证据引用");
  }
  return missing.length ? missing : ["无阻断缺口"];
};

const adoptionEvidenceLevel = (status) => {
  if (status === "healthy") {
    return "L5";
  }
  if (["degraded", "redaction_failed", "unknown"].includes(status)) {
    return "L3";
  }
  return "pending";
};

const adoptionConfidence = (status) => {
  if (status === "healthy") {
    return 0.92;
  }
  if (["degraded", "redaction_failed"].includes(status)) {
    return 0.68;
  }
  if (status === "unknown") {
    return 0.45;
  }
  return 0.58;
};

const generatedLines = Math.max(consoleData.runs.length, 1) * 180;
const degradedQuality = consoleData.quality.filter((item) => item.status !== "healthy").length;
const blockedRisks = consoleData.risks.filter((item) => ["block", "redaction_failed", "unverified", "degraded"].includes(item.state)).length;
const retainedLines = Math.max(generatedLines - degradedQuality * 24 - blockedRisks * 16, 0);

consoleData.adoption = {
  metrics: {
    generated_lines: generatedLines,
    retained_lines: retainedLines,
    human_modified_lines: degradedQuality * 18 + blockedRisks * 9,
    deleted_lines: degradedQuality * 7 + blockedRisks * 5,
    rework_rounds: Math.max(degradedQuality, blockedRisks),
    pr_review_findings: degradedQuality + blockedRisks,
    ci_failure_types: ["证据脱敏失败", "策略阻断", "治理加载证明缺失"],
    retention_rate: `${Math.round(retainedLines / generatedLines * 100)}%`
  },
  explanationChains: consoleData.quality.map((item) => ({
    id: `chain_${slug(item.signal_id || item.id)}`,
    signal_id: item.signal_id,
    category: item.category,
    status: item.status,
    score: item.score,
    score_template_id: `quality_summary_${slug(item.category)}`,
    evidence_level: adoptionEvidenceLevel(item.status),
    confidence: adoptionConfidence(item.status),
    missing_evidence: adoptionMissingEvidence(item),
    explanation: `${item.category} 当前评分为 ${item.score}，依据 ${item.evidence_ref} 形成摘要判断。`,
    appeal_path: `联系${item.owner_hint}补充证据或发起人工复核。`,
    lifecycle_guardrail: "低置信不自动下架。"
  })),
  segments: [
    { id: "segment_sdlc_runs", title: "Ai_AutoSDLC 标准路径", status: "healthy", retention_rate: `${Math.round(retainedLines / generatedLines * 100)}%`, affected_agents: String(consoleData.runs.length), owner: "SDLC 负责人", next_review: "按周复核采纳摘要" },
    { id: "segment_agent_store_echo", title: "Agent Store 回显", status: "pending", retention_rate: "待采集", affected_agents: String(consoleData.agentStore.storeSummaries.length), owner: "Agent 负责人", next_review: "等待注册事实同步后复核" }
  ],
  reviewSignals: [
    ...consoleData.quality
      .filter((item) => item.status !== "healthy")
      .map((item) => ({
        id: `review_${slug(item.signal_id || item.id)}`,
        title: `${item.category} 需要人工复核`,
        status: item.status,
        owner: item.owner_hint,
        evidence_ref: item.evidence_ref,
        reason: "低置信或缺失证据只进入复核队列，不自动下架。",
        action: "发起人工复核"
      })),
    ...consoleData.risks
      .filter((item) => ["block", "redaction_failed", "unverified"].includes(item.state))
      .map((item) => ({
        id: `review_${slug(item.id)}`,
        title: `${item.source} 影响采纳判断`,
        status: item.state,
        owner: item.owner_hint,
        evidence_ref: item.id,
        reason: "风险归因会降低采纳置信度，但不触发自动生命周期动作。",
        action: "补充风险处置证明"
      }))
  ].slice(0, 8),
  guardrails: [
    "低置信不自动下架，只进入人工复核和申诉路径。",
    "缺失证据不按 0 分处理，必须展示 missing_evidence。",
    "采纳指标只展示聚合摘要，不包含代码片段、差异内容或 PR 原文。",
    "本阶段不写 Agent Store，不自动降推荐。"
  ]
};
