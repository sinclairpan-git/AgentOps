import { consoleData as mockConsoleData, routes as mockRoutes } from "./mockAgentOpsData.js";

export const SNAPSHOT_SCHEMA_VERSION = "agentops.console.snapshot.v1";
export const SNAPSHOT_TIMEOUT_MS = 3000;

const allowedStates = new Set([
  "healthy",
  "created",
  "allow",
  "conditional_allow",
  "warn",
  "approval_required",
  "block",
  "blocked",
  "succeeded",
  "failed",
  "cancelled",
  "timeout",
  "approval_paused",
  "trace_pending",
  "running",
  "ok",
  "waiting",
  "error",
  "unset",
  "degraded",
  "unknown",
  "empty",
  "pending",
  "needs_more_info",
  "approved",
  "rejected",
  "expired",
  "revoked",
  "escalated",
  "active",
  "consumed",
  "summary_only",
  "pending_approval",
  "approved_limited",
  "redaction_failed",
  "permission_denied",
  "materialized",
  "verified_loaded",
  "unsupported",
  "dry_run_passed",
  "unverified",
  "suspected",
  "governed",
  "registered",
  "unregistered",
  "normal",
  "warning",
  "ready",
  "insufficient_data",
  "watching",
  "needs_review",
  "critical",
  "insufficient_evidence",
  "no_receipts",
  "receiving",
  "incomplete",
  "review_required",
  "disable_review_recommended",
  "ready_for_manual_approval",
  "needs_human_review",
  "candidate",
  "draft",
  "retired",
  "neutral",
  "improved",
  "negative",
  "credential_issued",
  "signature_verified",
  "not_asserted",
  "authenticated"
]);

const requiredRouteIds = [
  "overview",
  "runs",
  "evidence",
  "approvals",
  "policies",
  "quality",
  "risks",
  "agent-store-audit",
  "credential-handoff",
  "connectors",
  "sdlc-runs"
];

const fallbackSnapshot = (reason) => ({
  source: "mock_fallback",
  sourceState: {
    status: "degraded",
    label: "后端快照不可用",
    copy: reason || "已切换到本地安全样例，当前内容不能作为真实运行事实。",
    generatedAt: "未生成",
    sourceType: "本地安全样例",
    sourceSummary: "后端生成失败后使用的脱敏样例，不包含真实运行事实。",
    request_id: "req_console_snapshot_fallback",
    primary_action: "重试拉取"
  },
  routes: mockRoutes,
  consoleData: consoleDataWithWorkbenchDefaults({
    ...mockConsoleData,
    summary: {
      ...mockConsoleData.summary,
      adapter: {
        ...mockConsoleData.summary.adapter,
        copy: "后端快照不可用；当前展示本地安全样例。"
      }
    }
  })
});

const apiSnapshot = (snapshot) => {
  const repositoryBacked = snapshot.source_detail?.mode === "repository_backed";
  return {
    source: "api_snapshot",
    sourceState: {
      status: "healthy",
      label: repositoryBacked ? "后端事实快照已连接" : "后端快照已连接",
      copy: repositoryBacked
        ? "页面正在展示由 AgentOps 事件仓库生成的治理快照。"
        : "页面正在展示 AgentOps API 返回的治理快照。",
      generatedAt: snapshot.generated_at || "未返回",
      sourceType: repositoryBacked ? "事件仓库事实" : "API 快照",
      sourceSummary: repositoryBacked
        ? "基于本地事件仓库事实生成，不包含生产 IAM、数据库或多租户权限事实。"
        : "基于后端快照接口生成。",
      request_id: "req_console_snapshot_live",
      primary_action: repositoryBacked ? "重新生成快照" : "刷新快照"
    },
    routes: snapshot.routes,
    consoleData: consoleDataWithWorkbenchDefaults(snapshot.consoleData)
  };
};

export function apiBaseUrl() {
  const viteEnv = import.meta.env || {};
  return viteEnv.VITE_AGENTOPS_API_BASE || "http://127.0.0.1:8765";
}

export function validateSnapshot(snapshot) {
  if (!snapshot || snapshot.schema_version !== SNAPSHOT_SCHEMA_VERSION) {
    return false;
  }
  if (!routesAreComplete(snapshot.routes) || !snapshot.consoleData) {
    return false;
  }

  const consoleData = consoleDataWithWorkbenchDefaults(snapshot.consoleData);
  const requiredKeys = [
    "summary",
    "runs",
    "evidence",
    "approvals",
    "policies",
    "quality",
    "risks",
    "agentStore",
    "credentialHandoff",
    "operationCenter",
    "evidenceVault",
    "approvalWorkbench",
    "connectorWorkbench",
    "sdlcRunWorkbench",
    "qualityCenterWorkbench",
    "actionWorkbench",
    "connectors",
    "sdlcRuns"
  ];
  if (!requiredKeys.every((key) => Object.prototype.hasOwnProperty.call(consoleData, key))) {
    return false;
  }
  if (!snapshotShapeIsSafe(consoleData)) {
    return false;
  }
  if (!runtimeRunsAreSafe(consoleData)) {
    return false;
  }
  if (!actionDetailsAreComplete(consoleData)) {
    return false;
  }
  if (!evidenceVaultIsComplete(consoleData)) {
    return false;
  }
  if (!approvalWorkbenchIsComplete(consoleData)) {
    return false;
  }
  if (!connectorWorkbenchIsComplete(consoleData)) {
    return false;
  }
  if (!sdlcRunWorkbenchIsComplete(consoleData)) {
    return false;
  }
  if (!qualityCenterWorkbenchIsComplete(consoleData)) {
    return false;
  }
  if (!credentialHandoffIsSafe(consoleData)) {
    return false;
  }
  if (!adoptionInsightsAreComplete(consoleData)) {
    return false;
  }
  if (!qualitySignalsAreSafe(consoleData)) {
    return false;
  }
  if (containsForbiddenKey(snapshot, "raw_payload")) {
    return false;
  }
  if (containsForbiddenCredentialMaterial(snapshot)) {
    return false;
  }
  return statesAreKnown(consoleData) &&
    operationActionsResolve(consoleData) &&
    verifiedLoadedProofIsSafe(consoleData);
}

function consoleDataWithWorkbenchDefaults(consoleData) {
  if (!isRecord(consoleData)) {
    return consoleData;
  }
  const withAdoption = Object.prototype.hasOwnProperty.call(consoleData, "adoption")
    ? consoleData
    : {
      ...consoleData,
      adoption: emptyAdoptionInsights()
    };
  const withEvidenceVault = Object.prototype.hasOwnProperty.call(withAdoption, "evidenceVault")
    ? withAdoption
    : {
      ...withAdoption,
      evidenceVault: legacyEvidenceVault(withAdoption.evidence)
    };
  const withApprovalWorkbench = Object.prototype.hasOwnProperty.call(withEvidenceVault, "approvalWorkbench")
    ? withEvidenceVault
    : {
    ...withEvidenceVault,
    approvalWorkbench: legacyApprovalWorkbench(withEvidenceVault.approvals)
  };
  const withConnectorWorkbench = Object.prototype.hasOwnProperty.call(withApprovalWorkbench, "connectorWorkbench")
    ? withApprovalWorkbench
    : {
      ...withApprovalWorkbench,
      connectorWorkbench: legacyConnectorWorkbench(withApprovalWorkbench.connectors)
    };
  const withSdlcRunWorkbench = Object.prototype.hasOwnProperty.call(withConnectorWorkbench, "sdlcRunWorkbench")
    ? withConnectorWorkbench
    : {
      ...withConnectorWorkbench,
      sdlcRunWorkbench: legacySdlcRunWorkbench(withConnectorWorkbench)
    };
  const withQualityCenterWorkbench = Object.prototype.hasOwnProperty.call(withSdlcRunWorkbench, "qualityCenterWorkbench")
    ? withSdlcRunWorkbench
    : {
      ...withSdlcRunWorkbench,
      qualityCenterWorkbench: legacyQualityCenterWorkbench(withSdlcRunWorkbench)
    };
  return credentialHandoffDefaulted(withQualityCenterWorkbench);
}

function credentialHandoffDefaulted(consoleData) {
  if (Object.prototype.hasOwnProperty.call(consoleData, "credentialHandoff")) {
    return consoleData;
  }
  return {
    ...consoleData,
    credentialHandoff: emptyCredentialHandoff()
  };
}

function emptyCredentialHandoff() {
  return {
    summary: {
      id: "legacy_credential_handoff_summary",
      schema_version: "agentops_credential_status.v1",
      bootstrap_count: 0,
      credential_issued: 0,
      signature_verified: 0,
      agentops_fact_owner: "agentops",
      agent_store_boundary: "display_only_no_active_inference",
      verified_loaded: "not_asserted",
      l5_status: "not_asserted",
      primary_action: "等待凭证联调记录",
      safety_note: "旧版快照未提供凭证联调工作台，前端仅展示安全空态。"
    },
    sessions: [],
    guardrails: [
      "Agent Store 只能消费 AgentOps 回显字段，不得本地推导 active。",
      "signature_verified 只表示签名测试事件通过，不构成 verified_loaded 或 L5。",
      "控制台不展示 token 值、私钥、原始载荷、下载链接、PR 原文或外部 URL。"
    ]
  };
}

function emptyEvidenceVault() {
  return {
    requests: [],
    grants: [],
    auditTrail: [],
    guardrails: [
      "默认不展示原文，只展示脱敏摘要、哈希和审计引用。",
      "旧版 v1 快照未提供 Evidence Vault 访问工作台，前端仅展示安全空态。"
    ]
  };
}

function legacyEvidenceVault(evidenceItems) {
  const items = Array.isArray(evidenceItems) ? evidenceItems : [];
  if (!items.length) {
    return emptyEvidenceVault();
  }
  return {
    requests: items.map((item) => legacyVaultRequest(item)),
    grants: items.map((item) => legacyVaultGrant(item)),
    auditTrail: items.map((item) => legacyVaultAudit(item)),
    guardrails: [
      "默认不展示原文，只展示脱敏摘要、哈希和审计引用。",
      "旧版 v1 快照未提供 Evidence Vault 访问工作台，前端仅按 evidence 状态合成只读申请、授权和审计摘要。",
      "合成记录不提供原文下载，不自动批准、不自动写回。"
    ]
  };
}

function legacyVaultRequest(item) {
  const state = item.raw_access_state;
  return {
    id: `legacy_vault_req_${item.evidence_id}`,
    evidence_id: item.evidence_id,
    run_id: item.run_id,
    requester: "证据负责人",
    reason: legacyVaultReason(state),
    status: legacyVaultRequestStatus(state),
    denied_scope: item.denied_scope || "",
    audit_id: item.audit_id,
    ttl_summary: legacyVaultTtl(state),
    primary_action: legacyVaultPrimaryAction(state),
    safety_note: "仅记录原文访问申请摘要，不展示 Evidence Vault 原文。"
  };
}

function legacyVaultGrant(item) {
  const state = item.raw_access_state;
  return {
    id: `legacy_vault_grant_${item.evidence_id}`,
    evidence_id: item.evidence_id,
    requester: "证据负责人",
    status: legacyVaultGrantStatus(state),
    scope: state === "approved_limited" ? "限定复核字段" : item.denied_scope || legacyVaultPendingScope(state),
    expires_at: legacyVaultExpiresAt(state),
    audit_id: item.audit_id,
    consumption_policy: "只读复核窗口内可查看授权记录；不提供原文下载。"
  };
}

function legacyVaultAudit(item) {
  const state = item.raw_access_state;
  return {
    id: `legacy_vault_audit_${item.evidence_id}`,
    evidence_id: item.evidence_id,
    stage: legacyVaultStage(state),
    occurred_at: "旧版快照同步时",
    summary: legacyVaultAuditSummary(state),
    owner: "证据负责人",
    status: state,
    audit_id: item.audit_id
  };
}

function legacyVaultRequestStatus(state) {
  if (state === "summary_only" || state === "degraded") {
    return "pending";
  }
  if (["approved_limited", "redaction_failed", "permission_denied"].includes(state)) {
    return state;
  }
  return "pending";
}

function legacyVaultGrantStatus(state) {
  if (state === "approved_limited") {
    return "active";
  }
  if (state === "permission_denied") {
    return "rejected";
  }
  if (state === "redaction_failed") {
    return "redaction_failed";
  }
  return "pending";
}

function legacyVaultReason(state) {
  if (state === "approved_limited") {
    return "旧版快照显示限定授权，仅查看授权记录。";
  }
  if (state === "degraded") {
    return "旧版快照显示运行降级，需先补齐治理证据后再申请原文访问。";
  }
  if (state === "redaction_failed") {
    return "旧版快照显示脱敏失败，需要先修复脱敏或补充审批理由。";
  }
  if (state === "permission_denied") {
    return "旧版快照显示访问被拒绝，需要补充限定范围申请。";
  }
  return "旧版快照默认仅展示安全摘要，必要时发起原文访问申请。";
}

function legacyVaultTtl(state) {
  if (state === "approved_limited") {
    return "15 分钟限时窗口";
  }
  if (state === "degraded") {
    return "待补偿";
  }
  if (state === "permission_denied") {
    return "未授权";
  }
  if (state === "redaction_failed") {
    return "脱敏失败，暂停授权";
  }
  return "待审批";
}

function legacyVaultPrimaryAction(state) {
  if (state === "approved_limited") {
    return "查看授权记录";
  }
  if (state === "degraded") {
    return "等待审批";
  }
  if (state === "permission_denied") {
    return "补充申请理由";
  }
  if (state === "redaction_failed") {
    return "仅查看哈希告警";
  }
  return "申请原文访问";
}

