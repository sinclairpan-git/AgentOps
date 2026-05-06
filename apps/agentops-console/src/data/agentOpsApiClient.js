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
  "unverified"
]);

const requiredRouteIds = [
  "overview",
  "runs",
  "evidence",
  "approvals",
  "policies",
  "quality",
  "risks",
  "connectors",
  "sdlc-runs"
];

const fallbackSnapshot = (reason) => ({
  source: "mock_fallback",
  sourceState: {
    status: "degraded",
    label: "后端快照不可用",
    copy: reason || "已切换到本地安全样例，当前内容不能作为真实运行事实。",
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

const apiSnapshot = (snapshot) => ({
  source: "api_snapshot",
  sourceState: {
    status: "healthy",
    label: "后端快照已连接",
    copy: "页面正在展示 AgentOps API 返回的治理快照。",
    request_id: "req_console_snapshot_live",
    primary_action: "刷新快照"
  },
  routes: snapshot.routes,
  consoleData: snapshot.consoleData
});

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
    "connectors",
    "sdlcRuns"
  ];
  return requiredCollections.every((key) => Array.isArray(consoleData[key]));
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
      request_id: "req_console_snapshot_loading",
      primary_action: "等待连接"
    },
    routes: mockRoutes,
    consoleData: mockConsoleData
  };
}
