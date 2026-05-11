import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(root, "..", "..");

const readText = (path) => readFileSync(resolve(root, path), "utf8");
const readRepoText = (path) => readFileSync(resolve(repoRoot, path), "utf8");

const { consoleData } = await import(`file://${resolve(root, "src/data/mockAgentOpsData.js")}`);
const packageJson = JSON.parse(readText("package.json"));
const packageLock = readText("package-lock.json");
const indexSource = readText("index.html");
const viteConfigSource = readText("vite.config.js");
const providerSource = readText("src/provider/enterpriseVue2Provider.js");
const mainSource = readText("src/main.js");
const appSource = readText("src/App.js");
const appShellSource = readText("src/components/AppShell.js");
const statusBadgeSource = readText("src/components/StatusBadge.js");
const dataTableSource = readText("src/components/DataTable.js");
const mockDataSource = readText("src/data/mockAgentOpsData.js");
const apiClientSource = readText("src/data/agentOpsApiClient.js");
const viewSources = [
  "src/views/OverviewView.js",
  "src/views/RunsView.js",
  "src/views/EvidenceExplorerView.js",
  "src/views/ApprovalCenterView.js",
  "src/views/PolicyCenterView.js",
  "src/views/QualityCenterView.js",
  "src/views/RiskTriageView.js",
  "src/views/AgentStoreAuditView.js",
  "src/views/CredentialHandoffView.js",
  "src/views/ConnectorStatusView.js",
  "src/views/SdlcRunsView.js"
].map(readText).join("\n");
const uiSource = `${appSource}\n${appShellSource}\n${statusBadgeSource}\n${dataTableSource}\n${mockDataSource}\n${apiClientSource}\n${viewSources}`;
const techStack = readRepoText(".ai-sdlc/profiles/tech-stack.yml");
const {
  loadAgentOpsSnapshot,
  qualityCenterWorkbenchIsComplete,
  validateSnapshot
} = await import(`file://${resolve(root, "src/data/agentOpsApiClient.js")}`);

const vendoredDependencies = {
  "@sxf/er-components": "sxf-er-components-1.27.5.tgz",
  "@sxf/er-config": "sxf-er-config-1.4.0.tgz",
  "@sxf/er-feature": "sxf-er-feature-0.1.0.tgz",
  "@sxf/er-lib": "sxf-er-lib-1.0.0.tgz",
  "@sxf/er-style": "sxf-er-style-1.2.1.tgz",
  "@sxf/er-utils": "sxf-er-utils-1.4.0.tgz",
  "@sxf/er-validator": "sxf-er-validator-1.2.0.tgz",
  "@sxf/er-widget": "sxf-er-widget-1.15.2.tgz",
  "@sxf/intl": "sxf-intl-2.5.3.tgz",
  "@sxf/jquery": "sxf-jquery-1.0.6.tgz",
  "@sxf/sf-theme": "sxf-sf-theme-0.2.5.tgz",
  "@sxf/vtv-icon": "sxf-vtv-icon-1.0.272.tgz",
  "@sxf/vue-intl": "sxf-vue-intl-1.11.4.tgz",
  "@uedc/sf-layout": "uedc-sf-layout-1.15.0.tgz",
  jquery: "sxf-jquery-1.0.6.tgz"
};

for (const [dependencyName, tarballName] of Object.entries(vendoredDependencies)) {
  const expectedSpec = `file:../../vendor/enterprise-vue2/${tarballName}`;
  assert.equal(packageJson.dependencies[dependencyName], expectedSpec, `${dependencyName} must use project-vendor tarball`);
  assert.ok(existsSync(resolve(repoRoot, "vendor/enterprise-vue2", tarballName)), `${tarballName} must exist`);
}

assert.match(providerSource, /allowFullVueUse:\s*false/);
assert.match(providerSource, /installedVersion:\s*"1\.27\.5"/);
assert.doesNotMatch(providerSource, /Vue\.use\(\s*ErComponents\s*\)/);
assert.doesNotMatch(mainSource, /Vue\.use\(\s*ErComponents\s*\)/);
assert.match(mainSource, /import Vue from "vue"/);
assert.match(viteConfigSource, /find:\s*\/\^vue\$\/,/);
assert.match(viteConfigSource, /vue\/dist\/vue\.esm\.js/);
assert.match(indexSource, /<link rel="icon" href="data:," \/>/);
assert.doesNotMatch(packageLock, /registry\.npmjs\.org\/@sxf|registry\.npmjs\.org\/@uedc|@sxf%2f|@uedc%2f|code\.sangfor|mq\.code\.sangfor/);
assert.match(apiClientSource, /agentops\.console\.snapshot\.v1/);
assert.match(apiClientSource, /\/v1\/console\/snapshot/);
assert.match(appSource, /loadAgentOpsSnapshot/);
assert.match(appSource, /refreshSnapshot/);
assert.match(appSource, /AgentStoreAuditView/);
assert.match(appSource, /CredentialHandoffView/);
assert.match(appShellSource, /sourceState/);
assert.match(appShellSource, /refresh-snapshot/);
assert.match(appShellSource, /else\s*\{\s*this\.\$emit\("close-action-detail"\);\s*\}/);
assert.match(viewSources, /actionId\(risk\)/);
assert.match(viewSources, /action_gap_/);
assert.match(uiSource, /后端快照/);

assert.match(techStack, /source:\s*project-vendor/);
assert.match(techStack, /path:\s*vendor\/enterprise-vue2\/sxf-er-components-1\.27\.5\.tgz/);

assert.ok(existsSync(resolve(root, "src/styles.css")), "src/styles.css must exist because src/main.js imports it");