function legacyVaultPendingScope(state) {
  return state === "degraded" ? "待补偿范围" : "待审批范围";
}

function legacyVaultExpiresAt(state) {
  if (state === "approved_limited") {
    return "快照生成后 15 分钟";
  }
  if (state === "degraded") {
    return "待补偿";
  }
  if (state === "permission_denied") {
    return "未授权";
  }
  if (state === "redaction_failed") {
    return "暂停授权";
  }
  return "待审批";
}

function legacyVaultStage(state) {
  if (state === "approved_limited") {
    return "授权";
  }
  if (state === "degraded") {
    return "降级";
  }
  if (state === "permission_denied") {
    return "拒绝";
  }
  if (state === "redaction_failed") {
    return "脱敏失败";
  }
  return "申请";
}

function legacyVaultAuditSummary(state) {
  if (state === "redaction_failed") {
    return "旧版快照显示脱敏失败，审计仅保留哈希和告警。";
  }
  if (state === "degraded") {
    return "旧版快照显示运行降级，原文访问保持待审批。";
  }
  if (state === "permission_denied") {
    return "旧版快照显示访问被拒绝，需补充限定范围申请理由。";
  }
  if (state === "approved_limited") {
    return "旧版快照显示限定范围授权，原文仍不在控制台展示。";
  }
  return "旧版快照显示原文访问尚未批准，继续展示安全摘要。";
}

function legacyApprovalWorkbench(approvalItems) {
  const items = Array.isArray(approvalItems) ? approvalItems : [];
  return {
    queues: items.map((item) => legacyApprovalQueue(item)),
    grants: items.map((item) => legacyApprovalGrant(item)),
    auditTrail: items.map((item) => legacyApprovalAudit(item)),
    guardrails: [
      "审批队列只展示人工处置摘要，不在本页执行批准、拒绝或撤销。",
      "Grant 必须绑定原始审批编号、策略版本、资源范围、授权时限和审计编号。",
      "申请人不得作为唯一审批人批准自己的高风险动作，除非存在 break_glass 审计。",
      "补充材料只展示摘要和审计引用，不展示原文、PR 正文或下载链接。"
    ]
  };
}

function legacyApprovalQueue(item) {
  return {
    id: `legacy_approval_queue_${item.approval_id}`,
    approval_id: item.approval_id,
    requester: item.requester,
    reason: item.reason,
    affected_actions: item.affected_actions,
    status: item.status,
    sla_due_at: item.sla_due_at,
    sla_state: legacyApprovalSlaState(item.status),
    approver_scope: "安全/IAM 审批人",
    supplemental_materials: "待补充：变更说明、影响范围、回滚预案",
    primary_action: legacyApprovalPrimaryAction(item.status),
    secondary_action: legacyApprovalSecondaryAction(item.status),
    audit_id: item.audit_id,
    denied_scope: ["rejected", "revoked", "permission_denied"].includes(item.status) ? item.affected_actions || "approval.scope" : "",
    safety_note: "只读展示审批处置摘要，不执行批准、拒绝、撤销或生产写操作。"
  };
}

function legacyApprovalGrant(item) {
  const grantStatus = legacyApprovalGrantStatus(item.status, item.grant_status);
  return {
    id: `legacy_approval_grant_${item.approval_id}`,
    approval_id: item.approval_id,
    grant_status: grantStatus,
    policy_version: item.policy_version || "runtime-v2.3",
    resource_scope: item.resource_scope || item.affected_actions || "待确认范围",
    ttl_summary: legacyApprovalGrantTtl(grantStatus),
    expires_at: legacyApprovalGrantExpiresAt(grantStatus),
    revocation_state: legacyApprovalRevocationState(grantStatus),
    audit_id: item.audit_id,
    consumption_policy: "Grant 仅可由绑定审批、策略版本和资源范围消费；本页不执行生产写操作。"
  };
}

function legacyApprovalGrantStatus(approvalStatus, grantStatus) {
  if (approvalStatus === "approved") {
    return ["active", "expired"].includes(grantStatus) ? grantStatus : "active";
  }
  if (approvalStatus === "revoked") {
    return "revoked";
  }
  if (approvalStatus === "rejected") {
    return "rejected";
  }
  if (approvalStatus === "expired") {
    return "expired";
  }
  if (approvalStatus === "escalated") {
    return grantStatus === "expired" ? "expired" : "pending";
  }
  if (["pending", "needs_more_info"].includes(approvalStatus)) {
    return "pending";
  }
  return grantStatus === "active" ? "pending" : grantStatus;
}

function legacyApprovalAudit(item) {
  return {
    id: `legacy_approval_audit_${item.approval_id}`,
    approval_id: item.approval_id,
    stage: legacyApprovalAuditStage(item.status),
    occurred_at: "旧版快照同步时",
    summary: `${item.requester} 申请 ${item.affected_actions}：${item.reason}。`,
    owner: "安全/IAM 审批人",
    status: item.status,
    audit_id: item.audit_id
  };
}

function legacyApprovalSlaState(status) {
  if (status === "pending") {
    return "待处理";
  }
  if (status === "escalated") {
    return "已升级";
  }
  if (status === "approved") {
    return "已完成";
  }
  if (status === "revoked") {
    return "已撤销";
  }
  if (status === "rejected") {
    return "已拒绝";
  }
  if (status === "expired") {
    return "已过期";
  }
  if (status === "needs_more_info") {
    return "待补充材料";
  }
  return "需复核";
}

function legacyApprovalPrimaryAction(status) {
  if (status === "approved") {
    return "查看审批记录";
  }
  if (status === "revoked") {
    return "查看撤销原因";
  }
  if (status === "escalated") {
    return "升级审批";
  }
  if (status === "rejected") {
    return "查看拒绝原因";
  }
  if (status === "needs_more_info") {
    return "补充材料";
  }
  return "处理审批";
}

function legacyApprovalSecondaryAction(status) {
  if (status === "approved") {
    return "查看 Grant 状态";
  }
  if (status === "revoked") {
    return "通知申请方";
  }
  if (status === "escalated") {
    return "转交安全/IAM 审批人";
  }
  return "补充材料或转交审批";
}

function legacyApprovalGrantTtl(status) {
  if (status === "active") {
    return "15 分钟限时 Grant";
  }
  if (status === "expired") {
    return "Grant 已过期";
  }
  if (status === "revoked") {
    return "Grant 已撤销";
  }
  if (status === "rejected") {
    return "未签发 Grant";
  }
  return "待审批后签发";
}

function legacyApprovalGrantExpiresAt(status) {
  if (status === "active") {
    return "快照生成后 15 分钟";
  }
  if (status === "expired") {
    return "已过期";
  }
  if (status === "revoked") {
    return "已撤销";
  }
  if (status === "rejected") {
    return "未授权";
  }
  return "待审批";
}

function legacyApprovalRevocationState(status) {
  if (status === "revoked") {
    return "已撤销，后续 Policy Check 不得 conditional_allow";
  }
  if (status === "expired") {
    return "已过期，需重新审批";
  }
  if (status === "active") {
    return "未撤销，仍需按资源范围和授权时限消费";
  }
  return "未签发";
}

function legacyApprovalAuditStage(status) {
  if (status === "approved") {
    return "批准";
  }
  if (status === "revoked") {
    return "撤销";
  }
  if (status === "escalated") {
    return "升级";
  }
  if (status === "rejected") {
    return "拒绝";
  }
  if (status === "expired") {
    return "过期";
  }
  if (status === "needs_more_info") {
    return "补充材料";
  }
  return "申请";
}

function legacyConnectorWorkbench(connectorItems) {
  const items = Array.isArray(connectorItems) ? connectorItems : [];
  return {
    health: items.map((item) => legacyConnectorHealth(item)),
    dlq: items.map((item) => legacyConnectorDlq(item)),
    syncTrail: items.map((item) => legacyConnectorSyncTrail(item)),
    guardrails: [
      "连接器新鲜度 SLO 为 15 分钟内，超过 20 分钟必须告警并降低证据等级。",
      "DLQ 与 Outbox Replay 只展示只读摘要，本页不执行回放、重试或生产写操作。",
      "Git、PR、CI、测试、IAM 等外部连接器必须展示限流状态、降级动作和负责人。",
      "materialized/unverified 只能说明配置已生成或 CLI 预演成功，不构成 verified_loaded 治理激活证明。",
      "连接器工作台不得展示原始载荷、下载链接、PR 原文或外部 URL。"
    ]
  };
}

function legacyConnectorHealth(item) {
  return {
    id: `legacy_connector_health_${item.id}`,
    connector_id: item.id,
    name: item.name,
    status: item.status,
    last_seen_at: item.last_seen_at,
    freshness: legacyConnectorFreshness(item.status),
    freshness_state: legacyConnectorFreshnessState(item.status),
    rate_limit_state: legacyConnectorRateLimitState(item.id, item.status),
    rate_limit_detail: legacyConnectorRateLimitDetail(item.id, item.status),
    degrade_action: item.degrade_action,
    evidence_impact: legacyConnectorEvidenceImpact(item),
    owner: legacyConnectorOwner(item.id),
    request_id: item.request_id,
    primary_action: legacyConnectorPrimaryAction(item),
    secondary_action: legacyConnectorSecondaryAction(item),
    safety_note: "只读健康摘要，不执行连接器重试、回放、写回或权限变更。"
  };
}

function legacyConnectorDlq(item) {
  return {
    id: `legacy_connector_dlq_${item.id}`,
    connector_id: item.id,
    dlq_depth: legacyConnectorDlqDepth(item.status),
    oldest_event_age: legacyConnectorOldestEventAge(item.status),
    replay_state: legacyConnectorReplayState(item.status),
    retry_window: legacyConnectorRetryWindow(item.status),
    degrade_policy: legacyConnectorDlqPolicy(item),
    request_id: item.request_id,
    audit_id: `audit_${item.id}`,
    safety_note: "Outbox Replay 需要人工审批后在后端执行，本页只展示队列摘要。"
  };
}

function legacyConnectorSyncTrail(item) {
  return {
    id: `legacy_connector_sync_${item.id}`,
    connector_id: item.id,
    stage: legacyConnectorSyncStage(item.status),
    occurred_at: item.last_seen_at,
    summary: legacyConnectorSyncSummary(item),
    owner: legacyConnectorOwner(item.id),
    status: item.status,
    request_id: item.request_id
  };
}

function legacyConnectorOwner(connectorId) {
  const owners = {
    conn_agent_store: "Agent Store 负责人",
    conn_ingestion: "事件接入负责人",
    conn_repository: "运行事实仓库负责人",
    conn_git: "Git 仓库负责人",
    conn_pr: "PR 服务负责人",
    conn_ci: "CI 负责人",
    conn_test: "测试负责人",
    conn_sdlc: "SDLC 负责人",
    conn_evidence: "证据负责人",
    conn_policy: "策略服务负责人",
    conn_iam: "安全/IAM 负责人"
  };
  return owners[connectorId] || "连接器负责人";
}

function legacyConnectorFreshness(status) {
  if (status === "healthy") {
    return "15 分钟内";
  }
  if (status === "materialized") {
    return "配置已生成，待 verified_loaded 证明";
  }
  if (status === "degraded") {
    return "超过 20 分钟或降级";
  }
  return "待采集";
}

function legacyConnectorFreshnessState(status) {
  if (status === "healthy") {
    return "healthy";
  }
  if (status === "materialized") {
    return "materialized";
  }
  if (status === "degraded") {
    return "degraded";
  }
  return "unknown";
}

function legacyConnectorRateLimitState(connectorId, status) {
  if (status === "degraded") {
    return "degraded";
  }
  if (["conn_sdlc", "conn_policy", "conn_evidence"].includes(connectorId)) {
    return "warning";
  }
  return "healthy";
}

function legacyConnectorRateLimitDetail(connectorId, status) {
  if (status === "degraded") {
    return "限流或不可用已影响同步，降低证据等级并进入人工复核。";
  }
  if (connectorId === "conn_sdlc") {
    return "治理证明未完成，仅低频探测，不提升为 verified_loaded。";
  }
  if (["conn_policy", "conn_evidence", "conn_ci"].includes(connectorId)) {
    return "接近配额或依赖外部检查，按低频采集并保留摘要。";
  }
  return "未触发限流，按连接器新鲜度 SLO 采集。";
}

function legacyConnectorEvidenceImpact(item) {
  if (item.status === "healthy") {
    return "证据等级不降低";
  }
  if (item.status === "materialized") {
    return "仅证明配置已生成，不构成 verified_loaded 治理激活证明";
  }
  return "降低证据等级，相关运行进入人工复核";
}

function legacyConnectorPrimaryAction(item) {
  if (item.status === "healthy") {
    return "保持监控";
  }
  if (item.status === "degraded") {
    return "查看降级影响";
  }
  if (item.status === "materialized") {
    return "补齐治理加载证明";
  }
  return "查看降级影响";
}

function legacyConnectorSecondaryAction(item) {
  if (item.status === "healthy") {
    return "按 SLO 继续采集心跳";
  }
  if (item.status === "materialized") {
    return "等待 verified_loaded 机器证据";
  }
  return "转交负责人并降低相关证据等级";
}

function legacyConnectorDlqDepth(status) {
  if (status === "healthy") {
    return "0";
  }
  if (status === "materialized") {
    return "待验证";
  }
  return "3";
}

function legacyConnectorOldestEventAge(status) {
  if (status === "healthy") {
    return "0 分钟";
  }
  if (status === "materialized") {
    return "待采集";
  }
  return "22 分钟";
}

