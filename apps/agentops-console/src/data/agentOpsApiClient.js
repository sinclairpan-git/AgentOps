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
    consoleData: consoleDataWithAdoptionDefault(snapshot.consoleData)
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

  const consoleData = consoleDataWithAdoptionDefault(snapshot.consoleData);
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

function consoleDataWithAdoptionDefault(consoleData) {
  if (!isRecord(consoleData)) {
    return consoleData;
  }
  if (Object.prototype.hasOwnProperty.call(consoleData, "adoption")) {
    return consoleData;
  }
  return {
    ...consoleData,
    adoption: emptyAdoptionInsights()
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
    isRecord(consoleData.adoption) &&
    isRecord(consoleData.adoption.metrics) &&
    Array.isArray(consoleData.adoption.explanationChains) &&
    Array.isArray(consoleData.adoption.segments) &&
    Array.isArray(consoleData.adoption.reviewSignals) &&
    Array.isArray(consoleData.adoption.guardrails);
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
    return Object.keys(value).some((key) =>
      forbiddenKeys.has(key) ||
      /^code/i.test(key) ||
      /snippet/i.test(key) ||
      /^diff/i.test(key) ||
      /patch/i.test(key) ||
      /^pull_request/i.test(key)
    ) ||
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
    const normalized = value.replace(/\s+/g, "");
    const redlineRemoved = normalized
      .replace(/低置信不自动下架/g, "")
      .replace(/不自动下架/g, "")
      .replace(/不自动降推荐/g, "")
      .replace(/不触发自动生命周期动作/g, "")
      .replace(/不执行自动生命周期动作/g, "")
      .replace(/不写AgentStore/g, "");
    return /自动下架|自动降推荐|写回AgentStore|自动写回|发布|合并|批准|撤销|执行/.test(redlineRemoved);
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
