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
  if (Object.prototype.hasOwnProperty.call(withAdoption, "evidenceVault")) {
    return withAdoption;
  }
  return {
    ...withAdoption,
    evidenceVault: emptyEvidenceVault()
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
  const evidenceById = new Map((consoleData.evidence || []).map((item) => [item.evidence_id, item]));

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