for (const expectedChineseText of [
  "治理控制台",
  "当前视图",
  "全局搜索",
  "通知中心",
  "待办中心",
  "处置详情",
  "处置时间线",
  "审计包摘要",
  "Evidence Vault 访问工作台",
  "原文访问申请",
  "限时授权",
  "审计轨迹",
  "默认不展示原文",
  "人工审批与 Grant 工作台",
  "审批队列",
  "Grant 影响",
  "审批审计轨迹",
  "只读审批摘要",
  "不得作为唯一审批人",
  "补充材料",
  "建议动作",
  "前往相关页面",
  "关闭条件",
  "审计引用",
  "导出状态",
  "回显目标",
  "只读复核包",
  "建议动作，不在本页执行",
  "只读处置预案",
  "采纳概览",
  "质量中心工作台",
  "Agent 质量摘要",
  "评分器发布",
  "发布执行",
  "原质量信号",
  "质量解释链",
  "复核队列",
  "低置信不自动下架",
  "申诉路径",
  "总览",
  "运行记录",
  "证据检索",
  "审批中心",
  "策略中心",
  "质量中心",
  "风险处置",
  "Agent Store 审计",
  "凭证联调",
  "凭证状态回显",
  "签名测试通过",
  "已撤销",
  "重新签发凭证",
  "撤销原因",
  "Agent Store 只消费展示字段",
  "不得本地推导 active",
  "不等同“已验证加载”或 L5",
  "发现队列",
  "负责人",
  "影响运行",
  "运行审计",
  "注册映射",
  "回显摘要",
  "连接器状态",
  "连接器健康工作台",
  "运行时运行态",
  "轨迹摘要",
  "轨迹待补齐",
  "健康与限流",
  "DLQ 与 Outbox Replay",
  "同步轨迹",
  "新鲜度",
  "限流",
  "超过 20 分钟",
  "不构成 verified_loaded",
  "Ai_AutoSDLC 运行",
  "生成时间",
  "来源类型",
  "来源边界",
  "已生成配置",
  "脱敏失败"
]) {
  assert.ok(
    uiSource.includes(expectedChineseText),
    `${expectedChineseText} must be present in Chinese UI text`
  );
}

assert.ok(
  mockDataSource.includes('verified_loaded: "unverified"'),
  "mock data must not present verified_loaded as active without machine-verifiable proof"
);

const validApiSnapshot = {
  schema_version: "agentops.console.snapshot.v1",
  generated_at: "2026-05-06T00:00:00Z",
  source: "api_snapshot",
  routes: consoleData ? [
    { id: "overview", label: "总览", icon: "⌂" },
    { id: "runs", label: "运行记录", icon: "▶" },
    { id: "evidence", label: "证据检索", icon: "◇" },
    { id: "approvals", label: "审批中心", icon: "✓" },
    { id: "policies", label: "策略中心", icon: "!" },
    { id: "quality", label: "质量中心", icon: "质" },
    { id: "risks", label: "风险处置", icon: "△" },
    { id: "agent-store-audit", label: "Agent Store 审计", icon: "AS" },
    { id: "credential-handoff", label: "凭证联调", icon: "凭" },
    { id: "connectors", label: "连接器状态", icon: "∞" },
    { id: "sdlc-runs", label: "Ai_AutoSDLC 运行", icon: "SD" }
  ] : [],
  consoleData
};