function legacyConnectorReplayState(status) {
  if (status === "healthy") {
    return "healthy";
  }
  if (status === "materialized") {
    return "materialized";
  }
  return "pending";
}

function legacyConnectorRetryWindow(status) {
  if (status === "healthy") {
    return "无需回放";
  }
  if (status === "materialized") {
    return "待 verified_loaded 后确认";
  }
  return "人工审批后 15 分钟内回放";
}

function legacyConnectorDlqPolicy(item) {
  if (item.status === "healthy") {
    return "无积压，继续按 15 分钟新鲜度 SLO 采集";
  }
  if (item.status === "materialized") {
    return "未形成治理激活证明前，不提升证据等级";
  }
  return `执行降级：${item.degrade_action}；Outbox Replay 需人工审批`;
}

function legacyConnectorSyncStage(status) {
  if (status === "healthy") {
    return "同步";
  }
  if (status === "materialized") {
    return "待证明";
  }
  return "降级";
}

function legacyConnectorSyncSummary(item) {
  if (item.status === "healthy") {
    return `${item.name} 心跳正常，继续按新鲜度 SLO 采集。`;
  }
  if (item.status === "materialized") {
    return `${item.name} 已生成配置，但仍缺 verified_loaded 机器证明。`;
  }
  return `${item.name} 进入降级路径：${item.degrade_action}。`;
}

function legacySdlcRunWorkbench(consoleData) {
  const runs = Array.isArray(consoleData.sdlcRuns) ? consoleData.sdlcRuns : [];
  const verifiedCount = runs.filter((item) => sdlcProofVerified(item)).length;
  return {
    summary: {
      id: "legacy_sdlc_run_summary",
      adapter_status: consoleData.summary?.adapter?.status || "materialized",
      proof_state: runs.length > 0 && verifiedCount === runs.length ? "verified_loaded" : "unverified",
      dry_run_state: sdlcDryRunState(runs),
      reporter_ready: verifiedCount,
      pending_proofs: Math.max(runs.length - verifiedCount, 0),
      primary_action: verifiedCount === runs.length && runs.length ? "保持治理加载证明" : "补齐 verified_loaded 机器证明",
      safety_note: "CLI dry-run、AGENTS.md 或本地仓库事实不构成 verified_loaded 治理激活证明。"
    },
    reporter: runs.map((item) => legacySdlcReporterItem(item)),
    outbox: runs.map((item) => legacySdlcOutboxItem(item)),
    eligibility: runs.map((item) => legacySdlcEligibilityItem(item)),
    guardrails: [
      "Reporter active 必须有 machine-verifiable proof，不得由 dry-run 或 AGENTS.md 推导。",
      "Outbox delivered 只表示投递状态，不在 Console 执行 Outbox Replay 或事件重放。",
      "materialized/unverified 只能说明配置已生成或 CLI 预演成功，不构成 verified_loaded 治理激活证明。",
      "L5 条件缺失必须展示 failed_conditions 和下一步动作，不得显示为 healthy。",
      "Ai_AutoSDLC 运行工作台不得展示原始载荷、下载链接、PR 原文、diff、patch 或外部 URL。"
    ]
  };
}

function sdlcProofVerified(item) {
  const proofText = `${item.proof_source || ""} ${item.captured_at || ""}`;
  const proofPending = /待采集|待接入|CLI 预演|AGENTS\.md/.test(proofText);
  return item.verified_loaded === "verified_loaded" &&
    Boolean(item.proof_source) &&
    Boolean(item.captured_at) &&
    !proofPending;
}

function sdlcRunRef(item) {
  return item.run_id || item.id || "unknown_sdlc_run";
}

function sdlcDryRunState(items) {
  if (!items.length) {
    return "empty";
  }
  return items.every((item) => item.dry_run_status === "dry_run_passed") ? "dry_run_passed" : "pending";
}

function legacySdlcReporterItem(item) {
  const verified = sdlcProofVerified(item);
  const runId = sdlcRunRef(item);
  return {
    id: `legacy_sdlc_reporter_${runId}`,
    run_id: runId,
    command: item.command,
    reporter_status: verified ? "active" : "materialized",
    integration_mode: "enterprise_managed",
    credential_status: verified ? "active" : "unverified",
    source_signed: verified ? "active" : "unverified",
    identity_confidence: verified ? "verified_loaded" : "unverified",
    governance_state: item.adapter_status || "materialized",
    proof_source: item.proof_source,
    primary_action: verified ? "保持 Reporter 心跳" : "补齐治理加载证明",
    safety_note: "只读 Reporter 摘要，不签发凭证、不绑定设备、不执行企业激活。"
  };
}

function legacySdlcOutboxItem(item) {
  const verified = sdlcProofVerified(item);
  const runId = sdlcRunRef(item);
  return {
    id: `legacy_sdlc_outbox_${runId}`,
    run_id: runId,
    outbox_status: verified ? "healthy" : "pending",
    sequence_state: verified ? "healthy" : "pending",
    pending_events: verified ? "0" : "待验证",
    oldest_pending_age: verified ? "0 分钟" : "待采集",
    replay_boundary: "只读摘要，不在 Console 执行 Outbox Replay 或事件重放。",
    evidence_impact: verified ? "可进入 L5 复核" : "pending L5 verification，不提升证据等级。",
    audit_id: `audit_sdlc_${runId}`,
    safety_note: "Outbox Replay 必须由后端审批流程执行，本页不提供重放按钮。"
  };
}

function legacySdlcEligibilityItem(item) {
  const verified = sdlcProofVerified(item);
  const runId = sdlcRunRef(item);
  return {
    id: `legacy_sdlc_eligibility_${runId}`,
    run_id: runId,
    evidence_level: verified ? "L5" : "pending",
    l5_result: verified ? "healthy" : "pending",
    failed_conditions: verified ? "无" : "governance_loaded,source_signed,outbox_delivered",
    policy_state_known: verified ? "allow" : "unknown",
    governance_loaded: verified ? "verified_loaded" : "unverified",
    verification_fresh: verified ? "healthy" : "pending",
    outbox_delivered: verified ? "healthy" : "pending",
    next_action: verified ? "保持证据链" : "补齐 verified_loaded、签名来源和 Outbox delivered 证明",
    safety_note: "Eligibility 仅解释 L5 条件，不覆盖 AgentOps 后端最终等级判定。"
  };
}

function legacyQualityCenterWorkbench(consoleData) {
  const quality = Array.isArray(consoleData.quality) ? consoleData.quality : [];
  const adoption = consoleData.adoption || emptyAdoptionInsights();
  const agentSummaries = quality.map((item, index) => legacyQualityAgentSummary(item, index));
  const reviewQueue = legacyQualityReviewQueue(agentSummaries, adoption);
  const comparisonStates = agentSummaries.map((item) => item.scorer_comparison.comparison_state);
  return {
    schema_version: "quality_center_workbench.v1",
    report_period: "legacy_console_snapshot",
    workbench_state: agentSummaries.length ? "ready" : "empty",
    generated_by: "agentops_console_legacy_fallback",
    agent_summaries: agentSummaries,
    scorer_rollout_panel: {
      candidate_count: agentSummaries.length,
      ready_for_manual_approval_count: comparisonStates.filter((state) => state === "ready_for_manual_approval").length,
      needs_human_review_count: comparisonStates.filter((state) => state === "needs_human_review").length,
      insufficient_evidence_count: comparisonStates.filter((state) => state === "insufficient_evidence").length,
      automatic_rollout_enabled: false,
      automatic_template_switch: false,
      manual_approval_queue_size: reviewQueue.filter((item) => item.review_type === "scorer_rollout").length
    },
    external_intake_panel: legacyExternalIntakePanel(agentSummaries, reviewQueue),
    external_intake_portfolio: legacyExternalIntakePortfolio(agentSummaries, reviewQueue),
    review_queue: reviewQueue,
    trend_summary: {
      report_state: adoption.metrics ? "ready" : "insufficient_data",
      retention_rate: adoption.metrics?.retention_rate || "0%",
      review_queue_size: reviewQueue.length,
      rework_rounds: adoption.metrics?.rework_rounds || 0,
      pr_review_findings: adoption.metrics?.pr_review_findings || 0,
      recommendation: "人工复核缺证据、低置信和评分器发布项；不执行自动生命周期动作。"
    },
    summary: {
      payload_access: "forbidden",
      prompt_access: "forbidden",
      change_access: "forbidden",
      terminal_access: "forbidden",
      automatic_rollout_enabled: false,
      automatic_lifecycle_action: false,
      store_write_performed: false,
      automatic_publish_performed: false,
      notification_sent: false,
      external_intake_receipt_count: 0
    },
    audit_id: "audit_quality_center_legacy_fallback"
  };
}

function legacyQualityAgentSummary(item, index) {
  const status = item.status || "unknown";
  const comparisonState = legacyQualityComparisonState(status);
  const qualityState = legacyQualityState(status);
  return {
    agent_id: safeDisplayText(item.category || item.signal_id || `quality_${index}`),
    version: "console_snapshot",
    owner_team: safeDisplayText(item.owner_hint || "质量负责人"),
    score: legacyQualityScore(item.score),
    quality_state: qualityState,
    confidence: legacyQualityConfidence(status),
    score_template_id: "quality_summary_console_snapshot",
    evidence_level: safeDisplayText(item.score || "summary_only"),
    missing_evidence: legacyQualityMissingEvidence(item),
    explanation: safeDisplayText(item.primary_action || "仅展示 Console 摘要，必要时进入人工复核。"),
    lifecycle_state: legacyLifecycleState(qualityState),
    lifecycle_action: legacyLifecycleAction(qualityState),
    scorer: {
      scorer_id: "quality_summary_console_snapshot",
      scorer_version: "summary",
      rollout_state: "candidate"
    },
    scorer_comparison: {
      comparison_state: comparisonState,
      safety_impact: comparisonState === "ready_for_manual_approval" ? "neutral" : "needs_review",
      alignment_delta: 0,
      recommendation: comparisonState === "ready_for_manual_approval"
        ? "submit_for_manual_rollout_approval"
        : "collect_more_samples",
      manual_approval_required: true
    },
    external_intake_health: legacyExternalIntakeHealth()
  };
}

function legacyExternalIntakeHealth() {
  return {
    schema_version: "quality_center_external_intake_health.v1",
    health_state: "no_receipts",
    receipt_count: 0,
    window_limit: 25,
    latest_intake_id: "",
    latest_received_at: "",
    latest_pass_rate: 0,
    latest_sample_size: 0,
    intake_state_counts: {},
    source_trust_counts: {},
    accepted_execution_count: 0,
    scorer_refs: [],
    manual_review_required: false,
    recommendation: "optional",
    summary: {
      summary_only_intake_health: true,
      latest_summary_keys: [],
      automatic_rollout_enabled: false,
      automatic_template_switch: false,
      scorer_execution_performed: false,
      store_write_performed: false,
      notification_sent: false
    }
  };
}

function legacyExternalIntakePanel(agentSummaries, reviewQueue) {
  const healthItems = agentSummaries.map((item) => item.external_intake_health);
  return {
    monitored_agent_count: healthItems.length,
    receiving_count: healthItems.filter((item) => item.health_state === "receiving").length,
    no_receipts_count: healthItems.filter((item) => item.health_state === "no_receipts").length,
    needs_review_count: healthItems.filter((item) => item.health_state === "needs_review").length,
    receipt_count: healthItems.reduce((sum, item) => sum + Number(item.receipt_count || 0), 0),
    accepted_execution_count: healthItems.reduce((sum, item) => sum + Number(item.accepted_execution_count || 0), 0),
    manual_review_queue_size: reviewQueue.filter((item) => item.review_type === "external_intake").length,
    automatic_rollout_enabled: false,
    automatic_scorer_invocation: false,
    store_write_performed: false
  };
}

function legacyExternalIntakePortfolio(agentSummaries, reviewQueue) {
  const panel = legacyExternalIntakePanel(agentSummaries, reviewQueue);
  return {
    schema_version: "quality_center_external_intake_portfolio.v1",
    portfolio_state: agentSummaries.length ? "no_receipts" : "empty",
    scope_count: agentSummaries.length,
    version_scope_count: new Set(agentSummaries.map((item) => `${item.agent_id}@${item.version}`)).size,
    state_counts: {
      receiving: panel.receiving_count,
      no_receipts: panel.no_receipts_count,
      needs_review: panel.needs_review_count
    },
    receipt_count: panel.receipt_count,
    accepted_execution_count: panel.accepted_execution_count,
    manual_review_queue_size: panel.manual_review_queue_size,
    required_missing_scope_count: 0,
    required_missing_scopes: [],
    latest_receipts: [],
    scorer_coverage: {
      unique_scorer_count: 0,
      scopes_with_scorer_receipts: 0,
      scorer_refs: []
    },
    summary: {
      summary_only_intake_portfolio: true,
      automatic_rollout_enabled: false,
      automatic_template_switch: false,
      automatic_scorer_invocation: false,
      scorer_execution_performed: false,
      store_write_performed: false,
      notification_sent: false
    }
  };
}

