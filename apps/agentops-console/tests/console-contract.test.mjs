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
  "src/views/ConnectorStatusView.js",
  "src/views/SdlcRunsView.js"
].map(readText).join("\n");
const uiSource = `${appSource}\n${appShellSource}\n${statusBadgeSource}\n${mockDataSource}\n${apiClientSource}\n${viewSources}`;
const techStack = readRepoText(".ai-sdlc/profiles/tech-stack.yml");
const { loadAgentOpsSnapshot, validateSnapshot } = await import(`file://${resolve(root, "src/data/agentOpsApiClient.js")}`);

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
assert.match(appShellSource, /sourceState/);
assert.match(appShellSource, /refresh-snapshot/);
assert.match(uiSource, /后端快照/);

assert.match(techStack, /source:\s*project-vendor/);
assert.match(techStack, /path:\s*vendor\/enterprise-vue2\/sxf-er-components-1\.27\.5\.tgz/);

assert.ok(existsSync(resolve(root, "src/styles.css")), "src/styles.css must exist because src/main.js imports it");

for (const expectedChineseText of [
  "治理控制台",
  "当前视图",
  "总览",
  "运行记录",
  "证据检索",
  "审批中心",
  "策略中心",
  "质量中心",
  "风险处置",
  "连接器状态",
  "Ai_AutoSDLC 运行",
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
    { id: "connectors", label: "连接器状态", icon: "∞" },
    { id: "sdlc-runs", label: "Ai_AutoSDLC 运行", icon: "SD" }
  ] : [],
  consoleData
};

assert.equal(validateSnapshot(validApiSnapshot), true);
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
    consoleData: { ...consoleData, connectors: [{ id: "conn_bad", status: "surprise_green" }] }
  }),
  false
);

const apiLoad = await loadAgentOpsSnapshot(async () => ({
  ok: true,
  json: async () => validApiSnapshot
}), "http://127.0.0.1:8765");
assert.equal(apiLoad.source, "api_snapshot");
assert.equal(apiLoad.sourceState.label, "后端快照已连接");

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
  "Ai_AutoSDLC",
  "AI-SDLC",
  "CLI",
  "dry-run",
  "adapter",
  "verified_loaded",
  "materialized",
  "Grant",
  "Grant TTL",
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
  "API",
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