assert.equal(validateSnapshot(validApiSnapshot), true);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      runs: [{
        ...consoleData.runs[0],
        runtime_status: "invented_runtime_state"
      }]
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      runs: consoleData.runs.map((run, index) =>
        index === 0 ? { ...run, runtime_status: "created" } : run
      )
    }
  }),
  true
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      runs: consoleData.runs.map((run, index) =>
        index === 0 ? {
          ...run,
          trace_timeline: run.trace_timeline.map((span, spanIndex) =>
            spanIndex === 0 ? { ...span, status_code: "waiting" } : span
          )
        } : run
      )
    }
  }),
  true
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      runs: [{
        ...consoleData.runs[0],
        trace_timeline: [{
          span_id: "span_unsafe",
          status_code: "ok",
          raw_input: "prompt text must not be exposed"
        }]
      }]
    }
  }),
  false
);
const healthyConnectorWarningRateLimit = {
  ...consoleData,
  connectors: consoleData.connectors.map((connector) =>
    connector.id === "conn_policy" ? {
      ...connector,
      status: "healthy",
      degrade_action: "本地内核策略摘要"
    } : connector
  ),
  connectorWorkbench: {
    ...consoleData.connectorWorkbench,
    health: consoleData.connectorWorkbench.health.map((item) =>
      item.connector_id === "conn_policy" ? {
        ...item,
        status: "healthy",
        freshness: "15 分钟内",
        freshness_state: "healthy",
        rate_limit_state: "warning",
        rate_limit_detail: "接近配额或依赖外部检查，按低频采集并保留摘要。",
        degrade_action: "本地内核策略摘要",
        evidence_impact: "证据等级不降低",
        primary_action: "保持监控",
        secondary_action: "按 SLO 继续采集心跳"
      } : item
    ),
    dlq: consoleData.connectorWorkbench.dlq.map((item) =>
      item.connector_id === "conn_policy" ? {
        ...item,
        dlq_depth: "0",
        oldest_event_age: "0 分钟",
        replay_state: "healthy",
        retry_window: "无需回放",
        degrade_policy: "无积压，继续按 15 分钟新鲜度 SLO 采集"
      } : item
    ),
    syncTrail: consoleData.connectorWorkbench.syncTrail.map((item) =>
      item.connector_id === "conn_policy" ? {
        ...item,
        stage: "同步",
        summary: "策略服务心跳正常，继续按新鲜度 SLO 采集。",
        status: "healthy"
      } : item
    )
  }
};
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: healthyConnectorWarningRateLimit
  }),
  true
);
const healthyConnectorDegradedRateLimitState = {
  ...healthyConnectorWarningRateLimit,
  connectorWorkbench: {
    ...healthyConnectorWarningRateLimit.connectorWorkbench,
    health: healthyConnectorWarningRateLimit.connectorWorkbench.health.map((item) =>
      item.connector_id === "conn_policy" ? {
        ...item,
        rate_limit_state: "degraded"
      } : item
    )
  }
};
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: healthyConnectorDegradedRateLimitState
  }),
  false
);
const verifiedSdlcRuns = consoleData.sdlcRuns.map((item) => ({
  ...item,
  adapter_status: "verified_loaded",
  proof_source: "governance-load-probe sha256:machine-proof",
  captured_at: "2026-05-07T10:30:00Z",
  verified_loaded: "verified_loaded"
}));
const verifiedSdlcRunWorkbench = {
  summary: {
    ...consoleData.sdlcRunWorkbench.summary,
    adapter_status: "verified_loaded",
    proof_state: "verified_loaded",
    reporter_ready: verifiedSdlcRuns.length,
    pending_proofs: 0,
    primary_action: "保持治理加载证明"
  },
  reporter: consoleData.sdlcRunWorkbench.reporter.map((item) => ({
    ...item,
    reporter_status: "active",
    credential_status: "active",
    source_signed: "active",
    identity_confidence: "verified_loaded",
    governance_state: "verified_loaded",
    proof_source: "governance-load-probe sha256:machine-proof",
    primary_action: "保持 Reporter 心跳"
  })),
  outbox: consoleData.sdlcRunWorkbench.outbox.map((item) => ({
    ...item,
    outbox_status: "healthy",
    sequence_state: "healthy",
    pending_events: "0",
    oldest_pending_age: "0 分钟",
    evidence_impact: "可进入 L5 复核"
  })),
  eligibility: consoleData.sdlcRunWorkbench.eligibility.map((item) => ({
    ...item,
    evidence_level: "L5",
    l5_result: "healthy",
    failed_conditions: "无",
    policy_state_known: "allow",
    governance_loaded: "verified_loaded",
    verification_fresh: "healthy",
    outbox_delivered: "healthy",
    next_action: "保持证据链"
  })),
  guardrails: consoleData.sdlcRunWorkbench.guardrails
};
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      summary: {
        ...consoleData.summary,
        adapter: {
          ...consoleData.summary.adapter,
          status: "verified_loaded",
          proof_source: "governance-load-probe sha256:machine-proof",
          captured_at: "2026-05-07T10:30:00Z"
        }
      },
      sdlcRuns: verifiedSdlcRuns,
      sdlcRunWorkbench: verifiedSdlcRunWorkbench
    }
  }),
  true
);
assert.equal(validateSnapshot({ ...validApiSnapshot, schema_version: "wrong" }), false);
assert.equal(
  validateSnapshot({ ...validApiSnapshot, routes: [{ id: "overview", label: "总览", icon: "⌂" }] }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, evidence: [{ raw_payload: "secret" }] }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, risks: null }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, agentStore: null }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, agentStore: { ...consoleData.agentStore, runAudits: null } }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, operationCenter: null }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, operationCenter: { ...consoleData.operationCenter, searchIndex: null } }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, actionWorkbench: null }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, actionWorkbench: { ...consoleData.actionWorkbench, details: null } }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, sdlcRunWorkbench: null }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, qualityCenterWorkbench: null }
  }),
  false
);
const legacyV1SnapshotWithoutAdoption = {
  ...validApiSnapshot,
  consoleData: { ...consoleData }
};
delete legacyV1SnapshotWithoutAdoption.consoleData.adoption;
assert.equal(
  validateSnapshot(legacyV1SnapshotWithoutAdoption),
  true
);
const legacyV1SnapshotWithoutEvidenceVault = {
  ...validApiSnapshot,
  consoleData: { ...consoleData }
};
delete legacyV1SnapshotWithoutEvidenceVault.consoleData.evidenceVault;
assert.equal(
  validateSnapshot(legacyV1SnapshotWithoutEvidenceVault),
  true
);
const legacyV1SnapshotWithoutApprovalWorkbench = {
  ...validApiSnapshot,
  consoleData: { ...consoleData }
};
delete legacyV1SnapshotWithoutApprovalWorkbench.consoleData.approvalWorkbench;
assert.equal(
  validateSnapshot(legacyV1SnapshotWithoutApprovalWorkbench),
  true
);
const legacyV1SnapshotWithoutConnectorWorkbench = {
  ...validApiSnapshot,
  consoleData: { ...consoleData }
};
delete legacyV1SnapshotWithoutConnectorWorkbench.consoleData.connectorWorkbench;
assert.equal(
  validateSnapshot(legacyV1SnapshotWithoutConnectorWorkbench),
  true
);
const legacyV1SnapshotWithoutSdlcRunWorkbench = {
  ...validApiSnapshot,
  consoleData: { ...consoleData }
};
delete legacyV1SnapshotWithoutSdlcRunWorkbench.consoleData.sdlcRunWorkbench;
assert.equal(
  validateSnapshot(legacyV1SnapshotWithoutSdlcRunWorkbench),
  true
);
const legacyV1SnapshotWithoutQualityCenterWorkbench = {
  ...validApiSnapshot,
  consoleData: { ...consoleData }
};
delete legacyV1SnapshotWithoutQualityCenterWorkbench.consoleData.qualityCenterWorkbench;
assert.equal(
  validateSnapshot(legacyV1SnapshotWithoutQualityCenterWorkbench),
  true
);
const legacyUnsafeSdlcRunSnapshot = {
  ...legacyV1SnapshotWithoutSdlcRunWorkbench,
  consoleData: {
    ...legacyV1SnapshotWithoutSdlcRunWorkbench.consoleData,
    sdlcRuns: legacyV1SnapshotWithoutSdlcRunWorkbench.consoleData.sdlcRuns.map((item) =>
      item.id === "sdlc_001" ? {
        ...item,
        raw_access_url: "/sdlc/raw/proof"
      } : item
    )
  }
};
assert.equal(
  validateSnapshot(legacyUnsafeSdlcRunSnapshot),
  false
);
const legacyV1SnapshotWithSmallConnectorSet = {
  ...validApiSnapshot,
  consoleData: {
    ...consoleData,
    connectors: consoleData.connectors.filter((connector) =>
      ["conn_agent_store", "conn_sdlc", "conn_evidence", "conn_policy", "conn_iam"].includes(connector.id)
    )
  }
};
delete legacyV1SnapshotWithSmallConnectorSet.consoleData.connectorWorkbench;
assert.equal(
  validateSnapshot(legacyV1SnapshotWithSmallConnectorSet),
  true
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      adoption: {
        ...consoleData.adoption,
        guardrails: [...consoleData.adoption.guardrails, "不执行自动生命周期动作。", "不自动写回 Agent Store。"],
        explanationChains: [{
          ...consoleData.adoption.explanationChains[0],
          category: "发布前质量门禁",
          explanation: "发布前质量门禁仅展示摘要判断。"
        }],
        reviewSignals: [{
          ...consoleData.adoption.reviewSignals[0],
          reason: "执行人工复核，不触发自动生命周期动作。"
        }]
      }
    }
  }),
  true
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, adoption: null }
  }),
  false
);
const pendingApprovalWithActiveGrant = {
  ...consoleData,
  approvals: consoleData.approvals.map((approval) =>
    approval.approval_id === "ap_001" ? { ...approval, grant_status: "active" } : approval
  ),
  approvalWorkbench: {
    ...consoleData.approvalWorkbench,
    grants: consoleData.approvalWorkbench.grants.map((grant) =>
      grant.approval_id === "ap_001" ? {
        ...grant,
        grant_status: "active",
        ttl_summary: "15 分钟限时 Grant",
        expires_at: "快照生成后 15 分钟",
        revocation_state: "未撤销，仍需按资源范围和授权时限消费"
      } : grant
    )
  }
};
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: pendingApprovalWithActiveGrant
  }),
  false
);
const pendingApprovalWithNormalizedGrant = {
  ...consoleData,
  approvals: consoleData.approvals.map((approval) =>
    approval.approval_id === "ap_001" ? { ...approval, grant_status: "active" } : approval
  )
};
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: pendingApprovalWithNormalizedGrant
  }),
  true
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, evidenceVault: null }
  }),
  false
);
const sdlcSummarySpoofedVerifiedLoaded = {
  ...consoleData,
  sdlcRunWorkbench: {
    ...consoleData.sdlcRunWorkbench,
    summary: {
      ...consoleData.sdlcRunWorkbench.summary,
      proof_state: "verified_loaded"
    }
  }
};
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: sdlcSummarySpoofedVerifiedLoaded
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      credentialHandoff: {
        ...consoleData.credentialHandoff,
        sessions: consoleData.credentialHandoff.sessions.map((item) =>
          item.bootstrap_id === "boot-inst-fixture" ? { ...item, token_id: "token-inst-fixture" } : item
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      credentialHandoff: {
        ...consoleData.credentialHandoff,
        sessions: consoleData.credentialHandoff.sessions.map((item) =>
          item.bootstrap_id === "boot-inst-fixture" ? { ...item, signature: "sig-fixture" } : item
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      credentialHandoff: {
        ...consoleData.credentialHandoff,
        summary: {
          ...consoleData.credentialHandoff.summary,
          revoked: 0
        }
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      credentialHandoff: {
        ...consoleData.credentialHandoff,
        sessions: consoleData.credentialHandoff.sessions.map((item) =>
          item.bootstrap_status === "revoked" ? {
            ...item,
            next_action: "display_activation_result"
          } : item
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      credentialHandoff: {
        ...consoleData.credentialHandoff,
        sessions: consoleData.credentialHandoff.sessions.map((item) =>
          item.bootstrap_status !== "revoked" ? {
            ...item,
            revocation_id: "revoke-spoof"
          } : item
        )
      }
    }
  }),
  false
);
const sdlcDryRunStateSpoofedPassed = {
  ...consoleData,
  sdlcRuns: consoleData.sdlcRuns.map((item) =>
    item.id === "sdlc_001" ? { ...item, dry_run_status: "pending" } : item
  ),
  sdlcRunWorkbench: {
    ...consoleData.sdlcRunWorkbench,
    summary: {
      ...consoleData.sdlcRunWorkbench.summary,
      dry_run_state: "dry_run_passed"
    }
  }
};
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: sdlcDryRunStateSpoofedPassed
  }),
  false
);
const sdlcReporterProofSourceSpoofed = {
  ...consoleData,
  sdlcRunWorkbench: {
    ...consoleData.sdlcRunWorkbench,
    reporter: consoleData.sdlcRunWorkbench.reporter.map((item) =>
      item.run_id === "sdlc_001" ? {
        ...item,
        proof_source: "伪造治理加载证明"
      } : item
    )
  }
};
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: sdlcReporterProofSourceSpoofed
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, approvalWorkbench: null }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, connectorWorkbench: null }
  }),
  false
);
const legacyUnsafeConnectorSnapshot = {
  ...validApiSnapshot,
  consoleData: {
    ...consoleData,
    connectors: legacyV1SnapshotWithSmallConnectorSet.consoleData.connectors.map((connector) =>
      connector.id === "conn_sdlc" ? { ...connector, raw_access_url: "/connectors/raw/conn_sdlc" } : connector
    )
  }
};
delete legacyUnsafeConnectorSnapshot.consoleData.connectorWorkbench;
assert.equal(
  validateSnapshot(legacyUnsafeConnectorSnapshot),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      evidenceVault: {
        ...consoleData.evidenceVault,
        requests: [],
        grants: [],
        auditTrail: []
      }
    }
  }),
  false
);
const sdlcSpoofedHealthyConnector = {
  ...consoleData,
  connectors: consoleData.connectors.map((connector) =>
    connector.id === "conn_sdlc" ? {
      ...connector,
      status: "healthy",
      last_seen_at: "2026-05-05 18:49",
      degrade_action: "无"
    } : connector
  ),
  connectorWorkbench: {
    ...consoleData.connectorWorkbench,
    health: consoleData.connectorWorkbench.health.map((item) =>
      item.connector_id === "conn_sdlc" ? {
        ...item,
        status: "healthy",
        last_seen_at: "2026-05-05 18:49",
        freshness: "15 分钟内",
        freshness_state: "healthy",
        rate_limit_state: "healthy",
        rate_limit_detail: "未触发限流，按连接器新鲜度 SLO 采集。",
        degrade_action: "无",
        evidence_impact: "证据等级不降低",
        primary_action: "保持监控",
        secondary_action: "按 SLO 继续采集心跳"
      } : item
    ),
    dlq: consoleData.connectorWorkbench.dlq.map((item) =>
      item.connector_id === "conn_sdlc" ? {
        ...item,
        dlq_depth: "0",
        oldest_event_age: "0 分钟",
        replay_state: "healthy",
        retry_window: "无需回放",
        degrade_policy: "无积压，继续按 15 分钟新鲜度 SLO 采集"
      } : item
    ),
    syncTrail: consoleData.connectorWorkbench.syncTrail.map((item) =>
      item.connector_id === "conn_sdlc" ? {
        ...item,
        stage: "同步",
        occurred_at: "2026-05-05 18:49",
        summary: "Ai_AutoSDLC 心跳正常，继续按新鲜度 SLO 采集。",
        status: "healthy"
      } : item
    )
  }
};
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: sdlcSpoofedHealthyConnector
  }),
  false
);
const missingExternalConnectorBoundary = {
  ...consoleData,
  connectors: consoleData.connectors.filter((connector) => connector.id !== "conn_git"),
  connectorWorkbench: {
    ...consoleData.connectorWorkbench,
    health: consoleData.connectorWorkbench.health.filter((item) => item.connector_id !== "conn_git"),
    dlq: consoleData.connectorWorkbench.dlq.filter((item) => item.connector_id !== "conn_git"),
    syncTrail: consoleData.connectorWorkbench.syncTrail.filter((item) => item.connector_id !== "conn_git")
  }
};
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: missingExternalConnectorBoundary
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      connectorWorkbench: {
        ...consoleData.connectorWorkbench,
        health: consoleData.connectorWorkbench.health.map((item) =>
          item.connector_id === "conn_ci" ? {
            ...item,
            rate_limit_state: "healthy"
          } : item
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      approvalWorkbench: {
        ...consoleData.approvalWorkbench,
        queues: [],
        grants: [],
        auditTrail: []
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      connectorWorkbench: {
        ...consoleData.connectorWorkbench,
        health: [],
        dlq: [],
        syncTrail: []
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      connectorWorkbench: {
        ...consoleData.connectorWorkbench,
        dlq: consoleData.connectorWorkbench.dlq.map((item) =>
          item.connector_id === "conn_ci" ? {
            ...item,
            oldest_event_age: "0 分钟"
          } : item
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      connectorWorkbench: {
        ...consoleData.connectorWorkbench,
        health: consoleData.connectorWorkbench.health.map((item) =>
          item.connector_id === "conn_sdlc" ? {
            ...item,
            status: "healthy",
            freshness_state: "healthy",
            evidence_impact: "证据等级不降低",
            primary_action: "保持监控"
          } : item
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      connectorWorkbench: {
        ...consoleData.connectorWorkbench,
        dlq: consoleData.connectorWorkbench.dlq.map((item) =>
          item.connector_id === "conn_policy" ? {
            ...item,
            dlq_depth: "0",
            replay_state: "healthy",
            retry_window: "无需回放",
            degrade_policy: "无积压，继续按 15 分钟新鲜度 SLO 采集"
          } : item
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      connectorWorkbench: {
        ...consoleData.connectorWorkbench,
        health: [{
          ...consoleData.connectorWorkbench.health[0],
          raw_access_url: "/connectors/raw/conn_agent_store"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      connectorWorkbench: {
        ...consoleData.connectorWorkbench,
        syncTrail: [{
          ...consoleData.connectorWorkbench.syncTrail[0],
          summary: "查看 https://example.invalid/connector"
        }]
      }
    }
  }),
  false
);
const degradedEvidence = {
  ...consoleData.evidence[0],
  evidence_id: "ev_degraded_001",
  id: "ev_degraded_001",
  run_id: "run_degraded_001",
  raw_access_state: "degraded",
  audit_id: "audit_degraded_001",
  summary: "运行降级，仅展示摘要和哈希。",
  denied_scope: ""
};
const degradedConsoleData = {
  ...consoleData,
  evidence: [degradedEvidence],
  evidenceVault: {
    ...consoleData.evidenceVault,
    requests: [{
      id: "vault_req_ev_degraded_001",
      evidence_id: "ev_degraded_001",
      run_id: "run_degraded_001",
      requester: "证据负责人",
      reason: "运行降级，需先补齐 L5/治理证据后再申请原文访问。",
      status: "pending",
      denied_scope: "",
      audit_id: "audit_degraded_001",
      ttl_summary: "待补偿",
      primary_action: "等待审批",
      safety_note: "仅记录原文访问申请摘要，不展示 Evidence Vault 原文。"
    }],
    grants: [{
      id: "vault_grant_ev_degraded_001",
      evidence_id: "ev_degraded_001",
      requester: "证据负责人",
      status: "pending",
      scope: "待补偿范围",
      expires_at: "待补偿",
      audit_id: "audit_degraded_001",
      consumption_policy: "只读复核窗口内可查看授权记录；不提供原文下载。"
    }],
    auditTrail: [{
      id: "vault_audit_ev_degraded_001",
      evidence_id: "ev_degraded_001",
      stage: "降级",
      occurred_at: "快照生成时",
      summary: "运行降级，原文访问保持待审批，仅展示摘要和哈希。",
      owner: "证据负责人",
      status: "degraded",
      audit_id: "audit_degraded_001"
    }]
  }
};
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: degradedConsoleData
  }),
  true
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...degradedConsoleData,
      evidenceVault: {
        ...degradedConsoleData.evidenceVault,
        grants: [{
          ...degradedConsoleData.evidenceVault.grants[0],
          status: "active",
          scope: "限定复核字段",
          expires_at: "快照生成后 15 分钟"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      approvalWorkbench: {
        ...consoleData.approvalWorkbench,
        queues: consoleData.approvalWorkbench.queues.map((queue) =>
          queue.approval_id === "ap_001" ? { ...queue, status: "approved", primary_action: "查看审批记录" } : queue
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      approvalWorkbench: {
        ...consoleData.approvalWorkbench,
        grants: consoleData.approvalWorkbench.grants.map((grant) =>
          grant.approval_id === "ap_001" ? {
            ...grant,
            grant_status: "active",
            ttl_summary: "15 分钟限时 Grant",
            expires_at: "快照生成后 15 分钟"
          } : grant
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      approvalWorkbench: {
        ...consoleData.approvalWorkbench,
        auditTrail: [{
          ...consoleData.approvalWorkbench.auditTrail[0],
          raw_access_url: "/approval/raw/ap_001"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      approvalWorkbench: {
        ...consoleData.approvalWorkbench,
        guardrails: [...consoleData.approvalWorkbench.guardrails, "自动批准审批"]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...degradedConsoleData,
      evidenceVault: {
        ...degradedConsoleData.evidenceVault,
        requests: [{
          ...degradedConsoleData.evidenceVault.requests[0],
          primary_action: "申请原文访问",
          ttl_summary: "待审批"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      evidenceVault: {
        ...consoleData.evidenceVault,
        requests: consoleData.evidenceVault.requests.map((request) =>
          request.evidence_id === "ev_004" ? { ...request, status: "approved" } : request
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      evidenceVault: {
        ...consoleData.evidenceVault,
        grants: consoleData.evidenceVault.grants.map((grant) =>
          grant.evidence_id === "ev_004" ? { ...grant, status: "active", expires_at: "快照生成后 15 分钟" } : grant
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      evidenceVault: {
        ...consoleData.evidenceVault,
        requests: consoleData.evidenceVault.requests.map((request) =>
          request.evidence_id === "ev_003" ? { ...request, status: "approved" } : request
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      evidenceVault: {
        ...consoleData.evidenceVault,
        grants: consoleData.evidenceVault.grants.map((grant) =>
          grant.evidence_id === "ev_003" ? { ...grant, status: "active", expires_at: "快照生成后 15 分钟" } : grant
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      evidenceVault: {
        ...consoleData.evidenceVault,
        requests: consoleData.evidenceVault.requests.map((request) =>
          request.evidence_id === "ev_004" ? { ...request, primary_action: "申请原文访问", ttl_summary: "待审批" } : request
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      evidenceVault: {
        ...consoleData.evidenceVault,
        requests: [{
          ...consoleData.evidenceVault.requests[0],
          raw_access_url: "/vault/raw/ev_001"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      evidenceVault: {
        ...consoleData.evidenceVault,
        grants: [{
          ...consoleData.evidenceVault.grants[0],
          download_url: "/vault/download"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      evidenceVault: {
        ...consoleData.evidenceVault,
        auditTrail: [{
          ...consoleData.evidenceVault.auditTrail[0],
          summary: "查看 https://example.invalid/raw"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      evidenceVault: {
        ...consoleData.evidenceVault,
        requests: [{
          ...consoleData.evidenceVault.requests[0],
          pullRequestBody: "PR 原文"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      evidenceVault: {
        ...consoleData.evidenceVault,
        guardrails: [...consoleData.evidenceVault.guardrails, "自动批准原文访问"]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      adoption: {
        ...consoleData.adoption,
        reviewSignals: [{
          ...consoleData.adoption.reviewSignals[0],
          reason: "低置信后自动-下架"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      quality: [{
        ...consoleData.quality[0],
        primary_action: "自动-批准"
      }]
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      adoption: {
        ...consoleData.adoption,
        metrics: { ...consoleData.adoption.metrics, generated_lines: undefined }
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      actionWorkbench: {
        ...consoleData.actionWorkbench,
        details: [{
          ...consoleData.actionWorkbench.details[0],
          pullRequestBody: "PR 原文"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      quality: [{
        ...consoleData.quality[0],
        primary_action: "写回AgentStore"
      }]
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      quality: [{
        ...consoleData.quality[0],
        primary_action: "自动写回"
      }]
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      adoption: {
        ...consoleData.adoption,
        guardrails: [...consoleData.adoption.guardrails, "自动下架低质量 Agent"]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      adoption: {
        ...consoleData.adoption,
        reviewSignals: [{
          ...consoleData.adoption.reviewSignals[0],
          reason: "低置信后自动下架"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      adoption: {
        ...consoleData.adoption,
        explanationChains: [{
          ...consoleData.adoption.explanationChains[0],
          lifecycle_guardrail: "低置信不自动下架；自动降推荐低质量 Agent"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      adoption: {
        ...consoleData.adoption,
        metrics: {
          ...consoleData.adoption.metrics,
          code_snippet: "secret"
        }
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      adoption: {
        ...consoleData.adoption,
        reviewSignals: [{
          ...consoleData.adoption.reviewSignals[0],
          pr_body: "PR 原文"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      adoption: {
        ...consoleData.adoption,
        explanationChains: [{
          ...consoleData.adoption.explanationChains[0],
          missing_evidence: null
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      adoption: {
        ...consoleData.adoption,
        explanationChains: [{
          ...consoleData.adoption.explanationChains[0],
          explanation: "查看 https://example.invalid/pr-diff"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      adoption: {
        ...consoleData.adoption,
        reviewSignals: [{
          ...consoleData.adoption.reviewSignals[0],
          action: "自动下架"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      adoption: {
        ...consoleData.adoption,
        reviewSignals: [{
          ...consoleData.adoption.reviewSignals[0],
          action: "写回 Agent Store"
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      quality: [{
        ...consoleData.quality[0],
        evidence_ref: "https://example.invalid/pr"
      }]
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      quality: [{
        ...consoleData.quality[0],
        diff_content: "PR 原文"
      }]
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      actionWorkbench: {
        ...consoleData.actionWorkbench,
        details: [{
          ...consoleData.actionWorkbench.details[0],
          timeline: null
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      actionWorkbench: {
        ...consoleData.actionWorkbench,
        details: [{
          ...consoleData.actionWorkbench.details[0],
          timeline: [{
            ...consoleData.actionWorkbench.details[0].timeline[0],
            download_url: "/unsafe/raw"
          }, ...consoleData.actionWorkbench.details[0].timeline.slice(1)]
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      actionWorkbench: {
        ...consoleData.actionWorkbench,
        details: [{
          ...consoleData.actionWorkbench.details[0],
          timeline: [{
            ...consoleData.actionWorkbench.details[0].timeline[0],
            body: "查看 http://example.invalid/raw"
          }, ...consoleData.actionWorkbench.details[0].timeline.slice(1)]
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      actionWorkbench: {
        ...consoleData.actionWorkbench,
        details: [{
          ...consoleData.actionWorkbench.details[0],
          audit_packet: {
            ...consoleData.actionWorkbench.details[0].audit_packet,
            summary: "查看 https://example.invalid/raw"
          }
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      actionWorkbench: {
        ...consoleData.actionWorkbench,
        details: [{
          ...consoleData.actionWorkbench.details[0],
          audit_packet: {
            ...consoleData.actionWorkbench.details[0].audit_packet,
            evidence_refs: ["https://example.invalid/raw"]
          }
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      actionWorkbench: {
        ...consoleData.actionWorkbench,
        details: [{
          ...consoleData.actionWorkbench.details[0],
          audit_packet: null
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      operationCenter: {
        ...consoleData.operationCenter,
        todos: [{ ...consoleData.operationCenter.todos[0], action_id: "action_missing" }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, summary: null }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      summary: {
        ...consoleData.summary,
        metrics: null
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      sdlcRuns: [{
        id: "bad_verified_loaded",
        command: "ai-sdlc run --dry-run",
        adapter_status: "materialized",
        dry_run_status: "dry_run_passed",
        proof_source: "CLI 预演",
        captured_at: "待采集",
        verified_loaded: "verified_loaded"
      }]
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      summary: {
        ...consoleData.summary,
        adapter: {
          ...consoleData.summary.adapter,
          status: "verified_loaded",
          proof_source: "AGENTS.md",
          captured_at: "待采集"
        }
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      sdlcRunWorkbench: {
        ...consoleData.sdlcRunWorkbench,
        reporter: consoleData.sdlcRunWorkbench.reporter.map((item) =>
          item.run_id === "sdlc_001" ? {
            ...item,
            reporter_status: "active",
            credential_status: "active",
            source_signed: "active",
            identity_confidence: "verified_loaded"
          } : item
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      sdlcRunWorkbench: {
        ...consoleData.sdlcRunWorkbench,
        outbox: consoleData.sdlcRunWorkbench.outbox.map((item) =>
          item.run_id === "sdlc_001" ? {
            ...item,
            outbox_status: "healthy",
            sequence_state: "healthy",
            pending_events: "0",
            oldest_pending_age: "0 分钟"
          } : item
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      sdlcRunWorkbench: {
        ...consoleData.sdlcRunWorkbench,
        eligibility: consoleData.sdlcRunWorkbench.eligibility.map((item) =>
          item.run_id === "sdlc_001" ? {
            ...item,
            evidence_level: "L5",
            l5_result: "healthy",
            failed_conditions: "无",
            governance_loaded: "verified_loaded",
            outbox_delivered: "healthy"
          } : item
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      sdlcRunWorkbench: {
        ...consoleData.sdlcRunWorkbench,
        reporter: consoleData.sdlcRunWorkbench.reporter.slice(1)
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      sdlcRunWorkbench: {
        ...consoleData.sdlcRunWorkbench,
        reporter: consoleData.sdlcRunWorkbench.reporter.map((item) =>
          item.run_id === "sdlc_001" ? {
            ...item,
            raw_access_url: "/sdlc/raw/proof"
          } : item
        )
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: { ...consoleData, connectors: [{ id: "conn_bad", status: "surprise_green" }] }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      summary: {
        ...consoleData.summary,
        metrics: [{ label: "今日运行", value: 0, status: "empty", detail: "暂无运行事实" }]
      }
    }
  }),
  true
);

const detailIds = new Set(consoleData.actionWorkbench.details.map((item) => item.id));
for (const collectionName of ["notifications", "todos", "searchIndex"]) {
  for (const item of consoleData.operationCenter[collectionName]) {
    if (item.action_id) {
      assert.ok(detailIds.has(item.action_id), `${item.action_id} must resolve to action detail`);
    }
  }
}

const apiLoad = await loadAgentOpsSnapshot(async () => ({
  ok: true,
  json: async () => validApiSnapshot
}), "http://127.0.0.1:8765");
assert.equal(apiLoad.source, "api_snapshot");
assert.equal(apiLoad.sourceState.label, "后端快照已连接");
assert.equal(qualityCenterWorkbenchIsComplete(apiLoad.consoleData), true);
assert.equal(apiLoad.consoleData.qualityCenterWorkbench.schema_version, "quality_center_workbench.v1");
assert.equal(
  apiLoad.consoleData.qualityCenterWorkbench.agent_summaries.length,
  consoleData.quality.length
);
assert.equal(
  apiLoad.consoleData.qualityCenterWorkbench.scorer_rollout_panel.automatic_rollout_enabled,
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      qualityCenterWorkbench: {
        ...apiLoad.consoleData.qualityCenterWorkbench,
        summary: {
          ...apiLoad.consoleData.qualityCenterWorkbench.summary,
          automatic_rollout_enabled: true
        }
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      qualityCenterWorkbench: {
        ...apiLoad.consoleData.qualityCenterWorkbench,
        review_queue: [{
          ...apiLoad.consoleData.qualityCenterWorkbench.review_queue[0],
          automatic_action_performed: true
        }]
      }
    }
  }),
  false
);
assert.equal(
  validateSnapshot({
    ...validApiSnapshot,
    consoleData: {
      ...consoleData,
      qualityCenterWorkbench: {
        ...apiLoad.consoleData.qualityCenterWorkbench,
        agent_summaries: [{
          ...apiLoad.consoleData.qualityCenterWorkbench.agent_summaries[0],
          explanation: "查看 https://example.invalid/raw-quality"
        }]
      }
    }
  }),
  false
);

const legacyApiLoad = await loadAgentOpsSnapshot(async () => ({
  ok: true,
  json: async () => legacyV1SnapshotWithoutAdoption
}), "http://127.0.0.1:8765");
assert.equal(legacyApiLoad.source, "api_snapshot");
assert.equal(legacyApiLoad.consoleData.adoption.metrics.generated_lines, 0);
assert.equal(legacyApiLoad.consoleData.adoption.metrics.retention_rate, "0%");
assert.equal(legacyApiLoad.consoleData.adoption.segments[0].status, "empty");
assert.match(legacyApiLoad.consoleData.adoption.guardrails.join(" "), /低置信不自动下架/);

const legacyVaultApiLoad = await loadAgentOpsSnapshot(async () => ({
  ok: true,
  json: async () => legacyV1SnapshotWithoutEvidenceVault
}), "http://127.0.0.1:8765");
assert.equal(legacyVaultApiLoad.source, "api_snapshot");
assert.equal(legacyVaultApiLoad.consoleData.evidenceVault.requests.length, consoleData.evidence.length);
assert.equal(legacyVaultApiLoad.consoleData.evidenceVault.grants.length, consoleData.evidence.length);
assert.equal(legacyVaultApiLoad.consoleData.evidenceVault.auditTrail.length, consoleData.evidence.length);
assert.match(legacyVaultApiLoad.consoleData.evidenceVault.guardrails.join(" "), /默认不展示原文/);

const legacyApprovalApiLoad = await loadAgentOpsSnapshot(async () => ({
  ok: true,
  json: async () => legacyV1SnapshotWithoutApprovalWorkbench
}), "http://127.0.0.1:8765");
assert.equal(legacyApprovalApiLoad.source, "api_snapshot");
assert.equal(legacyApprovalApiLoad.consoleData.approvalWorkbench.queues.length, consoleData.approvals.length);
assert.equal(legacyApprovalApiLoad.consoleData.approvalWorkbench.grants.length, consoleData.approvals.length);
assert.equal(legacyApprovalApiLoad.consoleData.approvalWorkbench.auditTrail.length, consoleData.approvals.length);
assert.match(legacyApprovalApiLoad.consoleData.approvalWorkbench.guardrails.join(" "), /审批队列只展示人工处置摘要/);

const legacyConnectorApiLoad = await loadAgentOpsSnapshot(async () => ({
  ok: true,
  json: async () => legacyV1SnapshotWithoutConnectorWorkbench
}), "http://127.0.0.1:8765");
assert.equal(legacyConnectorApiLoad.source, "api_snapshot");
assert.equal(legacyConnectorApiLoad.consoleData.connectorWorkbench.health.length, consoleData.connectors.length);
assert.equal(legacyConnectorApiLoad.consoleData.connectorWorkbench.dlq.length, consoleData.connectors.length);
assert.equal(legacyConnectorApiLoad.consoleData.connectorWorkbench.syncTrail.length, consoleData.connectors.length);
assert.match(legacyConnectorApiLoad.consoleData.connectorWorkbench.guardrails.join(" "), /Outbox Replay/);

const legacySdlcRunApiLoad = await loadAgentOpsSnapshot(async () => ({
  ok: true,
  json: async () => legacyV1SnapshotWithoutSdlcRunWorkbench
}), "http://127.0.0.1:8765");
assert.equal(legacySdlcRunApiLoad.source, "api_snapshot");
assert.equal(legacySdlcRunApiLoad.consoleData.sdlcRunWorkbench.reporter.length, consoleData.sdlcRuns.length);
assert.equal(legacySdlcRunApiLoad.consoleData.sdlcRunWorkbench.outbox.length, consoleData.sdlcRuns.length);
assert.equal(legacySdlcRunApiLoad.consoleData.sdlcRunWorkbench.eligibility.length, consoleData.sdlcRuns.length);
assert.match(legacySdlcRunApiLoad.consoleData.sdlcRunWorkbench.guardrails.join(" "), /Reporter active/);

const legacyQualityCenterApiLoad = await loadAgentOpsSnapshot(async () => ({
  ok: true,
  json: async () => legacyV1SnapshotWithoutQualityCenterWorkbench
}), "http://127.0.0.1:8765");
assert.equal(legacyQualityCenterApiLoad.source, "api_snapshot");
assert.equal(legacyQualityCenterApiLoad.consoleData.qualityCenterWorkbench.agent_summaries.length, consoleData.quality.length);
assert.equal(legacyQualityCenterApiLoad.consoleData.qualityCenterWorkbench.summary.store_write_performed, false);
assert.equal(legacyQualityCenterApiLoad.consoleData.qualityCenterWorkbench.review_queue[0].manual_review_required, true);

const liveApiLoad = await loadAgentOpsSnapshot(async () => ({
  ok: true,
  json: async () => ({ ...validApiSnapshot, source_detail: { mode: "repository_backed" } })
}), "http://127.0.0.1:8765");
assert.equal(liveApiLoad.sourceState.label, "后端事实快照已连接");
assert.match(liveApiLoad.sourceState.copy, /事件仓库生成/);
assert.equal(liveApiLoad.sourceState.sourceType, "事件仓库事实");
assert.match(liveApiLoad.sourceState.sourceSummary, /不包含生产 IAM、数据库/);
assert.equal(liveApiLoad.sourceState.primary_action, "重新生成快照");

const fallbackLoad = await loadAgentOpsSnapshot(async () => {
  throw new Error("offline");
}, "http://127.0.0.1:8765");
assert.equal(fallbackLoad.source, "mock_fallback");
assert.equal(fallbackLoad.sourceState.status, "degraded");
assert.match(fallbackLoad.sourceState.copy, /本地安全样例/);
assert.equal(fallbackLoad.sourceState.primary_action, "重试拉取");

const timeoutLoad = await loadAgentOpsSnapshot((_url, options) => new Promise((_resolve, reject) => {
  options.signal.addEventListener("abort", () => reject(Object.assign(new Error("aborted"), { name: "AbortError" })));
}), "http://127.0.0.1:8765", 1);
assert.equal(timeoutLoad.source, "mock_fallback");
assert.match(timeoutLoad.sourceState.copy, /超时/);

for (const sdlcRun of consoleData.sdlcRuns) {
  const proofSource = String(sdlcRun.proof_source || "");
  const capturedAt = String(sdlcRun.captured_at || "");
  const proofPending = /待采集|待接入|CLI 预演|AGENTS\.md/.test(`${proofSource} ${capturedAt}`);

  if (proofPending) {
    assert.equal(
      sdlcRun.verified_loaded,
      "unverified",
      `${sdlcRun.id} must stay unverified until machine-verifiable proof is captured`
    );
  }

  if (sdlcRun.verified_loaded === "verified_loaded") {
    assert.ok(
      !proofPending && capturedAt && proofSource,
      `${sdlcRun.id} verified_loaded requires non-pending proof source and captured_at`
    );
  }
}

for (const removedEnglishText of [
  "Governance Console",
  "Current View",
  "Priority Risks",
  "Open queue",
  "Governance Proof",
  "Evidence Explorer",
  "Approval Center",
  "Policy Center",
  "Quality Center",
  "Risk Triage",
  "Connector Status",
  "Redaction failed. Summary body withheld.",
  "Request access"
]) {
  assert.ok(
    !uiSource.includes(removedEnglishText),
    `${removedEnglishText} must not appear as user-facing UI text`
  );
}

const allowedEnglishUiTerms = [
  "AgentOps",
  "Agent",
  "Skill",
  "Ai_AutoSDLC",
  "AI-SDLC",
  "CLI",
  "dry-run",
  "adapter",
  "verified_loaded",
  "materialized",
  "unverified",
  "Grant",
  "Grant TTL",
  "TTL",
  "Git",
  "PR",
  "CI",
  "DLQ",
  "Reporter",
  "Outbox",
  "Outbox Replay",
  "L5",
  "Evidence Vault",
  "L5 Gate",
  "Browser Gate",
  "Policy SLO",
  "SLA",
  "SLO",
  "IAM",
  "AGENTS.md",
  "P95",
  "AO",
  "AO1",
  "AO2",
  "AO3",
  "Adapter",
  "Agent Store",
  "Store",
  "API",
  "active",
  "mock",
  "deny",
  "block",
  "require_online",
  "deploy:prod",
  "evidence.raw",
  "db.migrate",
  "store.publish",
  "test:run",
  "runtime-v2.1",
  "runtime-v2.2",
  "runtime-v2.3",
  "runtime-v2",
  "runtime_policy",
  "sha256",
  "SDLC",
  "SD"
];
const userFacingValuePattern =
  /(?:label|copy|detail|summary|proof_source|agent|skill|risk_level|reason|requester|grant_ttl|source|severity|owner_hint|primary_action|category|score|evidence_ref|name|degrade_action|fallback_action|policy_version|denied_scope)\s*:\s*"([^"]*)"/g;
const templateTextPattern = />\s*([^<>{}`\n][^<>{}`]*)\s*</g;
const userFacingTextCandidates = [
  ...[...mockDataSource.matchAll(userFacingValuePattern)].map((match) => match[1]),
  ...[...uiSource.matchAll(templateTextPattern)].map((match) => match[1].trim()).filter(Boolean)
];
const allowedEnglishPattern = new RegExp(
  allowedEnglishUiTerms
    .sort((left, right) => right.length - left.length)
    .map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("|"),
  "g"
);

for (const candidate of userFacingTextCandidates) {
  const residue = candidate
    .replace(allowedEnglishPattern, "")
    .replace(/[0-9:._/%/-]/g, "")
    .trim();
  assert.doesNotMatch(residue, /[A-Za-z]{3,}/, `${candidate} must be Chinese unless it is an allowed fixed term`);
}