function legacyQualityReviewQueue(agentSummaries, adoption) {
  const items = [];
  for (const summary of agentSummaries) {
    if (summary.quality_state !== "healthy") {
      items.push(legacyQualityReviewItem(summary, "quality_evidence", "missing_or_low_confidence_evidence", "collect_more_evidence"));
    }
    items.push(legacyQualityReviewItem(
      summary,
      "scorer_rollout",
      summary.scorer_comparison.comparison_state,
      summary.scorer_comparison.recommendation
    ));
    if (summary.lifecycle_state !== "healthy") {
      items.push(legacyQualityReviewItem(summary, "lifecycle", summary.lifecycle_state, summary.lifecycle_action));
    }
  }
  for (const signal of adoption.reviewSignals || []) {
    items.push({
      id: `legacy_quality_adoption_${safeId(signal.id || signal.title || "review")}`,
      agent_id: safeDisplayText(signal.title || "adoption"),
      version: "console_snapshot",
      review_type: "quality_evidence",
      reason: safeDisplayText(signal.reason || "review"),
      recommended_action: "open_ops_review",
      owner_team: safeDisplayText(signal.owner || "质量负责人"),
      manual_review_required: true,
      automatic_action_performed: false
    });
  }
  return items;
}

function legacyQualityReviewItem(summary, reviewType, reason, recommendedAction) {
  return {
    id: `legacy_quality_${safeId(reviewType)}_${safeId(summary.agent_id)}_${safeId(reason)}`,
    agent_id: summary.agent_id,
    version: summary.version,
    review_type: reviewType,
    reason: safeDisplayText(reason),
    recommended_action: safeDisplayText(recommendedAction),
    owner_team: summary.owner_team,
    manual_review_required: true,
    automatic_action_performed: false
  };
}

function legacyQualityState(status) {
  if (["healthy", "normal", "ok", "succeeded"].includes(status)) {
    return "healthy";
  }
  if (["degraded", "warning", "warn", "pending"].includes(status)) {
    return "watching";
  }
  if (["redaction_failed", "permission_denied", "failed", "blocked"].includes(status)) {
    return "needs_review";
  }
  if (["block", "critical"].includes(status)) {
    return "critical";
  }
  return "insufficient_evidence";
}

function legacyLifecycleState(qualityState) {
  if (qualityState === "healthy") {
    return "healthy";
  }
  if (qualityState === "watching") {
    return "watching";
  }
  if (qualityState === "critical") {
    return "disable_review_recommended";
  }
  return "review_required";
}

function legacyLifecycleAction(qualityState) {
  if (qualityState === "healthy") {
    return "none";
  }
  if (qualityState === "watching") {
    return "watch";
  }
  if (qualityState === "critical") {
    return "open_disable_review";
  }
  return "open_ops_review";
}

function legacyQualityComparisonState(status) {
  if (["healthy", "normal", "ok", "succeeded"].includes(status)) {
    return "ready_for_manual_approval";
  }
  if (["redaction_failed", "permission_denied", "failed", "blocked", "block"].includes(status)) {
    return "needs_human_review";
  }
  return "insufficient_evidence";
}

function legacyQualityConfidence(status) {
  if (["healthy", "normal", "ok", "succeeded"].includes(status)) {
    return 0.86;
  }
  if (["degraded", "warning", "warn", "pending"].includes(status)) {
    return 0.62;
  }
  return 0.38;
}

function legacyQualityScore(score) {
  const value = Number(String(score || "").replace(/[^\d.]+/g, ""));
  return Number.isFinite(value) ? Math.min(value, 100) : 0;
}

function legacyQualityMissingEvidence(item) {
  if (["healthy", "normal", "ok", "succeeded"].includes(item.status)) {
    return [];
  }
  return [safeDisplayText(item.evidence_ref || "quality_summary")];
}

function safeDisplayText(value) {
  const text = String(value || "");
  return /https?:\/\//i.test(text) || /secret|token/i.test(text) ? "[redacted]" : text;
}

