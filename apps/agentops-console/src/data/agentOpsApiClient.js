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
    consoleData: snapshot.consoleData
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

  const requiredKeys = [
    "summary",
    "runs",
    "evidence",
    "approvals",
    "policies",
    "quality",
    "risks",
    "agentStore",
    "connectors",
    "sdlcRuns"
  ];
  if (!requiredKeys.every((key) => Object.prototype.hasOwnProperty.call(snapshot.consoleData, key))) {
    return false;
  }
  if (!snapshotShapeIsSafe(snapshot.consoleData)) {
    return false;
  }
  if (containsForbiddenKey(snapshot, "raw_payload")) {
    return false;
  }
  return statesAreKnown(snapshot.consoleData) && verifiedLoadedProofIsSafe(snapshot.consoleData);
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
    return Array.isArray(consoleData[key]);
  });
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
    ...(consoleData.agentStore?.discoveryGaps || []).map((item) => item.state),
    ...(consoleData.agentStore?.runAudits || []).flatMap((item) => [item.registration_state, item.raw_access_state]),
    ...(consoleData.agentStore?.storeSummaries || []).flatMap((item) => [item.metadata_state, item.risk_state]),
    ...(consoleData.agentStore?.registryMap || []).map((item) => item.metadata_state),
    ...(consoleData.connectors || []).map((item) => item.status),
    ...(consoleData.sdlcRuns || []).flatMap((item) => [item.adapter_status, item.dry_run_status, item.verified_loaded])
  ].filter(Boolean);

  return candidates.every((state) => allowedStates.has(state));
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
