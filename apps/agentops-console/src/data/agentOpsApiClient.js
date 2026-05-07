import { consoleData as mockConsoleData, routes as mockRoutes } from "./mockAgentOpsData.js";

export const SNAPSHOT_SCHEMA_VERSION = "agentops.console.snapshot.v1";
export const SNAPSHOT_TIMEOUT_MS = 3000;

const allowedStates = new Set([
  "healthy",
  "allow",
  "conditional_allow",
  "warn",
  "approval_required",
  "block",
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
  "warning"
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
  consoleData: {
    ...mockConsoleData,
    summary: {
      ...mockConsoleData.summary,
      adapter: {
        ...mockConsoleData.summary.adapter,
        copy: "后端快照不可用；当前展示本地安全样例。"
      }
    }
  }
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
    "operationCenter",
    "evidenceVault",
    "approvalWorkbench",
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
  if (!actionDetailsAreComplete(consoleData)) {
    return false;
  }
  if (!evidenceVaultIsComplete(consoleData)) {
    return false;
  }
  if (!approvalWorkbenchIsComplete(consoleData)) {
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
  if (Object.prototype.hasOwnProperty.call(withEvidenceVault, "approvalWorkbench")) {
    return withEvidenceVault;
  }
  return {
    ...withEvidenceVault,
    approvalWorkbench: legacyApprovalWorkbench(withEvidenceVault.approvals)
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
    "operationCenter",
    "approvalWorkbench",
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
    return Array.isArray(consoleData[key]);
  }) &&
    consoleDataHasAdoptionShape(consoleData) &&
    consoleDataHasEvidenceVaultShape(consoleData);
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

export function statesAreKnown(consoleData) {
  const candidates = [
    consoleData.summary?.adapter?.status,
    ...(consoleData.summary?.metrics || []).map((item) => item.status),
    ...(consoleData.runs || []).flatMap((item) => [item.l5_state, item.policy_state, item.evidence_state]),
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
    consoleData: mockConsoleData
  };
}