function safeId(value) {
  return String(value || "unknown").replace(/[^a-zA-Z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "unknown";
}

function emptyAdoptionInsights() {
  return {
    metrics: {
      generated_lines: 0,
      retained_lines: 0,
      human_modified_lines: 0,
      deleted_lines: 0,
      rework_rounds: 0,
      pr_review_findings: 0,
      ci_failure_types: ["旧版快照未提供失败归因"],
      retention_rate: "0%"
    },
    explanationChains: [],
    segments: [{
      id: "segment_sdlc_runs",
      title: "Ai_AutoSDLC 标准路径",
      status: "empty",
      retention_rate: "0%",
      affected_agents: "0",
      owner: "SDLC 负责人",
      next_review: "等待新版快照同步后复核"
    }],
    reviewSignals: [],
    guardrails: [
      "低置信不自动下架，只进入人工复核和申诉路径。",
      "旧版 v1 快照未提供采纳指标，前端仅展示安全空态。"
    ]
  };
}

function consoleDataHasEvidenceVaultShape(consoleData) {
  if (!isRecord(consoleData.evidenceVault)) {
    return false;
  }
  return Array.isArray(consoleData.evidenceVault.requests) &&
    Array.isArray(consoleData.evidenceVault.grants) &&
    Array.isArray(consoleData.evidenceVault.auditTrail) &&
    Array.isArray(consoleData.evidenceVault.guardrails);
}

function consoleDataHasAdoptionShape(consoleData) {
  if (!isRecord(consoleData.adoption)) {
    return false;
  }
  return isRecord(consoleData.adoption.metrics) &&
    Array.isArray(consoleData.adoption.explanationChains) &&
    Array.isArray(consoleData.adoption.segments) &&
    Array.isArray(consoleData.adoption.reviewSignals) &&
    Array.isArray(consoleData.adoption.guardrails);
}

function consoleDataHasConnectorWorkbenchShape(consoleData) {
  if (!isRecord(consoleData.connectorWorkbench)) {
    return false;
  }
  return Array.isArray(consoleData.connectorWorkbench.health) &&
    Array.isArray(consoleData.connectorWorkbench.dlq) &&
    Array.isArray(consoleData.connectorWorkbench.syncTrail) &&
    Array.isArray(consoleData.connectorWorkbench.guardrails);
}

function consoleDataHasSdlcRunWorkbenchShape(consoleData) {
  if (!isRecord(consoleData.sdlcRunWorkbench)) {
    return false;
  }
  return isRecord(consoleData.sdlcRunWorkbench.summary) &&
    Array.isArray(consoleData.sdlcRunWorkbench.reporter) &&
    Array.isArray(consoleData.sdlcRunWorkbench.outbox) &&
    Array.isArray(consoleData.sdlcRunWorkbench.eligibility) &&
    Array.isArray(consoleData.sdlcRunWorkbench.guardrails);
}

function consoleDataHasQualityCenterWorkbenchShape(consoleData) {
  if (!isRecord(consoleData.qualityCenterWorkbench)) {
    return false;
  }
  const workbench = consoleData.qualityCenterWorkbench;
  return Array.isArray(workbench.agent_summaries) &&
    isRecord(workbench.scorer_rollout_panel) &&
    isRecord(workbench.external_intake_panel) &&
    isRecord(workbench.external_intake_portfolio) &&
    Array.isArray(workbench.review_queue) &&
    isRecord(workbench.trend_summary) &&
    isRecord(workbench.summary) &&
    typeof workbench.audit_id === "string";
}

export function snapshotShapeIsSafe(consoleData) {
  if (!isRecord(consoleData.summary) || !isRecord(consoleData.summary.adapter)) {
    return false;
  }
  if (!Array.isArray(consoleData.summary.metrics)) {
    return false;
  }

  const requiredCollections = [
    "runs",
    "evidence",
    "approvals",
    "policies",
    "quality",
    "risks",
    "agentStore",
    "credentialHandoff",
    "operationCenter",
    "approvalWorkbench",
    "connectorWorkbench",
    "sdlcRunWorkbench",
    "qualityCenterWorkbench",
    "actionWorkbench",
    "connectors",
    "sdlcRuns"
  ];
  return requiredCollections.every((key) => {
    if (key === "agentStore") {
      return isRecord(consoleData.agentStore) &&
        Array.isArray(consoleData.agentStore.discoveryGaps) &&
        Array.isArray(consoleData.agentStore.runAudits) &&
        Array.isArray(consoleData.agentStore.storeSummaries) &&
        Array.isArray(consoleData.agentStore.registryMap);
    }
    if (key === "credentialHandoff") {
      return consoleDataHasCredentialHandoffShape(consoleData);
    }
    if (key === "operationCenter") {
      return isRecord(consoleData.operationCenter) &&
        Array.isArray(consoleData.operationCenter.notifications) &&
        Array.isArray(consoleData.operationCenter.todos) &&
        Array.isArray(consoleData.operationCenter.searchIndex);
    }
    if (key === "actionWorkbench") {
      return isRecord(consoleData.actionWorkbench) &&
        Array.isArray(consoleData.actionWorkbench.details);
    }
    if (key === "approvalWorkbench") {
      return isRecord(consoleData.approvalWorkbench) &&
        Array.isArray(consoleData.approvalWorkbench.queues) &&
        Array.isArray(consoleData.approvalWorkbench.grants) &&
        Array.isArray(consoleData.approvalWorkbench.auditTrail) &&
        Array.isArray(consoleData.approvalWorkbench.guardrails);
    }
    if (key === "connectorWorkbench") {
      return consoleDataHasConnectorWorkbenchShape(consoleData);
    }
    if (key === "sdlcRunWorkbench") {
      return consoleDataHasSdlcRunWorkbenchShape(consoleData);
    }
    if (key === "qualityCenterWorkbench") {
      return consoleDataHasQualityCenterWorkbenchShape(consoleData);
    }
    return Array.isArray(consoleData[key]);
  }) &&
    consoleDataHasAdoptionShape(consoleData) &&
    consoleDataHasEvidenceVaultShape(consoleData) &&
    consoleDataHasConnectorWorkbenchShape(consoleData) &&
    consoleDataHasSdlcRunWorkbenchShape(consoleData) &&
    consoleDataHasQualityCenterWorkbenchShape(consoleData) &&
    consoleDataHasCredentialHandoffShape(consoleData);
}

function runtimeRunsAreSafe(consoleData) {
  const runtimeStatuses = new Set([
    "created",
    "succeeded",
    "failed",
    "cancelled",
    "timeout",
    "blocked",
    "approval_paused",
    "running",
    "trace_pending",
    "degraded"
  ]);
  return (consoleData.runs || []).every((run) => {
    if (!isRecord(run) || containsUnsafeAuditReference(run)) {
      return false;
    }
    if (run.runtime_status && !runtimeStatuses.has(run.runtime_status)) {
      return false;
    }
    if (run.trace_state && !allowedStates.has(run.trace_state)) {
      return false;
    }
    if (run.outbox_state && !allowedStates.has(run.outbox_state)) {
      return false;
    }
    if (run.trace_timeline === undefined) {
      return true;
    }
    if (!Array.isArray(run.trace_timeline)) {
      return false;
    }
    return run.trace_timeline.every((span) =>
      isRecord(span) &&
      !containsUnsafeAuditReference(span) &&
      (!span.status_code || allowedStates.has(span.status_code))
    );
  });
}

function consoleDataHasCredentialHandoffShape(consoleData) {
  if (!isRecord(consoleData.credentialHandoff)) {
    return false;
  }
  return isRecord(consoleData.credentialHandoff.summary) &&
    Array.isArray(consoleData.credentialHandoff.sessions) &&
    Array.isArray(consoleData.credentialHandoff.guardrails);
}

function isRecord(value) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

export function routesAreComplete(routes) {
  if (!Array.isArray(routes)) {
    return false;
  }
  const routeIds = new Set(routes.map((route) => route.id));
  return requiredRouteIds.every((routeId) => routeIds.has(routeId));
}

export function containsForbiddenKey(value, forbiddenKey) {
  if (Array.isArray(value)) {
    return value.some((item) => containsForbiddenKey(item, forbiddenKey));
  }
  if (value && typeof value === "object") {
    return Object.keys(value).includes(forbiddenKey) ||
      Object.values(value).some((item) => containsForbiddenKey(item, forbiddenKey));
  }
  return false;
}

function containsForbiddenCredentialMaterial(value) {
  return [
    "token_value",
    "private_key",
    "raw_input",
    "raw_output",
    "raw_request",
    "raw_response",
    "raw_url",
    "download_url",
    "raw_payload",
    "assertion_signature",
    "device_signature",
    "signature"
  ].some((key) => containsForbiddenKey(value, key));
}

export function statesAreKnown(consoleData) {
  const candidates = [
    consoleData.summary?.adapter?.status,
    ...(consoleData.summary?.metrics || []).map((item) => item.status),
    ...(consoleData.runs || []).flatMap((item) => [
      item.l5_state,
      item.policy_state,
      item.evidence_state,
      item.runtime_status,
      item.trace_state,
      item.outbox_state,
      ...(item.trace_timeline || []).map((span) => span.status_code)
    ]),
    ...(consoleData.evidence || []).map((item) => item.raw_access_state),
    ...(consoleData.approvals || []).flatMap((item) => [item.status, item.grant_status]),
    ...(consoleData.policies || []).map((item) => item.decision),
    ...(consoleData.risks || []).map((item) => item.state),
    ...(consoleData.quality || []).map((item) => item.status),
    ...(consoleData.adoption?.explanationChains || []).map((item) => item.status),
    ...(consoleData.adoption?.segments || []).map((item) => item.status),
    ...(consoleData.adoption?.reviewSignals || []).map((item) => item.status),
    ...(consoleData.evidenceVault?.requests || []).map((item) => item.status),
    ...(consoleData.evidenceVault?.grants || []).map((item) => item.status),
    ...(consoleData.evidenceVault?.auditTrail || []).map((item) => item.status),
    ...(consoleData.approvalWorkbench?.queues || []).map((item) => item.status),
    ...(consoleData.approvalWorkbench?.grants || []).map((item) => item.grant_status),
    ...(consoleData.approvalWorkbench?.auditTrail || []).map((item) => item.status),
    ...(consoleData.connectorWorkbench?.health || []).flatMap((item) => [
      item.status,
      item.freshness_state,
      item.rate_limit_state
    ]),
    ...(consoleData.connectorWorkbench?.dlq || []).map((item) => item.replay_state),
    ...(consoleData.connectorWorkbench?.syncTrail || []).map((item) => item.status),
    consoleData.sdlcRunWorkbench?.summary?.adapter_status,
    consoleData.sdlcRunWorkbench?.summary?.proof_state,
    consoleData.sdlcRunWorkbench?.summary?.dry_run_state,
    ...(consoleData.sdlcRunWorkbench?.reporter || []).flatMap((item) => [
      item.reporter_status,
      item.credential_status,
      item.source_signed,
      item.identity_confidence,
      item.governance_state
    ]),
    ...(consoleData.sdlcRunWorkbench?.outbox || []).flatMap((item) => [
      item.outbox_status,
      item.sequence_state
    ]),
    ...(consoleData.sdlcRunWorkbench?.eligibility || []).flatMap((item) => [
      item.l5_result,
      item.policy_state_known,
      item.governance_loaded,
      item.verification_fresh,
      item.outbox_delivered
    ]),
    consoleData.qualityCenterWorkbench?.workbench_state,
    ...(consoleData.qualityCenterWorkbench?.agent_summaries || []).flatMap((item) => [
      item.quality_state,
      item.lifecycle_state,
      item.scorer?.rollout_state,
      item.scorer_comparison?.comparison_state,
      item.scorer_comparison?.safety_impact,
      item.external_intake_health?.health_state
    ]),
    consoleData.qualityCenterWorkbench?.external_intake_portfolio?.portfolio_state,
    consoleData.qualityCenterWorkbench?.trend_summary?.report_state,
    consoleData.credentialHandoff?.summary?.verified_loaded,
    consoleData.credentialHandoff?.summary?.l5_status,
    ...(consoleData.credentialHandoff?.sessions || []).flatMap((item) => [
      item.bootstrap_status,
      item.credential_status,
      item.verified_loaded,
      item.l5_status
    ]),
    ...(consoleData.agentStore?.discoveryGaps || []).map((item) => item.state),
    ...(consoleData.agentStore?.runAudits || []).flatMap((item) => [item.registration_state, item.raw_access_state]),
    ...(consoleData.agentStore?.storeSummaries || []).flatMap((item) => [item.metadata_state, item.risk_state]),
    ...(consoleData.agentStore?.registryMap || []).map((item) => item.metadata_state),
    ...(consoleData.operationCenter?.notifications || []).map((item) => item.status),
    ...(consoleData.operationCenter?.todos || []).map((item) => item.status),
    ...(consoleData.operationCenter?.searchIndex || []).map((item) => item.status),
    ...(consoleData.actionWorkbench?.details || []).map((item) => item.status),
    ...(consoleData.actionWorkbench?.details || []).flatMap((item) => (item.timeline || []).map((node) => node.status)),
    ...(consoleData.connectors || []).map((item) => item.status),
    ...(consoleData.sdlcRuns || []).flatMap((item) => [item.adapter_status, item.dry_run_status, item.verified_loaded])
  ].filter(Boolean);

  return candidates.every((state) => allowedStates.has(state));
}

export function operationActionsResolve(consoleData) {
  const detailIds = new Set((consoleData.actionWorkbench?.details || []).map((item) => item.id));
  const operationItems = [
    ...(consoleData.operationCenter?.notifications || []),
    ...(consoleData.operationCenter?.todos || []),
    ...(consoleData.operationCenter?.searchIndex || [])
  ];
  return operationItems.every((item) => !item.action_id || detailIds.has(item.action_id));
}

export function credentialHandoffIsSafe(consoleData) {
  const workbench = consoleData.credentialHandoff;
  if (!consoleDataHasCredentialHandoffShape(consoleData) || containsUnsafeAuditReference(workbench)) {
    return false;
  }
  const summary = workbench.summary;
  const sessions = workbench.sessions;
  if (
    summary.schema_version !== "agentops_credential_status.v1" ||
    summary.agentops_fact_owner !== "agentops" ||
    summary.agent_store_boundary !== "display_only_no_active_inference" ||
    summary.verified_loaded !== "not_asserted" ||
    summary.l5_status !== "not_asserted"
  ) {
    return false;
  }
  const issued = sessions.filter((item) => item.bootstrap_status === "credential_issued").length;
  const verified = sessions.filter((item) => item.bootstrap_status === "signature_verified").length;
  const revoked = sessions.filter((item) => item.bootstrap_status === "revoked" || item.credential_status === "revoked").length;
  const reissued = sessions.filter((item) => item.revocation_resolution === "reissued").length;
  if (
    summary.bootstrap_count !== sessions.length ||
    summary.credential_issued !== issued ||
    summary.signature_verified !== verified ||
    summary.revoked !== revoked ||
    summary.reissued !== reissued
  ) {
    return false;
  }
  const guardrailsText = workbench.guardrails.join(" ");
  if (
    !/不得本地推导 active/.test(guardrailsText) ||
    !/不构成 verified_loaded 或 L5/.test(guardrailsText) ||
    !/revoked 必须阻断后续签名测试和企业事件接入/.test(guardrailsText) ||
    !/旧 token 仍必须被拒绝/.test(guardrailsText)
  ) {
    return false;
  }
  return sessions.every((item) =>
    item.schema_version === "agentops_credential_status.v1" &&
    item.agentops_fact_owner === "agentops" &&
    item.agent_store_consumer_boundary === "display_only_no_active_inference" &&
    item.allowed_actions === "display_status,show_next_action" &&
    item.forbidden_actions === "infer_active,issue_credential,issue_ingestion_token,issue_device_key" &&
    item.token_id === "已隐藏" &&
    item.verified_loaded === "not_asserted" &&
    item.l5_status === "not_asserted" &&
    revocationFieldsMatchStatus(item) &&
    /只读回显/.test(item.display_scope || "") &&
    !containsUnsafeLifecycleText(`${item.next_action || ""} ${item.display_scope || ""}`)
  );
}

function revocationFieldsMatchStatus(item) {
  if (item.bootstrap_status === "revoked" || item.credential_status === "revoked") {
    return item.next_action === "reissue_credential" &&
      item.revocation_id &&
      item.revocation_id !== "未撤销" &&
      item.revoked_at &&
      item.revoked_at !== "未撤销" &&
      item.revocation_reason &&
      item.revocation_reason !== "未撤销" &&
      item.revocation_scope &&
      item.revocation_scope !== "未撤销" &&
      reissueFieldsMatchResolution(item);
  }
  return item.revocation_id === "未撤销" &&
    item.revoked_at === "未撤销" &&
    item.revocation_reason === "未撤销" &&
    item.revocation_scope === "未撤销" &&
    reissueFieldsMatchResolution(item);
}

function reissueFieldsMatchResolution(item) {
  const fields = [
    item.reissue_id,
    item.reissued_at,
    item.reissued_by,
    item.reissued_bootstrap_id,
    item.reissued_credential_id
  ];
  if (item.revocation_resolution === "reissued") {
    return fields.every((value) => value && value !== "未重新签发");
  }
  return item.revocation_resolution === "未重新签发" &&
    fields.every((value) => value === "未重新签发");
}

export function actionDetailsAreComplete(consoleData) {
  const details = consoleData.actionWorkbench?.details || [];
  return details.every((detail) => {
    const timeline = detail.timeline;
    const auditPacket = detail.audit_packet;
    if (containsUnsafeAuditReference(detail)) {
      return false;
    }
    return Array.isArray(timeline) &&
      timeline.length >= 3 &&
      timeline.every((node) =>
        node &&
        node.id &&
        node.stage &&
        node.occurred_at &&
        node.title &&
        node.body &&
        node.owner &&
        node.status
      ) &&
      auditPacket &&
      auditPacket.packet_id &&
      auditPacket.summary &&
      auditPacket.export_state &&
      Array.isArray(auditPacket.evidence_refs) &&
      Array.isArray(auditPacket.echo_targets) &&
      auditPacket.echo_targets.length > 0 &&
      auditPacket.retention_policy &&
      auditPacket.safety_note &&
      !auditPacket.download_url &&
      !auditPacket.raw_url;
  });
}

export function evidenceVaultIsComplete(consoleData) {
  const evidenceVault = consoleData.evidenceVault;
  if (!isRecord(evidenceVault) || containsUnsafeAuditReference(evidenceVault)) {
    return false;
  }
  if (!keysAreExactly(evidenceVault, ["requests", "grants", "auditTrail", "guardrails"])) {
    return false;
  }
  const evidenceItems = consoleData.evidence || [];
  const evidenceById = new Map(evidenceItems.map((item) => [item.evidence_id, item]));
  if (
    evidenceById.size !== evidenceItems.length ||
    !vaultRowsMatchEvidence(evidenceItems, evidenceVault.requests) ||
    !vaultRowsMatchEvidence(evidenceItems, evidenceVault.grants) ||
    !vaultRowsMatchEvidence(evidenceItems, evidenceVault.auditTrail)
  ) {
    return false;
  }

  const requestsOk = evidenceVault.requests.every((request) =>
    keysAreExactly(request, [
      "id",
      "evidence_id",
      "run_id",
      "requester",
      "reason",
      "status",
      "denied_scope",
      "audit_id",
      "ttl_summary",
      "primary_action",
      "safety_note"
    ]) &&
    request.id &&
    request.evidence_id &&
    request.run_id &&
    request.requester &&
    request.reason &&
    request.status &&
    request.audit_id &&
    request.ttl_summary &&
    ["申请原文访问", "查看授权记录", "补充申请理由", "仅查看哈希告警", "等待审批"].includes(request.primary_action) &&
    /不展示 Evidence Vault 原文/.test(request.safety_note || "") &&
    vaultRequestMatchesEvidence(request, evidenceById.get(request.evidence_id)) &&
    !containsUnsafeLifecycleText(`${request.reason || ""} ${request.primary_action || ""} ${request.safety_note || ""}`)
  );

  const grantsOk = evidenceVault.grants.every((grant) =>
    keysAreExactly(grant, [
      "id",
      "evidence_id",
      "requester",
      "status",
      "scope",
      "expires_at",
      "audit_id",
      "consumption_policy"
    ]) &&
    grant.id &&
    grant.evidence_id &&
    grant.requester &&
    grant.status &&
    grant.scope &&
    grant.expires_at &&
    grant.audit_id &&
    /不提供原文下载/.test(grant.consumption_policy || "") &&
    vaultGrantMatchesEvidence(grant, evidenceById.get(grant.evidence_id)) &&
    !containsUnsafeLifecycleText(grant.consumption_policy || "")
  );

  const auditTrailOk = evidenceVault.auditTrail.every((node) =>
    keysAreExactly(node, ["id", "evidence_id", "stage", "occurred_at", "summary", "owner", "status", "audit_id"]) &&
    node.id &&
    node.evidence_id &&
    node.stage &&
    node.occurred_at &&
    node.summary &&
    node.owner &&
    node.status &&
    node.audit_id &&
    vaultAuditMatchesEvidence(node, evidenceById.get(node.evidence_id)) &&
    !containsUnsafeLifecycleText(node.summary || "")
  );

  const guardrailsText = evidenceVault.guardrails.join(" ");
  return requestsOk &&
    grantsOk &&
    auditTrailOk &&
    evidenceVault.guardrails.every((item) => typeof item === "string" && item) &&
    /默认不展示原文/.test(guardrailsText) &&
    !containsUnsafeLifecycleText(guardrailsText);
}

function vaultRowsMatchEvidence(evidenceItems, rows) {
  if (!Array.isArray(rows) || rows.length !== evidenceItems.length) {
    return false;
  }
  const evidenceIds = new Set(evidenceItems.map((item) => item.evidence_id));
  const rowIds = new Set(rows.map((item) => item.evidence_id));
  return rowIds.size === rows.length &&
    evidenceIds.size === evidenceItems.length &&
    evidenceItems.every((item) => rowIds.has(item.evidence_id));
}

function vaultRequestMatchesEvidence(request, evidence) {
  if (!evidence || request.run_id !== evidence.run_id || request.audit_id !== evidence.audit_id) {
    return false;
  }
  const state = evidence.raw_access_state;
  if (state === "approved_limited") {
    return request.status === "approved_limited" &&
      request.primary_action === "查看授权记录" &&
      /限时/.test(request.ttl_summary);
  }
  if (state === "degraded") {
    return request.status === "pending" &&
      request.primary_action === "等待审批" &&
      request.ttl_summary === "待补偿";
  }
  if (state === "permission_denied") {
    return request.status === "permission_denied" &&
      request.primary_action === "补充申请理由" &&
      request.ttl_summary === "未授权";
  }
  if (state === "redaction_failed") {
    return request.status === "redaction_failed" &&
      request.primary_action === "仅查看哈希告警" &&
      /脱敏失败|暂停授权/.test(request.ttl_summary);
  }
  if (state === "summary_only") {
    return request.status === "pending" &&
      request.primary_action === "申请原文访问" &&
      request.ttl_summary === "待审批";
  }
  return false;
}

function vaultGrantMatchesEvidence(grant, evidence) {
  if (!evidence || grant.audit_id !== evidence.audit_id) {
    return false;
  }
  const state = evidence.raw_access_state;
  if (state === "approved_limited") {
    return grant.status === "active" &&
      /限定/.test(grant.scope) &&
      /15 分钟/.test(grant.expires_at);
  }
  if (state === "degraded") {
    return grant.status === "pending" &&
      /待补偿/.test(grant.scope) &&
      grant.expires_at === "待补偿";
  }
  if (state === "permission_denied") {
    return grant.status === "rejected" &&
      grant.expires_at === "未授权";
  }
  if (state === "redaction_failed") {
    return grant.status === "redaction_failed" &&
      grant.expires_at === "暂停授权";
  }
  if (state === "summary_only") {
    return grant.status === "pending" &&
      grant.expires_at === "待审批";
  }
  return false;
}

function vaultAuditMatchesEvidence(node, evidence) {
  return Boolean(evidence) &&
    node.audit_id === evidence.audit_id &&
    node.status === evidence.raw_access_state;
}

export function approvalWorkbenchIsComplete(consoleData) {
  const workbench = consoleData.approvalWorkbench;
  if (!isRecord(workbench) || containsUnsafeAuditReference(workbench)) {
    return false;
  }
  if (!keysAreExactly(workbench, ["queues", "grants", "auditTrail", "guardrails"])) {
    return false;
  }
  const approvals = consoleData.approvals || [];
  const approvalsById = new Map(approvals.map((item) => [item.approval_id, item]));
  if (
    approvalsById.size !== approvals.length ||
    !approvalRowsMatchApprovals(approvals, workbench.queues) ||
    !approvalRowsMatchApprovals(approvals, workbench.grants) ||
    !approvalRowsMatchApprovals(approvals, workbench.auditTrail)
  ) {
    return false;
  }

  const queuesOk = workbench.queues.every((item) =>
    keysAreExactly(item, [
      "id",
      "approval_id",
      "requester",
      "reason",
      "affected_actions",
      "status",
      "sla_due_at",
      "sla_state",
      "approver_scope",
      "supplemental_materials",
      "primary_action",
      "secondary_action",
      "audit_id",
      "denied_scope",
      "safety_note"
    ]) &&
    item.id &&
    item.approval_id &&
    item.requester &&
    item.reason &&
    item.affected_actions &&
    item.status &&
    item.sla_due_at &&
    item.sla_state &&
    item.approver_scope &&
    item.supplemental_materials &&
    item.primary_action &&
    item.secondary_action &&
    item.audit_id &&
    /只读展示审批处置摘要/.test(item.safety_note || "") &&
    approvalQueueMatchesApproval(item, approvalsById.get(item.approval_id)) &&
    !containsUnsafeLifecycleText(`${item.primary_action || ""} ${item.secondary_action || ""} ${item.safety_note || ""}`)
  );

  const grantsOk = workbench.grants.every((item) =>
    keysAreExactly(item, [
      "id",
      "approval_id",
      "grant_status",
      "policy_version",
      "resource_scope",
      "ttl_summary",
      "expires_at",
      "revocation_state",
      "audit_id",
      "consumption_policy"
    ]) &&
    item.id &&
    item.approval_id &&
    item.grant_status &&
    item.policy_version &&
    item.resource_scope &&
    item.ttl_summary &&
    item.expires_at &&
    item.revocation_state &&
    item.audit_id &&
    /绑定审批、策略版本和资源范围/.test(item.consumption_policy || "") &&
    approvalGrantMatchesApproval(item, approvalsById.get(item.approval_id)) &&
    !containsUnsafeLifecycleText(`${item.revocation_state || ""} ${item.consumption_policy || ""}`)
  );

  const auditOk = workbench.auditTrail.every((item) =>
    keysAreExactly(item, ["id", "approval_id", "stage", "occurred_at", "summary", "owner", "status", "audit_id"]) &&
    item.id &&
    item.approval_id &&
    item.stage &&
    item.occurred_at &&
    item.summary &&
    item.owner &&
    item.status &&
    item.audit_id &&
    approvalAuditMatchesApproval(item, approvalsById.get(item.approval_id)) &&
    !containsUnsafeLifecycleText(item.summary || "")
  );

  const guardrailsText = workbench.guardrails.join(" ");
  return queuesOk &&
    grantsOk &&
    auditOk &&
    workbench.guardrails.every((item) => typeof item === "string" && item) &&
    /审批队列只展示人工处置摘要/.test(guardrailsText) &&
    /不得作为唯一审批人/.test(guardrailsText) &&
    !containsUnsafeLifecycleText(guardrailsText);
}

function approvalRowsMatchApprovals(approvals, rows) {
  if (!Array.isArray(rows) || rows.length !== approvals.length) {
    return false;
  }
  const approvalIds = new Set(approvals.map((item) => item.approval_id));
  const rowIds = new Set(rows.map((item) => item.approval_id));
  return rowIds.size === rows.length &&
    approvalIds.size === approvals.length &&
    approvals.every((item) => rowIds.has(item.approval_id));
}

function approvalQueueMatchesApproval(item, approval) {
  return Boolean(approval) &&
    item.requester === approval.requester &&
    item.reason === approval.reason &&
    item.affected_actions === approval.affected_actions &&
    item.status === approval.status &&
    item.sla_due_at === approval.sla_due_at &&
    item.audit_id === approval.audit_id;
}

function approvalGrantMatchesApproval(item, approval) {
  return Boolean(approval) &&
    item.grant_status === legacyApprovalGrantStatus(approval.status, approval.grant_status) &&
    item.audit_id === approval.audit_id &&
    approvalGrantStatusAllowed(approval.status, item.grant_status) &&
    approvalGrantFieldsMatchStatus(item);
}

function approvalGrantStatusAllowed(approvalStatus, grantStatus) {
  if (approvalStatus === "approved") {
    return ["active", "expired"].includes(grantStatus);
  }
  if (approvalStatus === "revoked") {
    return grantStatus === "revoked";
  }
  if (approvalStatus === "rejected") {
    return grantStatus === "rejected";
  }
  if (approvalStatus === "expired") {
    return grantStatus === "expired";
  }
  if (approvalStatus === "escalated") {
    return ["pending", "expired"].includes(grantStatus);
  }
  if (["pending", "needs_more_info"].includes(approvalStatus)) {
    return grantStatus === "pending";
  }
  return grantStatus !== "active";
}

function approvalGrantFieldsMatchStatus(item) {
  if (item.grant_status === "active") {
    return /15 分钟/.test(item.ttl_summary) &&
      /15 分钟/.test(item.expires_at) &&
      /未撤销/.test(item.revocation_state);
  }
  if (item.grant_status === "expired") {
    return item.ttl_summary === "Grant 已过期" &&
      item.expires_at === "已过期" &&
      item.revocation_state === "已过期，需重新审批";
  }
  if (item.grant_status === "revoked") {
    return item.ttl_summary === "Grant 已撤销" &&
      item.expires_at === "已撤销" &&
      /已撤销/.test(item.revocation_state);
  }
  if (item.grant_status === "rejected") {
    return item.ttl_summary === "未签发 Grant" &&
      item.expires_at === "未授权" &&
      item.revocation_state === "未签发";
  }
  if (item.grant_status === "pending") {
    return item.ttl_summary === "待审批后签发" &&
      item.expires_at === "待审批" &&
      item.revocation_state === "未签发";
  }
  return false;
}

function approvalAuditMatchesApproval(item, approval) {
  return Boolean(approval) &&
    item.status === approval.status &&
    item.audit_id === approval.audit_id;
}

export function connectorWorkbenchIsComplete(consoleData) {
  const workbench = consoleData.connectorWorkbench;
  if (!isRecord(workbench) || containsUnsafeAuditReference(workbench)) {
    return false;
  }
  if (!Array.isArray(consoleData.connectors) || containsUnsafeAuditReference(consoleData.connectors)) {
    return false;
  }
  if (!keysAreExactly(workbench, ["health", "dlq", "syncTrail", "guardrails"])) {
    return false;
  }
  const connectors = consoleData.connectors || [];
  const connectorsById = new Map(connectors.map((item) => [item.id, item]));
  if (
    connectorsById.size !== connectors.length ||
    !connectorBoundarySetIsSafe(connectorsById) ||
    !connectorRowsMatchConnectors(connectors, workbench.health) ||
    !connectorRowsMatchConnectors(connectors, workbench.dlq) ||
    !connectorRowsMatchConnectors(connectors, workbench.syncTrail)
  ) {
    return false;
  }

  const healthOk = workbench.health.every((item) =>
    keysAreExactly(item, [
      "id",
      "connector_id",
      "name",
      "status",
      "last_seen_at",
      "freshness",
      "freshness_state",
      "rate_limit_state",
      "rate_limit_detail",
      "degrade_action",
      "evidence_impact",
      "owner",
      "request_id",
      "primary_action",
      "secondary_action",
      "safety_note"
    ]) &&
    item.id &&
    item.connector_id &&
    item.name &&
    item.status &&
    item.last_seen_at &&
    item.freshness &&
    item.freshness_state &&
    item.rate_limit_state &&
    item.rate_limit_detail &&
    item.degrade_action &&
    item.evidence_impact &&
    item.owner &&
    item.request_id &&
    item.primary_action &&
    item.secondary_action &&
    /只读健康摘要/.test(item.safety_note || "") &&
    connectorHealthMatchesConnector(item, connectorsById.get(item.connector_id)) &&
    connectorHealthStateIsSafe(item) &&
    !containsUnsafeLifecycleText(`${item.primary_action || ""} ${item.secondary_action || ""} ${item.safety_note || ""}`)
  );

  const dlqOk = workbench.dlq.every((item) =>
    keysAreExactly(item, [
      "id",
      "connector_id",
      "dlq_depth",
      "oldest_event_age",
      "replay_state",
      "retry_window",
      "degrade_policy",
      "request_id",
      "audit_id",
      "safety_note"
    ]) &&
    item.id &&
    item.connector_id &&
    item.dlq_depth &&
    item.oldest_event_age &&
    item.replay_state &&
    item.retry_window &&
    item.degrade_policy &&
    item.request_id &&
    item.audit_id &&
    /只展示队列摘要/.test(item.safety_note || "") &&
    connectorDlqMatchesConnector(item, connectorsById.get(item.connector_id)) &&
    !containsUnsafeLifecycleText(`${item.retry_window || ""} ${item.degrade_policy || ""} ${item.safety_note || ""}`)
  );

  const syncOk = workbench.syncTrail.every((item) =>
    keysAreExactly(item, ["id", "connector_id", "stage", "occurred_at", "summary", "owner", "status", "request_id"]) &&
    item.id &&
    item.connector_id &&
    item.stage &&
    item.occurred_at &&
    item.summary &&
    item.owner &&
    item.status &&
    item.request_id &&
    connectorSyncMatchesConnector(item, connectorsById.get(item.connector_id)) &&
    !containsUnsafeLifecycleText(item.summary || "")
  );

  const guardrailsText = workbench.guardrails.join(" ");
  return healthOk &&
    dlqOk &&
    syncOk &&
    sdlcConnectorProofStateIsSafe(consoleData, workbench) &&
    workbench.guardrails.every((item) => typeof item === "string" && item) &&
    /15 分钟/.test(guardrailsText) &&
    /超过 20 分钟/.test(guardrailsText) &&
    /DLQ/.test(guardrailsText) &&
    /Outbox Replay/.test(guardrailsText) &&
    /不构成 verified_loaded/.test(guardrailsText) &&
    /原始载荷/.test(guardrailsText) &&
    !containsUnsafeLifecycleText(guardrailsText);
}

function connectorBoundarySetIsSafe(connectorsById) {
  const externalConnectors = ["conn_git", "conn_pr", "conn_ci", "conn_test"];
  const hasAnyExternalConnector = externalConnectors.some((connectorId) => connectorsById.has(connectorId));
  if (!hasAnyExternalConnector) {
    return connectorsById.has("conn_iam");
  }
  return [...externalConnectors, "conn_iam"].every((connectorId) => connectorsById.has(connectorId));
}

function connectorRowsMatchConnectors(connectors, rows) {
  if (!Array.isArray(rows) || rows.length !== connectors.length) {
    return false;
  }
  const connectorIds = new Set(connectors.map((item) => item.id));
  const rowIds = new Set(rows.map((item) => item.connector_id));
  return rowIds.size === rows.length &&
    connectorIds.size === connectors.length &&
    connectors.every((item) => rowIds.has(item.id));
}

function connectorHealthMatchesConnector(item, connector) {
  return Boolean(connector) &&
    item.connector_id === connector.id &&
    item.name === connector.name &&
    item.status === connector.status &&
    item.last_seen_at === connector.last_seen_at &&
    item.degrade_action === connector.degrade_action &&
    item.request_id === connector.request_id;
}

function connectorHealthStateIsSafe(item) {
  if (item.status === "healthy") {
    return item.freshness_state === "healthy" &&
      ["healthy", "warning"].includes(item.rate_limit_state) &&
      item.primary_action === "保持监控" &&
      /未触发限流|治理证明未完成|接近配额|限流/.test(item.rate_limit_detail || "") &&
      /不降低/.test(item.evidence_impact || "");
  }
  if (item.status === "materialized") {
    return item.freshness_state === "materialized" &&
      item.rate_limit_state === "warning" &&
      item.primary_action === "补齐治理加载证明" &&
      /不提升为 verified_loaded/.test(item.rate_limit_detail || "") &&
      /不构成 verified_loaded/.test(item.evidence_impact || "");
  }
  if (item.status === "degraded") {
    return item.freshness_state === "degraded" &&
      item.rate_limit_state === "degraded" &&
      item.primary_action === "查看降级影响" &&
      /降低证据等级/.test(item.rate_limit_detail || "") &&
      /降低证据等级/.test(item.evidence_impact || "");
  }
  return item.freshness_state === "unknown" &&
    item.rate_limit_state === "unknown";
}

function connectorDlqMatchesConnector(item, connector) {
  if (!connector || item.request_id !== connector.request_id) {
    return false;
  }
  if (connector.status === "healthy") {
    return item.dlq_depth === "0" &&
      item.oldest_event_age === "0 分钟" &&
      item.replay_state === "healthy" &&
      item.retry_window === "无需回放";
  }
  if (connector.status === "materialized") {
    return item.dlq_depth === "待验证" &&
      item.replay_state === "materialized" &&
      /verified_loaded/.test(item.retry_window || "") &&
      /不提升证据等级/.test(item.degrade_policy || "");
  }
  if (connector.status === "degraded") {
    return item.dlq_depth !== "0" &&
      item.oldest_event_age !== "0 分钟" &&
      /分钟|小时|天/.test(item.oldest_event_age || "") &&
      item.replay_state === "pending" &&
      /人工审批/.test(item.retry_window || "") &&
      /Outbox Replay/.test(item.degrade_policy || "");
  }
  return false;
}

function connectorSyncMatchesConnector(item, connector) {
  return Boolean(connector) &&
    item.connector_id === connector.id &&
    item.status === connector.status &&
    item.occurred_at === connector.last_seen_at &&
    item.request_id === connector.request_id;
}

export function sdlcRunWorkbenchIsComplete(consoleData) {
  const workbench = consoleData.sdlcRunWorkbench;
  if (!isRecord(workbench) || containsUnsafeAuditReference(workbench)) {
    return false;
  }
  if (!keysAreExactly(workbench, ["summary", "reporter", "outbox", "eligibility", "guardrails"])) {
    return false;
  }
  if (!keysAreExactly(workbench.summary, [
    "id",
    "adapter_status",
    "proof_state",
    "dry_run_state",
    "reporter_ready",
    "pending_proofs",
    "primary_action",
    "safety_note"
  ])) {
    return false;
  }
  const sdlcRuns = consoleData.sdlcRuns || [];
  if (!Array.isArray(sdlcRuns) || containsUnsafeAuditReference(sdlcRuns)) {
    return false;
  }
  const sdlcRunsByRef = new Map(sdlcRuns.map((item) => [sdlcRunRef(item), item]));
  if (
    sdlcRunsByRef.size !== sdlcRuns.length ||
    !sdlcWorkbenchRowsMatchRuns(sdlcRuns, workbench.reporter) ||
    !sdlcWorkbenchRowsMatchRuns(sdlcRuns, workbench.outbox) ||
    !sdlcWorkbenchRowsMatchRuns(sdlcRuns, workbench.eligibility)
  ) {
    return false;
  }

  const verifiedProofCount = sdlcRuns.filter((item) => sdlcProofVerified(item)).length;
  const expectedProofState = sdlcRuns.length > 0 && verifiedProofCount === sdlcRuns.length
    ? "verified_loaded"
    : "unverified";
  const expectedDryRunState = sdlcDryRunState(sdlcRuns);
  const summaryOk = workbench.summary.id &&
    workbench.summary.adapter_status === consoleData.summary?.adapter?.status &&
    workbench.summary.proof_state === expectedProofState &&
    workbench.summary.dry_run_state === expectedDryRunState &&
    Number.isInteger(workbench.summary.reporter_ready) &&
    Number.isInteger(workbench.summary.pending_proofs) &&
    workbench.summary.reporter_ready === verifiedProofCount &&
    workbench.summary.pending_proofs === sdlcRuns.length - verifiedProofCount &&
    (
      expectedProofState === "verified_loaded"
        ? workbench.summary.primary_action === "保持治理加载证明"
        : /verified_loaded/.test(workbench.summary.primary_action || "")
    ) &&
    /不构成 verified_loaded/.test(workbench.summary.safety_note || "");

  const reporterOk = workbench.reporter.every((item) =>
    keysAreExactly(item, [
      "id",
      "run_id",
      "command",
      "reporter_status",
      "integration_mode",
      "credential_status",
      "source_signed",
      "identity_confidence",
      "governance_state",
      "proof_source",
      "primary_action",
      "safety_note"
    ]) &&
    item.id &&
    item.run_id &&
    item.command &&
    item.reporter_status &&
    item.integration_mode === "enterprise_managed" &&
    item.credential_status &&
    item.source_signed &&
    item.identity_confidence &&
    item.governance_state &&
    item.proof_source &&
    /只读 Reporter 摘要/.test(item.safety_note || "") &&
    sdlcReporterMatchesRun(item, sdlcRunsByRef.get(item.run_id)) &&
    !containsUnsafeLifecycleText(`${item.primary_action || ""} ${item.safety_note || ""}`)
  );

  const outboxOk = workbench.outbox.every((item) =>
    keysAreExactly(item, [
      "id",
      "run_id",
      "outbox_status",
      "sequence_state",
      "pending_events",
      "oldest_pending_age",
      "replay_boundary",
      "evidence_impact",
      "audit_id",
      "safety_note"
    ]) &&
    item.id &&
    item.run_id &&
    item.outbox_status &&
    item.sequence_state &&
    item.pending_events &&
    item.oldest_pending_age &&
    /不在 Console 执行 Outbox Replay/.test(item.replay_boundary || "") &&
    item.evidence_impact &&
    item.audit_id &&
    /不提供重放按钮/.test(item.safety_note || "") &&
    sdlcOutboxMatchesRun(item, sdlcRunsByRef.get(item.run_id)) &&
    !containsUnsafeLifecycleText(`${item.replay_boundary || ""} ${item.safety_note || ""}`)
  );

  const eligibilityOk = workbench.eligibility.every((item) =>
    keysAreExactly(item, [
      "id",
      "run_id",
      "evidence_level",
      "l5_result",
      "failed_conditions",
      "policy_state_known",
      "governance_loaded",
      "verification_fresh",
      "outbox_delivered",
      "next_action",
      "safety_note"
    ]) &&
    item.id &&
    item.run_id &&
    item.evidence_level &&
    item.l5_result &&
    item.failed_conditions &&
    item.policy_state_known &&
    item.governance_loaded &&
    item.verification_fresh &&
    item.outbox_delivered &&
    item.next_action &&
    /不覆盖 AgentOps 后端最终等级判定/.test(item.safety_note || "") &&
    sdlcEligibilityMatchesRun(item, sdlcRunsByRef.get(item.run_id)) &&
    !containsUnsafeLifecycleText(`${item.next_action || ""} ${item.safety_note || ""}`)
  );

  const guardrailsText = workbench.guardrails.join(" ");
  return summaryOk &&
    reporterOk &&
    outboxOk &&
    eligibilityOk &&
    workbench.guardrails.every((item) => typeof item === "string" && item) &&
    /Reporter active/.test(guardrailsText) &&
    /Outbox delivered/.test(guardrailsText) &&
    /Outbox Replay/.test(guardrailsText) &&
    /materialized\/unverified/.test(guardrailsText) &&
    /不构成 verified_loaded/.test(guardrailsText) &&
    /failed_conditions/.test(guardrailsText) &&
    /原始载荷/.test(guardrailsText) &&
    !containsUnsafeLifecycleText(guardrailsText);
}

export function qualityCenterWorkbenchIsComplete(consoleData) {
  const workbench = consoleData.qualityCenterWorkbench;
  if (!consoleDataHasQualityCenterWorkbenchShape(consoleData) || containsUnsafeAuditReference(workbench)) {
    return false;
  }
  if (!keysAreSubset(workbench.summary, [
    "payload_access",
    "prompt_access",
    "change_access",
    "terminal_access",
    "automatic_rollout_enabled",
    "automatic_lifecycle_action",
    "store_write_performed",
    "automatic_publish_performed",
    "notification_sent",
    "external_intake_receipt_count"
  ])) {
    return false;
  }
  if (!keysAreSubset(workbench.scorer_rollout_panel, [
    "candidate_count",
    "ready_for_manual_approval_count",
    "needs_human_review_count",
    "insufficient_evidence_count",
    "automatic_rollout_enabled",
    "automatic_template_switch",
    "manual_approval_queue_size"
  ])) {
    return false;
  }
  if (!externalIntakePanelIsSafe(workbench.external_intake_panel) ||
    !externalIntakePortfolioIsSafe(workbench.external_intake_portfolio)) {
    return false;
  }
  if (
    workbench.summary.automatic_rollout_enabled !== false ||
    workbench.summary.automatic_lifecycle_action !== false ||
    workbench.summary.store_write_performed !== false ||
    workbench.summary.automatic_publish_performed !== false ||
    workbench.summary.notification_sent !== false ||
    workbench.scorer_rollout_panel.automatic_rollout_enabled !== false ||
    workbench.scorer_rollout_panel.automatic_template_switch !== false ||
    workbench.external_intake_panel.automatic_rollout_enabled !== false ||
    workbench.external_intake_panel.automatic_scorer_invocation !== false ||
    workbench.external_intake_panel.store_write_performed !== false
  ) {
    return false;
  }
  const agentSummariesOk = workbench.agent_summaries.every((summary) =>
    keysAreExactly(summary, [
      "agent_id",
      "version",
      "owner_team",
      "score",
      "quality_state",
      "confidence",
      "score_template_id",
      "evidence_level",
      "missing_evidence",
      "explanation",
      "lifecycle_state",
      "lifecycle_action",
      "scorer",
      "scorer_comparison",
      "external_intake_health"
    ]) &&
    typeof summary.score === "number" &&
    typeof summary.confidence === "number" &&
    Array.isArray(summary.missing_evidence) &&
    keysAreExactly(summary.scorer, ["scorer_id", "scorer_version", "rollout_state"]) &&
    keysAreExactly(summary.scorer_comparison, [
      "comparison_state",
      "safety_impact",
      "alignment_delta",
      "recommendation",
      "manual_approval_required"
    ]) &&
    summary.scorer_comparison.manual_approval_required === true &&
    externalIntakeHealthIsSafe(summary.external_intake_health) &&
    !containsUnsafeLifecycleText(summary) &&
    !containsForbiddenCredentialMaterial(summary)
  );
  const reviewQueueOk = workbench.review_queue.every((item) =>
    keysAreExactly(item, [
      "id",
      "agent_id",
      "version",
      "review_type",
      "reason",
      "recommended_action",
      "owner_team",
      "manual_review_required",
      "automatic_action_performed"
    ]) &&
    item.manual_review_required === true &&
    item.automatic_action_performed === false &&
    !containsUnsafeLifecycleText(item) &&
    !containsForbiddenCredentialMaterial(item)
  );
  const trendOk = keysAreSubset(workbench.trend_summary, [
    "report_state",
    "retention_rate",
    "review_queue_size",
    "rework_rounds",
    "pr_review_findings",
    "recommendation"
  ]) &&
    !containsUnsafeLifecycleText(workbench.trend_summary);
  return agentSummariesOk && reviewQueueOk && trendOk;
}

function externalIntakeHealthIsSafe(health) {
  return keysAreExactly(health, [
    "schema_version",
    "health_state",
    "receipt_count",
    "window_limit",
    "latest_intake_id",
    "latest_received_at",
    "latest_pass_rate",
    "latest_sample_size",
    "intake_state_counts",
    "source_trust_counts",
    "accepted_execution_count",
    "scorer_refs",
    "manual_review_required",
    "recommendation",
    "summary"
  ]) &&
    health.schema_version === "quality_center_external_intake_health.v1" &&
    ["no_receipts", "receiving", "needs_review"].includes(health.health_state) &&
    Number.isFinite(Number(health.receipt_count)) &&
    Number.isFinite(Number(health.accepted_execution_count)) &&
    Array.isArray(health.scorer_refs) &&
    health.scorer_refs.every((item) => keysAreExactly(item, ["scorer_id", "scorer_version"])) &&
    keysAreExactly(health.summary, [
      "summary_only_intake_health",
      "latest_summary_keys",
      "automatic_rollout_enabled",
      "automatic_template_switch",
      "scorer_execution_performed",
      "store_write_performed",
      "notification_sent"
    ]) &&
    Array.isArray(health.summary.latest_summary_keys) &&
    health.summary.summary_only_intake_health === true &&
    health.summary.automatic_rollout_enabled === false &&
    health.summary.automatic_template_switch === false &&
    health.summary.scorer_execution_performed === false &&
    health.summary.store_write_performed === false &&
    health.summary.notification_sent === false;
}

function externalIntakePanelIsSafe(panel) {
  return keysAreExactly(panel, [
    "monitored_agent_count",
    "receiving_count",
    "no_receipts_count",
    "needs_review_count",
    "receipt_count",
    "accepted_execution_count",
    "manual_review_queue_size",
    "automatic_rollout_enabled",
    "automatic_scorer_invocation",
    "store_write_performed"
  ]) &&
    panel.automatic_rollout_enabled === false &&
    panel.automatic_scorer_invocation === false &&
    panel.store_write_performed === false;
}

function externalIntakePortfolioIsSafe(portfolio) {
  return keysAreExactly(portfolio, [
    "schema_version",
    "portfolio_state",
    "scope_count",
    "version_scope_count",
    "state_counts",
    "receipt_count",
    "accepted_execution_count",
    "manual_review_queue_size",
    "required_missing_scope_count",
    "required_missing_scopes",
    "latest_receipts",
    "scorer_coverage",
    "summary"
  ]) &&
    portfolio.schema_version === "quality_center_external_intake_portfolio.v1" &&
    ["empty", "no_receipts", "receiving", "incomplete", "needs_review"].includes(portfolio.portfolio_state) &&
    Array.isArray(portfolio.required_missing_scopes) &&
    Array.isArray(portfolio.latest_receipts) &&
    portfolio.required_missing_scopes.every((item) =>
      keysAreExactly(item, ["agent_id", "version", "owner_team", "health_state", "recommendation"])
    ) &&
    portfolio.latest_receipts.every((item) =>
      keysAreExactly(item, [
        "agent_id",
        "version",
        "health_state",
        "latest_intake_id",
        "latest_received_at",
        "latest_pass_rate",
        "latest_sample_size"
      ])
    ) &&
    keysAreExactly(portfolio.scorer_coverage, [
      "unique_scorer_count",
      "scopes_with_scorer_receipts",
      "scorer_refs"
    ]) &&
    Array.isArray(portfolio.scorer_coverage.scorer_refs) &&
    keysAreExactly(portfolio.summary, [
      "summary_only_intake_portfolio",
      "automatic_rollout_enabled",
      "automatic_template_switch",
      "automatic_scorer_invocation",
      "scorer_execution_performed",
      "store_write_performed",
      "notification_sent"
    ]) &&
    portfolio.summary.summary_only_intake_portfolio === true &&
    portfolio.summary.automatic_rollout_enabled === false &&
    portfolio.summary.automatic_template_switch === false &&
    portfolio.summary.automatic_scorer_invocation === false &&
    portfolio.summary.scorer_execution_performed === false &&
    portfolio.summary.store_write_performed === false &&
    portfolio.summary.notification_sent === false;
}

function sdlcWorkbenchRowsMatchRuns(sdlcRuns, rows) {
  if (!Array.isArray(rows) || rows.length !== sdlcRuns.length) {
    return false;
  }
  const runIds = new Set(sdlcRuns.map((item) => sdlcRunRef(item)));
  const rowIds = new Set(rows.map((item) => item.run_id));
  return rowIds.size === rows.length &&
    runIds.size === sdlcRuns.length &&
    sdlcRuns.every((item) => rowIds.has(sdlcRunRef(item)));
}

function sdlcReporterMatchesRun(item, run) {
  if (
    !run ||
    item.command !== run.command ||
    item.governance_state !== run.adapter_status ||
    item.proof_source !== run.proof_source
  ) {
    return false;
  }
  const verified = sdlcProofVerified(run);
  if (verified) {
    return item.reporter_status === "active" &&
      item.credential_status === "active" &&
      item.source_signed === "active" &&
      item.identity_confidence === "verified_loaded";
  }
  return item.reporter_status !== "active" &&
    item.credential_status !== "active" &&
    item.source_signed !== "active" &&
    item.identity_confidence !== "verified_loaded";
}

function sdlcOutboxMatchesRun(item, run) {
  if (!run) {
    return false;
  }
  const verified = sdlcProofVerified(run);
  if (verified) {
    return item.outbox_status === "healthy" &&
      item.sequence_state === "healthy" &&
      item.pending_events === "0" &&
      item.oldest_pending_age === "0 分钟";
  }
  return item.outbox_status !== "healthy" &&
    item.sequence_state !== "healthy" &&
    item.pending_events !== "0" &&
    item.oldest_pending_age !== "0 分钟" &&
    /不提升证据等级/.test(item.evidence_impact || "");
}

function sdlcEligibilityMatchesRun(item, run) {
  if (!run) {
    return false;
  }
  const verified = sdlcProofVerified(run);
  if (verified) {
    return item.evidence_level === "L5" &&
      item.l5_result === "healthy" &&
      item.failed_conditions === "无" &&
      item.governance_loaded === "verified_loaded" &&
      item.outbox_delivered === "healthy";
  }
  return item.evidence_level !== "L5" &&
    item.l5_result !== "healthy" &&
    item.failed_conditions !== "无" &&
    item.governance_loaded !== "verified_loaded" &&
    item.outbox_delivered !== "healthy";
}

function sdlcConnectorProofStateIsSafe(consoleData, workbench) {
  const health = (workbench.health || []).find((item) => item.connector_id === "conn_sdlc");
  if (!health) {
    return false;
  }
  const summaryStatus = consoleData.summary?.adapter?.status;
  const sdlcProofs = consoleData.sdlcRuns || [];
  const verifiedProof = summaryStatus === "verified_loaded" &&
    sdlcProofs.length > 0 &&
    sdlcProofs.every((item) => proofStateIsSafe(item) && item.verified_loaded === "verified_loaded");
  if (verifiedProof) {
    return true;
  }
  return health.status === "materialized" &&
    health.freshness_state === "materialized" &&
    health.primary_action === "补齐治理加载证明" &&
    /不构成 verified_loaded/.test(health.evidence_impact || "");
}

export function containsUnsafeAuditReference(value) {
  const forbiddenKeys = new Set([
    "raw_payload",
    "download_url",
    "raw_url",
    "original_url",
    "raw_access_url",
    "code_snippet",
    "source_code",
    "patch",
    "diff",
    "diff_content",
    "pr_body",
    "pull_request_body"
  ]);
  if (typeof value === "string") {
    return /https?:\/\//i.test(value);
  }
  if (Array.isArray(value)) {
    return value.some(containsUnsafeAuditReference);
  }
  if (value && typeof value === "object") {
    const compactForbiddenKeys = new Set([
      "rawpayload",
      "downloadurl",
      "rawurl",
      "originalurl",
      "rawaccessurl",
      "codesnippet",
      "sourcecode",
      "patch",
      "diff",
      "diffcontent",
      "prbody",
      "pullrequestbody"
    ]);
    return Object.keys(value).some((key) => {
      const normalizedKey = key.replace(/[_\-\s]/g, "").toLowerCase();
      return forbiddenKeys.has(key) ||
        compactForbiddenKeys.has(normalizedKey) ||
        /^code/i.test(key) ||
        /snippet/i.test(key) ||
        /^diff/i.test(key) ||
        /patch/i.test(key) ||
        /^pullrequest/i.test(normalizedKey);
    }) ||
      Object.values(value).some(containsUnsafeAuditReference);
  }
  return false;
}

export function adoptionInsightsAreComplete(consoleData) {
  const adoption = consoleData.adoption;
  if (!adoption || containsUnsafeAuditReference(adoption)) {
    return false;
  }
  if (!keysAreExactly(adoption, ["metrics", "explanationChains", "segments", "reviewSignals", "guardrails"])) {
    return false;
  }
  if (!keysAreExactly(adoption.metrics, [
    "generated_lines",
    "retained_lines",
    "human_modified_lines",
    "deleted_lines",
    "rework_rounds",
    "pr_review_findings",
    "ci_failure_types",
    "retention_rate"
  ])) {
    return false;
  }
  const metricKeys = [
    "generated_lines",
    "retained_lines",
    "human_modified_lines",
    "deleted_lines",
    "rework_rounds",
    "pr_review_findings",
    "ci_failure_types"
  ];
  if (!metricKeys.every((key) => Object.prototype.hasOwnProperty.call(adoption.metrics, key))) {
    return false;
  }
  if (!Array.isArray(adoption.metrics.ci_failure_types)) {
    return false;
  }
  for (const key of metricKeys.filter((item) => item !== "ci_failure_types")) {
    if (typeof adoption.metrics[key] !== "number") {
      return false;
    }
  }
  const chainsOk = adoption.explanationChains.every((chain) =>
    keysAreExactly(chain, [
      "id",
      "signal_id",
      "category",
      "status",
      "score",
      "score_template_id",
      "evidence_level",
      "confidence",
      "missing_evidence",
      "explanation",
      "appeal_path",
      "lifecycle_guardrail"
    ]) &&
    chain.id &&
    chain.score_template_id &&
    chain.evidence_level &&
    typeof chain.confidence === "number" &&
    Array.isArray(chain.missing_evidence) &&
    chain.explanation &&
    chain.appeal_path &&
    /低置信不自动下架/.test(chain.lifecycle_guardrail || "") &&
    !containsUnsafeLifecycleText(chain.lifecycle_guardrail || "")
  );
  const reviewSignalsOk = adoption.reviewSignals.every((signal) =>
    keysAreExactly(signal, ["id", "title", "status", "owner", "evidence_ref", "reason", "action"]) &&
    signal.id &&
    signal.title &&
    signal.status &&
    signal.owner &&
    signal.reason &&
    ["发起人工复核", "补充风险处置证明"].includes(signal.action) &&
    !containsUnsafeLifecycleText(signal.reason || "") &&
    !/自动下架|自动降推荐|写回 Agent Store|发布|合并|批准|撤销|执行/.test(signal.action || "")
  );
  const segmentsOk = adoption.segments.every((segment) =>
    keysAreExactly(segment, ["id", "title", "status", "retention_rate", "affected_agents", "owner", "next_review"]) &&
    segment.id &&
    segment.title &&
    segment.status &&
    segment.owner
  );
  const guardrailsText = adoption.guardrails.join(" ");
  return chainsOk &&
    segmentsOk &&
    reviewSignalsOk &&
    /低置信不自动下架/.test(guardrailsText) &&
    !containsUnsafeLifecycleText(guardrailsText);
}

export function qualitySignalsAreSafe(consoleData) {
  const allowedQualityKeys = ["id", "signal_id", "category", "status", "score", "evidence_ref", "owner_hint", "primary_action"];
  return (consoleData.quality || []).every((item) =>
    keysAreSubset(item, allowedQualityKeys) &&
    !containsUnsafeAuditReference(item) &&
    !containsUnsafeLifecycleText(item.primary_action || "")
  );
}

export function containsUnsafeLifecycleText(value) {
  if (typeof value === "string") {
    const normalized = value.replace(/[\s\p{P}\p{S}]+/gu, "");
    const redlineRemoved = normalized
      .replace(/低置信不自动下架/g, "")
      .replace(/不自动(?:下架|降推荐|写回AgentStore|写回|发布|合并|批准|撤销|执行)/g, "")
      .replace(/不自动下架/g, "")
      .replace(/不自动降推荐/g, "")
      .replace(/不触发自动生命周期动作/g, "")
      .replace(/不执行自动生命周期动作/g, "")
      .replace(/不写回AgentStore/g, "")
      .replace(/不写AgentStore/g, "");
    return /自动(?:下架|降推荐|写回|发布|合并|批准|撤销|执行)|写回AgentStore/.test(redlineRemoved);
  }
  if (Array.isArray(value)) {
    return value.some(containsUnsafeLifecycleText);
  }
  if (value && typeof value === "object") {
    return Object.values(value).some(containsUnsafeLifecycleText);
  }
  return false;
}

function keysAreExactly(value, allowedKeys) {
  return isRecord(value) &&
    keysAreSubset(value, allowedKeys) &&
    allowedKeys.every((key) => Object.prototype.hasOwnProperty.call(value, key));
}

function keysAreSubset(value, allowedKeys) {
  if (!isRecord(value)) {
    return false;
  }
  const allowed = new Set(allowedKeys);
  return Object.keys(value).every((key) => allowed.has(key));
}

export function verifiedLoadedProofIsSafe(consoleData) {
  const adapterProofSafe = proofStateIsSafe({
    verified_loaded: consoleData.summary?.adapter?.status,
    proof_source: consoleData.summary?.adapter?.proof_source,
    captured_at: consoleData.summary?.adapter?.captured_at
  });
  const runProofsSafe = (consoleData.sdlcRuns || []).every(proofStateIsSafe);
  return adapterProofSafe && runProofsSafe;
}

export function proofStateIsSafe(proofState) {
  if (proofState.verified_loaded !== "verified_loaded") {
    return true;
  }
  const proofText = `${proofState.proof_source || ""} ${proofState.captured_at || ""}`;
  const proofPending = /待采集|待接入|CLI 预演|AGENTS\.md/.test(proofText);
  return Boolean(proofState.proof_source && proofState.captured_at && !proofPending);
}

export async function loadAgentOpsSnapshot(fetchImpl = fetch, baseUrl = apiBaseUrl(), timeoutMs = SNAPSHOT_TIMEOUT_MS) {
  const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
  const timeoutId = controller
    ? setTimeout(() => controller.abort(), timeoutMs)
    : null;
  try {
    const response = await fetchImpl(`${baseUrl}/v1/console/snapshot`, {
      headers: { Accept: "application/json" },
      signal: controller?.signal
    });
    if (!response.ok) {
      return fallbackSnapshot("后端快照请求失败，已切换到本地安全样例。");
    }

    const snapshot = await response.json();
    if (!validateSnapshot(snapshot)) {
      return fallbackSnapshot("后端快照结构不符合契约，已切换到本地安全样例。");
    }

    return apiSnapshot(snapshot);
  } catch (error) {
    if (error?.name === "AbortError") {
      return fallbackSnapshot("连接 AgentOps API 超时，已切换到本地安全样例。");
    }
    return fallbackSnapshot("无法连接 AgentOps API，已切换到本地安全样例。");
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  }
}

export function initialSnapshot() {
  return {
    source: "loading",
    sourceState: {
      status: "pending",
      label: "正在连接后端快照",
      copy: "正在读取 AgentOps API，页面会在失败时自动使用本地安全样例。",
      generatedAt: "连接中",
      sourceType: "等待后端",
      sourceSummary: "尚未取得后端生成结果。",
      request_id: "req_console_snapshot_loading",
      primary_action: "等待连接"
    },
    routes: mockRoutes,
    consoleData: consoleDataWithWorkbenchDefaults(mockConsoleData)
  };
}
