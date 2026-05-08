#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

const REVIEW_MARKER = "<!-- agentops-adversarial-pr-review -->";
const root = process.cwd();

const args = new Map();
for (let index = 2; index < process.argv.length; index += 1) {
  const arg = process.argv[index];
  if (arg.startsWith("--")) {
    const next = process.argv[index + 1];
    if (next && !next.startsWith("--")) {
      args.set(arg, next);
      index += 1;
    } else {
      args.set(arg, "true");
    }
  }
}

const baseRef = args.get("--base") || process.env.BASE_REF || "origin/main";
const headRef = args.get("--head") || process.env.HEAD_REF || "HEAD";
const prNumber = args.get("--pr") || process.env.PR_NUMBER || "";
const shouldPostComment = args.get("--post-comment") === "true" || process.env.POST_REVIEW_COMMENT === "true";

const findings = [];

function git(argsList) {
  return execFileSync("git", argsList, { cwd: root, encoding: "utf8" }).trim();
}

function readText(path) {
  return readFileSync(resolve(root, path), "utf8");
}

function fileExists(path) {
  return existsSync(resolve(root, path));
}

function changedFiles() {
  const output = git(["diff", "--name-only", `${baseRef}...${headRef}`]);
  return output ? output.split("\n").filter(Boolean) : [];
}

function lineOf(path, needle) {
  if (!fileExists(path)) {
    return 1;
  }
  const lines = readText(path).split("\n");
  const index = lines.findIndex((line) => line.includes(needle));
  return index >= 0 ? index + 1 : 1;
}

function addFinding(priority, file, needle, title, body) {
  findings.push({
    priority,
    file,
    line: lineOf(file, needle),
    title,
    body
  });
}

function requireFile(path, priority, title, body) {
  if (!fileExists(path)) {
    findings.push({ priority, file: path, line: 1, title, body });
    return false;
  }
  return true;
}

function requireText(path, needle, priority, title, body) {
  if (!requireFile(path, priority, title, body)) {
    return false;
  }
  if (!readText(path).includes(needle)) {
    addFinding(priority, path, "", title, body);
    return false;
  }
  return true;
}

function checkEvidenceVaultBackend() {
  const path = "src/agentops/api/console_snapshot.py";
  if (!requireFile(path, "P1", "缺少后端 Evidence Vault 视图模型", "PR 涉及 012 Evidence Vault，但后端 snapshot 文件不存在，Console 无法形成可验证数据域。")) {
    return;
  }
  const text = readText(path);
  const required = [
    "def _evidence_vault_workbench",
    "\"requests\": [_evidence_vault_request",
    "\"grants\": [_evidence_vault_grant",
    "\"auditTrail\": [_evidence_vault_audit",
    "默认不展示原文",
    "不生成下载链接",
    "不自动批准、不自动写回"
  ];
  for (const needle of required) {
    if (!text.includes(needle)) {
      addFinding("P1", path, "_evidence_vault_workbench", "Evidence Vault 后端契约不完整", `后端 snapshot 必须包含 ${needle}，否则 PRD 中原文访问申请/授权/审计闭环不可验证。`);
    }
  }
  for (const forbidden of ["raw_payload", "download_url", "raw_url", "raw_access_url", "original_url"]) {
    if (text.includes(`"${forbidden}"`) || text.includes(`'${forbidden}'`)) {
      addFinding("P0", path, forbidden, "后端 Evidence Vault 暴露了原文访问红线字段", `后端安全摘要不得生成 ${forbidden} 字段。Evidence Vault 工作台只能展示申请、授权、审计和哈希摘要。`);
    }
  }
}

function checkEvidenceVaultFrontendValidator() {
  const path = "apps/agentops-console/src/data/agentOpsApiClient.js";
  if (!requireFile(path, "P1", "缺少前端快照校验器", "PR 涉及 Console 数据域，但前端 validator 不存在，无法阻断危险快照。")) {
    return;
  }
  const text = readText(path);
  const required = [
    "evidenceVaultIsComplete",
    "const evidenceById = new Map",
    "legacyEvidenceVault",
    "vaultRowsMatchEvidence",
    "rows.length !== evidenceItems.length",
    "vaultRequestMatchesEvidence",
    "vaultGrantMatchesEvidence",
    "vaultAuditMatchesEvidence",
    "state === \"permission_denied\"",
    "request.status === \"permission_denied\"",
    "grant.status === \"rejected\"",
    "request.primary_action === \"补充申请理由\"",
    "state === \"redaction_failed\"",
    "request.primary_action === \"仅查看哈希告警\"",
    "grant.status === \"redaction_failed\"",
    "grant.expires_at === \"暂停授权\"",
    "state === \"approved_limited\"",
    "grant.status === \"active\"",
    "state === \"degraded\"",
    "request.primary_action === \"等待审批\"",
    "request.ttl_summary === \"待补偿\"",
    "grant.expires_at === \"待补偿\"",
    "state === \"summary_only\"",
    "request.status === \"pending\""
  ];
  for (const needle of required) {
    if (!text.includes(needle)) {
      addFinding("P1", path, "evidenceVaultIsComplete", "Evidence Vault 状态绑定不完整", `前端 validator 必须包含 ${needle}。否则 permission_denied/redaction_failed 可能被篡改成授权态。`);
    }
  }
  for (const forbidden of ["raw_payload", "download_url", "raw_url", "original_url", "raw_access_url", "pull_request_body", "pullrequestbody"]) {
    if (!text.toLowerCase().includes(forbidden.toLowerCase())) {
      addFinding("P1", path, "containsUnsafeAuditReference", "危险字段拦截不完整", `validator 必须递归拒绝 ${forbidden}，以防 API 快照携带原文、下载链接或 PR 原文。`);
    }
  }
}

function checkEvidenceVaultUi() {
  const path = "apps/agentops-console/src/views/EvidenceExplorerView.js";
  if (!requireFile(path, "P2", "缺少 Evidence Explorer 页面", "证据检索页不存在，用户无法看到 Evidence Vault 工作台。")) {
    return;
  }
  const text = readText(path);
  for (const needle of ["证据检索与 Evidence Vault", "原文访问申请", "限时授权", "审计轨迹", "默认不展示原文", "不提供原文下载"]) {
    if (!text.includes(needle)) {
      addFinding("P2", path, "Evidence Vault", "Evidence Vault 中文界面信号不足", `页面必须展示“${needle}”，让大陆用户明确原文访问的申请、授权、审计和红线边界。`);
    }
  }
  for (const banned of ["Request access", "Evidence Explorer", "Approval Center", "Policy Center", "Redaction failed"]) {
    if (text.includes(banned)) {
      addFinding("P2", path, banned, "出现非必要英文界面文案", `面向中国大陆用户的 UI 不应出现“${banned}”这类非固定名词英文文案。`);
    }
  }
}

function checkEvidenceVaultTestsAndContracts() {
  const contractTest = "tests/contract/test_ao12_ct_console_evidence_vault_workbench.py";
  const frontendTest = "apps/agentops-console/tests/console-contract.test.mjs";
  const specContract = "specs/012-console-evidence-vault-workbench/contracts/evidence-vault-workbench-contract.md";
  const observations = "specs/012-console-evidence-vault-workbench/frontend-contract-observations.json";
  const pageMetadata = "contracts/frontend/pages/evidence-vault-workbench/page.metadata.yaml";
  const pageRecipe = "contracts/frontend/pages/evidence-vault-workbench/page.recipe.yaml";

  for (const path of [contractTest, frontendTest, specContract, observations, pageMetadata, pageRecipe]) {
    requireFile(path, "P1", "缺少 012 契约或观测产物", `${path} 是 Evidence Vault 云端 review 的必要证据，缺失会让 PR 无法证明实现满足契约。`);
  }
  if (fileExists(frontendTest)) {
    const text = readText(frontendTest);
    const requiredNegatives = [
      "raw_access_url",
      "download_url",
      "pullRequestBody",
      "自动批准原文访问",
      "ev_004",
      "ev_003",
      "raw_access_state: \"degraded\"",
      "primary_action: \"等待审批\"",
      "ttl_summary: \"待补偿\"",
      "requests: []",
      "grants: []",
      "auditTrail: []",
      "legacyV1SnapshotWithoutEvidenceVault",
      "status: \"active\"",
      "primary_action: \"申请原文访问\""
    ];
    for (const needle of requiredNegatives) {
      if (!text.includes(needle)) {
        addFinding("P1", frontendTest, "validateSnapshot", "前端负例覆盖不足", `console-contract.test.mjs 必须覆盖 ${needle}，否则拒绝态/脱敏失败态的篡改风险不会被云端 review 捕获。`);
      }
    }
  }
  if (fileExists(contractTest)) {
    const text = readText(contractTest);
    for (const needle of ["raw_payload", "download_url", "raw_access_url", "redaction_failed", "permission_denied", "degraded", "待补偿", "默认不展示原文"]) {
      if (!text.includes(needle)) {
        addFinding("P1", contractTest, "test_ao12", "后端契约测试覆盖不足", `AO12 后端契约测试必须覆盖 ${needle}。`);
      }
    }
  }
}

function checkApprovalWorkbenchBackend() {
  const path = "src/agentops/api/console_snapshot.py";
  if (!requireFile(path, "P1", "缺少后端 Approval Grant 工作台", "PR 涉及 013 人工审批与 Grant 工作台，但后端 snapshot 文件不存在，Console 无法形成可验证审批数据域。")) {
    return;
  }
  const text = readText(path);
  const required = [
    "def _approval_workbench",
    "\"queues\": [_approval_queue_item",
    "\"grants\": [_approval_grant_item",
    "\"auditTrail\": [_approval_audit_item",
    "审批队列只展示人工处置摘要",
    "Grant 必须绑定原始审批编号",
    "不得作为唯一审批人",
    "补充材料只展示摘要"
  ];
  for (const needle of required) {
    if (!text.includes(needle)) {
      addFinding("P1", path, "_approval_workbench", "Approval Grant 后端契约不完整", `后端 snapshot 必须包含 ${needle}，否则审批队列、Grant 影响和审计轨迹不可验证。`);
    }
  }
  for (const forbidden of ["raw_payload", "download_url", "raw_url", "raw_access_url", "original_url"]) {
    if (text.includes(`"${forbidden}"`) || text.includes(`'${forbidden}'`)) {
      addFinding("P0", path, forbidden, "后端 Approval Grant 暴露了原文访问红线字段", `审批工作台不得生成 ${forbidden} 字段。只能展示审批摘要、Grant 影响和审计引用。`);
    }
  }
}

function checkApprovalWorkbenchFrontendValidator() {
  const path = "apps/agentops-console/src/data/agentOpsApiClient.js";
  if (!requireFile(path, "P1", "缺少前端快照校验器", "PR 涉及审批工作台数据域，但前端 validator 不存在，无法阻断危险快照。")) {
    return;
  }
  const text = readText(path);
  const required = [
    "approvalWorkbenchIsComplete",
    "legacyApprovalWorkbench",
    "approvalRowsMatchApprovals",
    "approvalQueueMatchesApproval",
    "approvalGrantMatchesApproval",
    "approvalAuditMatchesApproval",
    "workbench.queues",
    "workbench.grants",
    "workbench.auditTrail",
    "item.status === approval.status",
    "item.grant_status === legacyApprovalGrantStatus(approval.status, approval.grant_status)",
    "审批队列只展示人工处置摘要",
    "不得作为唯一审批人"
  ];
  for (const needle of required) {
    if (!text.includes(needle)) {
      addFinding("P1", path, "approvalWorkbenchIsComplete", "Approval Grant 状态绑定不完整", `前端 validator 必须包含 ${needle}。否则 pending/escalated/revoked 可能被篡改成已授权态。`);
    }
  }
  for (const forbidden of ["raw_payload", "download_url", "raw_url", "original_url", "raw_access_url", "pull_request_body", "pullrequestbody"]) {
    if (!text.toLowerCase().includes(forbidden.toLowerCase())) {
      addFinding("P1", path, "containsUnsafeAuditReference", "审批工作台危险字段拦截不完整", `validator 必须递归拒绝 ${forbidden}，以防 API 快照携带原文、下载链接或 PR 原文。`);
    }
  }
}

function checkApprovalWorkbenchUi() {
  const path = "apps/agentops-console/src/views/ApprovalCenterView.js";
  if (!requireFile(path, "P2", "缺少 Approval Center 页面", "审批中心页面不存在，用户无法看到人工审批与 Grant 工作台。")) {
    return;
  }
  const text = readText(path);
  for (const needle of ["人工审批与 Grant 工作台", "审批队列", "Grant 影响", "审批审计轨迹", "只读审批摘要", "补充材料"]) {
    if (!text.includes(needle)) {
      addFinding("P2", path, "人工审批与 Grant 工作台", "Approval Grant 中文界面信号不足", `页面必须展示“${needle}”，让大陆用户明确审批队列、Grant 影响、审计轨迹和只读边界。`);
    }
  }
  for (const banned of ["Approval Queue", "Grant Impact", "Audit Trail", "Approve", "Reject"]) {
    if (text.includes(banned)) {
      addFinding("P2", path, banned, "出现非必要英文审批界面文案", `面向中国大陆用户的 UI 不应出现“${banned}”这类非固定名词英文文案。`);
    }
  }
}

function checkApprovalWorkbenchTestsAndContracts() {
  const contractTest = "tests/contract/test_ao13_ct_approval_grant_workbench.py";
  const frontendTest = "apps/agentops-console/tests/console-contract.test.mjs";
  const specContract = "specs/013-approval-grant-workbench/contracts/approval-grant-workbench-contract.md";

  for (const path of [contractTest, frontendTest, specContract]) {
    requireFile(path, "P1", "缺少 013 契约或测试产物", `${path} 是 Approval Grant 云端 review 的必要证据，缺失会让 PR 无法证明实现满足契约。`);
  }
  if (fileExists(frontendTest)) {
    const text = readText(frontendTest);
    const requiredNegatives = [
      "approvalWorkbench: null",
      "queues: []",
      "grants: []",
      "auditTrail: []",
      "raw_access_url",
      "自动批准审批",
      "legacyV1SnapshotWithoutApprovalWorkbench",
      "grant_status: \"active\"",
      "pendingApprovalWithActiveGrant",
      "primary_action: \"查看审批记录\""
    ];
    for (const needle of requiredNegatives) {
      if (!text.includes(needle)) {
        addFinding("P1", frontendTest, "validateSnapshot", "审批工作台前端负例覆盖不足", `console-contract.test.mjs 必须覆盖 ${needle}，否则审批状态或 Grant 状态篡改风险不会被云端 review 捕获。`);
      }
    }
  }
  if (fileExists(contractTest)) {
    const text = readText(contractTest);
    for (const needle of ["pending", "escalated", "approved", "revoked", "raw_access_url", "download_url", "不得作为唯一审批人", "审批队列只展示人工处置摘要"]) {
      if (!text.includes(needle)) {
        addFinding("P1", contractTest, "test_ao13", "后端审批契约测试覆盖不足", `AO13 后端契约测试必须覆盖 ${needle}。`);
      }
    }
  }
}

function checkConnectorWorkbenchBackend() {
  const path = "src/agentops/api/console_snapshot.py";
  if (!requireFile(path, "P1", "缺少后端 Connector Health 工作台", "PR 涉及 014 连接器健康工作台，但后端 snapshot 文件不存在，Console 无法形成可验证连接器数据域。")) {
    return;
  }
  const text = readText(path);
  const required = [
    "def _connector_workbench",
    "\"health\": [_connector_health",
    "\"dlq\": [_connector_dlq",
    "\"syncTrail\": [_connector_sync_trail",
    "连接器新鲜度 SLO 为 15 分钟内",
    "超过 20 分钟必须告警",
    "Outbox Replay",
    "不构成 verified_loaded 治理激活证明"
  ];
  for (const needle of required) {
    if (!text.includes(needle)) {
      addFinding("P1", path, "_connector_workbench", "Connector Health 后端契约不完整", `后端 snapshot 必须包含 ${needle}，否则连接器新鲜度、DLQ、回放边界或伪治理激活风险不可验证。`);
    }
  }
  for (const forbidden of ["raw_payload", "download_url", "raw_url", "raw_access_url", "original_url"]) {
    if (text.includes(`"${forbidden}"`) || text.includes(`'${forbidden}'`)) {
      addFinding("P0", path, forbidden, "后端 Connector Health 暴露了红线字段", `连接器工作台不得生成 ${forbidden} 字段，只能展示健康摘要、DLQ 摘要和同步轨迹。`);
    }
  }
}

function checkConnectorWorkbenchFrontendValidator() {
  const path = "apps/agentops-console/src/data/agentOpsApiClient.js";
  if (!requireFile(path, "P1", "缺少前端快照校验器", "PR 涉及连接器工作台数据域，但前端 validator 不存在，无法阻断危险快照。")) {
    return;
  }
  const text = readText(path);
  const required = [
    "connectorWorkbenchIsComplete",
    "legacyConnectorWorkbench",
    "connectorRowsMatchConnectors",
    "connectorHealthMatchesConnector",
    "connectorHealthStateIsSafe",
    "connectorDlqMatchesConnector",
    "connectorSyncMatchesConnector",
    "connectorBoundarySetIsSafe",
    "sdlcConnectorProofStateIsSafe",
    "containsUnsafeAuditReference(consoleData.connectors",
    "rate_limit_detail",
    "[\"healthy\", \"warning\"].includes(item.rate_limit_state)",
    "item.rate_limit_state === \"warning\"",
    "item.rate_limit_state === \"degraded\"",
    "item.status === \"materialized\"",
    "primary_action === \"补齐治理加载证明\"",
    "不构成 verified_loaded",
    "item.status === \"degraded\"",
    "降低证据等级",
    "item.oldest_event_age !== \"0 分钟\"",
    "replay_state === \"pending\"",
    "Outbox Replay"
  ];
  for (const needle of required) {
    if (!text.includes(needle)) {
      addFinding("P1", path, "connectorWorkbenchIsComplete", "Connector Health 状态绑定不完整", `前端 validator 必须包含 ${needle}。否则 materialized/unverified 或 degraded 连接器可能被篡改为健康态。`);
    }
  }
  for (const forbidden of ["raw_payload", "download_url", "raw_url", "original_url", "raw_access_url", "pull_request_body", "pullrequestbody"]) {
    if (!text.toLowerCase().includes(forbidden.toLowerCase())) {
      addFinding("P1", path, "containsUnsafeAuditReference", "连接器工作台危险字段拦截不完整", `validator 必须递归拒绝 ${forbidden}，以防 API 快照携带原文、下载链接或 PR 原文。`);
    }
  }
}

function checkConnectorWorkbenchUi() {
  const path = "apps/agentops-console/src/views/ConnectorStatusView.js";
  if (!requireFile(path, "P2", "缺少 Connector Status 页面", "连接器状态页面不存在，用户无法看到连接器健康工作台。")) {
    return;
  }
  const text = readText(path);
  for (const needle of ["连接器健康工作台", "健康与限流", "DLQ 与 Outbox Replay", "同步轨迹", "15 分钟 SLO", "超过 20 分钟", "不构成 verified_loaded"]) {
    if (!text.includes(needle)) {
      addFinding("P2", path, "连接器健康工作台", "Connector Health 中文界面信号不足", `页面必须展示“${needle}”，让大陆用户明确连接器新鲜度、限流、DLQ、回放和治理证明边界。`);
    }
  }
  for (const banned of ["Connector Status", "Connector Health", "Replay now", "Retry now"]) {
    if (text.includes(banned)) {
      addFinding("P2", path, banned, "出现非必要英文连接器界面文案", `面向中国大陆用户的 UI 不应出现“${banned}”这类非固定名词英文文案。`);
    }
  }
}

function checkConnectorWorkbenchTestsAndContracts() {
  const contractTest = "tests/contract/test_ao14_ct_connector_health_workbench.py";
  const frontendTest = "apps/agentops-console/tests/console-contract.test.mjs";
  const specContract = "specs/014-console-connector-health-workbench/contracts/connector-health-workbench-contract.md";

  for (const path of [contractTest, frontendTest, specContract]) {
    requireFile(path, "P1", "缺少 014 契约或测试产物", `${path} 是 Connector Health 云端 review 的必要证据，缺失会让 PR 无法证明实现满足契约。`);
  }
  if (fileExists(frontendTest)) {
    const text = readText(frontendTest);
    const requiredNegatives = [
      "connectorWorkbench: null",
      "legacyV1SnapshotWithoutConnectorWorkbench",
      "legacyV1SnapshotWithSmallConnectorSet",
      "connectorWorkbench.health.length",
      "legacyUnsafeConnectorSnapshot",
      "sdlcSpoofedHealthyConnector",
      "missingExternalConnectorBoundary",
      "conn_sdlc",
      "conn_git",
      "status: \"healthy\"",
      "healthyConnectorWarningRateLimit",
      "healthyConnectorDegradedRateLimitState",
      "rate_limit_state: \"healthy\"",
      "rate_limit_state: \"warning\"",
      "rate_limit_state: \"degraded\"",
      "oldest_event_age: \"0 分钟\"",
      "raw_access_url",
      "Outbox Replay",
      "超过 20 分钟"
    ];
    for (const needle of requiredNegatives) {
      if (!text.includes(needle)) {
        addFinding("P1", frontendTest, "validateSnapshot", "连接器工作台前端负例覆盖不足", `console-contract.test.mjs 必须覆盖 ${needle}，否则连接器状态或回放边界篡改风险不会被云端 review 捕获。`);
      }
    }
  }
  if (fileExists(contractTest)) {
    const text = readText(contractTest);
    for (const needle of ["materialized", "degraded", "verified_loaded", "Outbox Replay", "raw_access_url", "download_url", "Git、PR、CI、测试、IAM", "conn_git", "conn_pr", "conn_ci", "conn_test", "conn_iam"]) {
      if (!text.includes(needle)) {
        addFinding("P1", contractTest, "test_ao14", "后端连接器契约测试覆盖不足", `AO14 后端契约测试必须覆盖 ${needle}。`);
      }
    }
  }
}

function checkSdlcRunWorkbenchBackend() {
  const path = "src/agentops/api/console_snapshot.py";
  if (!requireFile(path, "P1", "缺少后端 Ai_AutoSDLC 运行工作台", "PR 涉及 015 Ai_AutoSDLC Runs，但后端 snapshot 文件不存在，Console 无法形成可验证数据域。")) {
    return;
  }
  const text = readText(path);
  const required = [
    "def _sdlc_run_workbench",
    "\"reporter\": [_sdlc_reporter_item",
    "\"outbox\": [_sdlc_outbox_item",
    "\"eligibility\": [_sdlc_eligibility_item",
    "Reporter active 必须有 machine-verifiable proof",
    "Outbox delivered",
    "不构成 verified_loaded",
    "failed_conditions"
  ];
  for (const needle of required) {
    if (!text.includes(needle)) {
      addFinding("P1", path, "_sdlc_run_workbench", "Ai_AutoSDLC 运行工作台后端契约不完整", `后端 snapshot 必须包含 ${needle}，否则 Reporter、Outbox 或 L5 条件无法被审计。`);
    }
  }
  for (const forbidden of ["raw_payload", "download_url", "raw_url", "raw_access_url", "original_url", "pull_request_body"]) {
    if (text.includes(`"${forbidden}"`) || text.includes(`'${forbidden}'`)) {
      addFinding("P0", path, forbidden, "后端 Ai_AutoSDLC 工作台暴露红线字段", `后端工作台不得生成 ${forbidden} 字段，只能展示运行证明摘要和审计引用。`);
    }
  }
}

function checkSdlcRunWorkbenchFrontendValidator() {
  const path = "apps/agentops-console/src/data/agentOpsApiClient.js";
  if (!requireFile(path, "P1", "缺少前端快照校验器", "PR 涉及 015 Ai_AutoSDLC Runs，但前端 validator 不存在，无法阻断危险快照。")) {
    return;
  }
  const text = readText(path);
  const required = [
    "sdlcRunWorkbenchIsComplete",
    "legacySdlcRunWorkbench",
    "sdlcWorkbenchRowsMatchRuns",
    "sdlcReporterMatchesRun",
    "sdlcOutboxMatchesRun",
    "sdlcEligibilityMatchesRun",
    "sdlcDryRunState",
    "Reporter active",
    "Outbox delivered",
    "governance_loaded",
    "failed_conditions",
    "sdlcProofVerified",
    "verified_loaded"
  ];
  for (const needle of required) {
    if (!text.includes(needle)) {
      addFinding("P1", path, "sdlcRunWorkbenchIsComplete", "Ai_AutoSDLC 运行工作台状态绑定不完整", `前端 validator 必须包含 ${needle}，否则 materialized/unverified 可能被伪装成治理已激活。`);
    }
  }
}

function checkSdlcRunWorkbenchUi() {
  const path = "apps/agentops-console/src/views/SdlcRunsView.js";
  if (!requireFile(path, "P2", "缺少 Ai_AutoSDLC Runs 页面", "Ai_AutoSDLC 运行页面不存在，用户无法区分 dry-run、Reporter、Outbox 和 L5 条件。")) {
    return;
  }
  const text = readText(path);
  for (const needle of ["Reporter 与凭证", "Outbox 投递", "L5 条件", "运行证明工作台", "不执行 Outbox Replay", "verified_loaded"]) {
    if (!text.includes(needle)) {
      addFinding("P2", path, "Ai_AutoSDLC 运行", "Ai_AutoSDLC 中文工作台信号不足", `页面必须展示“${needle}”，让大陆用户明确运行证明、投递、L5 条件和只读边界。`);
    }
  }
}

function checkSdlcRunWorkbenchTestsAndContracts() {
  const contractTest = "tests/contract/test_ao15_ct_console_sdlc_run_workbench.py";
  const frontendTest = "apps/agentops-console/tests/console-contract.test.mjs";
  const specContract = "specs/015-console-sdlc-run-workbench/contracts/sdlc-run-workbench-contract.md";
  for (const path of [contractTest, frontendTest, specContract]) {
    requireFile(path, "P1", "缺少 015 契约或测试产物", `${path} 是 Ai_AutoSDLC Run Workbench 云端 review 的必要证据。`);
  }
  if (fileExists(frontendTest)) {
    const text = readText(frontendTest);
    for (const needle of [
      "legacyV1SnapshotWithoutSdlcRunWorkbench",
      "legacyUnsafeSdlcRunSnapshot",
      "sdlcSummarySpoofedVerifiedLoaded",
      "sdlcDryRunStateSpoofedPassed",
      "sdlcReporterProofSourceSpoofed",
      "sdlcRunWorkbench: null",
      "proof_state: \"verified_loaded\"",
      "保持治理加载证明",
      "reporter_status: \"active\"",
      "outbox_status: \"healthy\"",
      "evidence_level: \"L5\"",
      "raw_access_url",
      "Reporter active",
      "Outbox Replay"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", frontendTest, "validateSnapshot", "Ai_AutoSDLC 工作台前端负例覆盖不足", `console-contract.test.mjs 必须覆盖 ${needle}，否则伪治理激活或伪 L5 风险不会被云端 review 捕获。`);
      }
    }
  }
}

function checkCrossProjectCredentialHandoff() {
  const credentialApi = "src/agentops/api/credentials.py";
  const credentialTest = "tests/contract/test_ao_ct_002_credential_issue.py";
  const openapi = "specs/001-agentops-trusted-loop/contracts/agentops-api.openapi.yaml";
  const fixtureDir = "contracts/cross-project/fixtures";
  for (const path of [
    `${fixtureDir}/signed_installation_assertion.v1.json`,
    `${fixtureDir}/device_proof.v1.json`,
    `${fixtureDir}/agentops_credential_handoff.v1.json`,
    `${fixtureDir}/credential_issue_response.v1.json`,
    `${fixtureDir}/unsupported_schema.v2.json`
  ]) {
    requireFile(path, "P1", "缺少跨项目 Credential Handoff fixture", `${path} 是 AgentOps 消费 Agent Store 008 producer 契约的必要证据。`);
  }
  if (requireFile(credentialApi, "P1", "缺少 Credential Issue API", "AgentOps 必须实现 agentops_credential_handoff.v1 consumer。")) {
    const text = readText(credentialApi);
    for (const needle of [
      "agentops_credential_handoff.v1",
      "signed_installation_assertion.v1",
      "device_proof.v1",
      "json-c14n-v1",
      "agent-store",
      "assertion_hash",
      "device_public_key_thumbprint",
      "BOOTSTRAP_ASSERTION_HASH_MISMATCH",
      "BOOTSTRAP_IDEMPOTENCY_CONFLICT",
      "send_signature_test_event"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", credentialApi, "issue_credentials", "Credential Handoff consumer 契约不完整", `Credential Issue 必须包含 ${needle}，否则无法消费 Agent Store 008 handoff。`);
      }
    }
    if (/algorithm"\]\s*!=\s*device_proof\["algorithm"|algorithm'\]\s*!=\s*device_proof\['algorithm'/.test(text)) {
      addFinding("P1", credentialApi, "algorithm", "错误要求 assertion 与 device proof algorithm 相等", "跨项目 appendix 明确 device proof algorithm 不需要等于 assertion algorithm，AgentOps 不能用旧约束误拒。");
    }
  }
  if (requireFile(credentialTest, "P1", "缺少 Credential Handoff 契约测试", "必须覆盖 CCT-001/CCT-002/CCT-003/CCT-006。")) {
    const text = readText(credentialTest);
    for (const needle of [
      "test_cct_001_agent_store_handoff_fixture_issues_credential",
      "test_cct_002_device_proof_binds_installation_device_and_assertion_hash",
      "test_cct_003_response_echoes_agent_store_consumable_status",
      "test_cct_006_unknown_major_schema_returns_unsupported_error",
      "BOOTSTRAP_IDEMPOTENCY_CONFLICT",
      "HS256",
      "Ed25519"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", credentialTest, "issue_credentials", "Credential Handoff 测试覆盖不足", `测试必须覆盖 ${needle}。`);
      }
    }
  }
  if (requireFile(openapi, "P2", "缺少 AgentOps OpenAPI 契约", "OpenAPI 必须同步 Credential Handoff v1 外部字段。")) {
    const text = readText(openapi);
    for (const needle of [
      "agentops_credential_handoff.v1",
      "signed_installation_assertion.v1",
      "device_proof.v1",
      "json-c14n-v1",
      "bootstrap_status",
      "send_signature_test_event"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P2", openapi, "CredentialIssueRequest", "OpenAPI 未同步 Credential Handoff v1", `OpenAPI 必须包含 ${needle}。`);
      }
    }
  }
}

function checkSignedTestEventActivation() {
  const ingestionApi = "src/agentops/api/ingestion.py";
  const repository = "src/agentops/storage/repository.py";
  const envelope = "src/agentops/core/envelope.py";
  const contractTest = "tests/contract/test_ao17_ct_signed_test_event_activation.py";
  const spec = "specs/017-signed-test-event-credential-activation/spec.md";
  for (const path of [ingestionApi, repository, envelope, contractTest, spec]) {
    requireFile(path, "P1", "缺少 signed test event 激活契约", `${path} 是 AgentOps 017 signed test event 激活闭环的必要证据。`);
  }
  if (fileExists(envelope)) {
    const text = readText(envelope);
    for (const needle of ["signature_test_event", "SIGNATURE_TEST_PAYLOAD_REQUIRED_FIELDS", "bootstrap_id", "credential_id", "token_id", "device_key_id"]) {
      if (!text.includes(needle)) {
        addFinding("P1", envelope, "SIGNATURE_TEST_EVENT_TYPE", "signature_test_event payload 契约不完整", `EventEnvelope 必须冻结 ${needle}，否则 Ai_AutoSDLC signed test event 无法稳定互通。`);
      }
    }
  }
  if (fileExists(repository)) {
    const text = readText(repository);
    for (const needle of [
      "validate_signature_test_event",
      "mark_signature_test_verified",
      "SIGNATURE_TEST_CREDENTIAL_NOT_FOUND",
      "EVENT_INGESTION_TOKEN_MISMATCH",
      "EVENT_DEVICE_KEY_MISMATCH",
      "EVENT_IDENTITY_MISMATCH",
      "signature_verified"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", repository, "validate_signature_test_event", "signed test event 绑定校验不完整", `Repository 必须包含 ${needle}，否则 credential_issued 可能被误推进为 verified。`);
      }
    }
  }
  if (fileExists(ingestionApi)) {
    const text = readText(ingestionApi);
    for (const needle of ["SIGNATURE_TEST_EVENT_TYPE", "validate_signature_test_event", "mark_signature_test_verified"]) {
      if (!text.includes(needle)) {
        addFinding("P1", ingestionApi, "ingest_events_batch", "Ingestion 未接入 signed test event 激活", `Ingestion 必须包含 ${needle}，否则 signed test event 不会推进 bootstrap 状态。`);
      }
    }
  }
  if (fileExists(contractTest)) {
    const text = readText(contractTest);
    for (const needle of [
      "test_ao17_cct_004_signed_test_event_verifies_bootstrap",
      "SIGNATURE_TEST_CREDENTIAL_NOT_FOUND",
      "EVENT_INGESTION_TOKEN_MISMATCH",
      "EVENT_DEVICE_KEY_INACTIVE",
      "EVENT_IDENTITY_MISMATCH",
      "EVENT_PAYLOAD_INVALID",
      "deduplicated",
      "signature_verified"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", contractTest, "test_ao17_cct_004", "AO17-CCT-004 测试覆盖不足", `CCT-004 必须覆盖 ${needle}。`);
      }
    }
  }
  if (fileExists(spec) && !readText(spec).includes("不把 `signature_verified`")) {
    addFinding("P1", spec, "非目标", "缺少 verified_loaded 边界", "017 spec 必须明确 signature_verified 不等于 verified_loaded 或 L5。");
  }
}

function checkAgentStoreCredentialStatusQuery() {
  const credentialApi = "src/agentops/api/credentials.py";
  const server = "src/agentops/api/server.py";
  const openapi = "specs/001-agentops-trusted-loop/contracts/agentops-api.openapi.yaml";
  const contractTest = "tests/contract/test_ao18_ct_agent_store_credential_status.py";
  const spec = "specs/018-agent-store-credential-status-query/spec.md";
  for (const path of [credentialApi, server, openapi, contractTest, spec]) {
    requireFile(path, "P1", "缺少 Agent Store credential status query 契约", `${path} 是 Agent Store 009 只读消费 AgentOps credential/bootstrap 状态的必要证据。`);
  }
  if (fileExists(credentialApi)) {
    const text = readText(credentialApi);
    for (const needle of [
      "agentops_credential_status.v1",
      "get_credential_status",
      "display_only_no_active_inference",
      "infer_active",
      "issue_ingestion_token",
      "not_asserted",
      "display_activation_result",
      "CREDENTIAL_STATUS_NOT_FOUND"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", credentialApi, "get_credential_status", "Credential status query 只读边界不完整", `Credential status query 必须包含 ${needle}，否则 Agent Store 009 可能本地推导 active 或缺少状态事实。`);
      }
    }
  }
  if (fileExists(server) && !readText(server).includes("/v1/bootstrap/credentials/")) {
    addFinding("P1", server, "do_GET", "HTTP status route 缺失", "Agent Store 009 需要 GET /v1/bootstrap/credentials/{bootstrap_id} 读取 AgentOps 状态回显。");
  }
  if (fileExists(openapi)) {
    const text = readText(openapi);
    for (const needle of ["CredentialStatusResponse", "agentops_credential_status.v1", "display_only_no_active_inference", "display_activation_result"]) {
      if (!text.includes(needle)) {
        addFinding("P1", openapi, "CredentialStatusResponse", "OpenAPI 未同步 credential status query", `OpenAPI 必须包含 ${needle}。`);
      }
    }
  }
  if (fileExists(contractTest)) {
    const text = readText(contractTest);
    for (const needle of [
      "test_ao18_cct_003_agent_store_reads_credential_issued_status",
      "test_ao18_cct_003b_agent_store_reads_signature_verified_status",
      "CREDENTIAL_STATUS_NOT_FOUND",
      "display_only_no_active_inference",
      "token_value",
      "private_key",
      "raw_payload",
      "download_url",
      "GET"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", contractTest, "test_ao18", "AO18 credential status 测试覆盖不足", `AO18 CCT 必须覆盖 ${needle}。`);
      }
    }
  }
}

function checkConsoleCredentialHandoffWorkbench() {
  const backend = "src/agentops/api/console_snapshot.py";
  const view = "apps/agentops-console/src/views/CredentialHandoffView.js";
  const app = "apps/agentops-console/src/App.js";
  const validator = "apps/agentops-console/src/data/agentOpsApiClient.js";
  const contractTest = "tests/contract/test_ao19_ct_console_credential_handoff_workbench.py";
  const spec = "specs/019-console-credential-handoff-workbench/spec.md";
  for (const path of [backend, view, app, validator, contractTest, spec]) {
    requireFile(path, "P1", "缺少 Console credential handoff 工作台契约", `${path} 是 AgentOps 019 凭证联调控制台工作台的必要证据。`);
  }
  if (fileExists(backend)) {
    const text = readText(backend);
    for (const needle of [
      "\"credential-handoff\"",
      "\"credentialHandoff\"",
      "def _credential_handoff_workbench",
      "agentops_credential_status.v1",
      "display_only_no_active_inference",
      "not_asserted",
      "不把 credential 或签名测试事件提升为 verified_loaded 或 L5"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", backend, "_credential_handoff_workbench", "后端 credential handoff 工作台不完整", `Console snapshot 必须包含 ${needle}。`);
      }
    }
  }
  if (fileExists(view)) {
    const text = readText(view);
    for (const needle of ["凭证联调", "凭证状态回显", "签名测试通过", "Agent Store 只消费展示字段", "不得本地推导 active"]) {
      if (!text.includes(needle)) {
        addFinding("P2", view, "凭证联调", "凭证联调中文界面信号不足", `页面必须展示“${needle}”，让大陆用户理解 AgentOps/Agent Store 边界。`);
      }
    }
  }
  if (fileExists(app) && !readText(app).includes("CredentialHandoffView")) {
    addFinding("P1", app, "views", "凭证联调页面未接入路由", "App.js 必须接入 CredentialHandoffView。");
  }
  if (fileExists(validator)) {
    const text = readText(validator);
    for (const needle of [
      "credentialHandoffIsSafe",
      "containsForbiddenCredentialMaterial",
      "display_only_no_active_inference",
      "not_asserted",
      "不得本地推导 active",
      "不构成 verified_loaded 或 L5"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", validator, "credentialHandoffIsSafe", "前端 credential handoff validator 不完整", `validator 必须包含 ${needle}，否则危险快照可能绕过前端。`);
      }
    }
  }
  if (fileExists(contractTest)) {
    const text = readText(contractTest);
    for (const needle of [
      "test_ao19_ct_001_console_declares_credential_handoff_route_and_shape",
      "test_ao19_ct_002_repository_snapshot_shows_agentops_status_without_store_inference",
      "test_ao19_ct_003_signature_verified_is_display_result_not_verified_loaded",
      "test_ao19_ct_004_credential_workbench_has_no_secret_or_raw_material",
      "token_value",
      "private_key"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", contractTest, "test_ao19", "AO19 凭证联调契约测试覆盖不足", `AO19 测试必须覆盖 ${needle}。`);
      }
    }
  }
}

function checkCredentialRevocationPropagation() {
  const credentialsApi = "src/agentops/api/credentials.py";
  const ingestionApi = "src/agentops/api/ingestion.py";
  const repository = "src/agentops/storage/repository.py";
  const server = "src/agentops/api/server.py";
  const validator = "apps/agentops-console/src/data/agentOpsApiClient.js";
  const view = "apps/agentops-console/src/views/CredentialHandoffView.js";
  const contractTest = "tests/contract/test_ao20_ct_credential_revocation_propagation.py";
  const spec = "specs/020-credential-revocation-propagation/spec.md";
  const openapi = "specs/001-agentops-trusted-loop/contracts/agentops-api.openapi.yaml";
  for (const path of [credentialsApi, ingestionApi, repository, server, validator, view, contractTest, spec, openapi]) {
    requireFile(path, "P1", "缺少 credential revocation propagation 契约", `${path} 是 AgentOps 020 凭证撤销传播的必要证据。`);
  }
  if (fileExists(credentialsApi)) {
    const text = readText(credentialsApi);
    for (const needle of [
      "agentops_credential_revocation.v1",
      "revoke_credentials",
      "reissue_credential",
      "CREDENTIAL_REVOCATION_SCHEMA_UNSUPPORTED",
      "display_only_no_active_inference",
      "not_asserted"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", credentialsApi, "revoke_credentials", "凭证撤销 API 契约不完整", `credentials API 必须包含 ${needle}。`);
      }
    }
  }
  if (fileExists(repository)) {
    const text = readText(repository);
    for (const needle of [
      "def revoke_credentials",
      "def validate_known_revocation_state",
      "EVENT_CREDENTIAL_REVOKED",
      "bootstrap_status",
      "revoked",
      "revocation_scope"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", repository, "revoke_credentials", "仓储撤销状态传播不完整", `repository 必须包含 ${needle}，否则 revoked 可能继续接入事件。`);
      }
    }
  }
  if (fileExists(ingestionApi) && !readText(ingestionApi).includes("validate_known_revocation_state")) {
    addFinding("P1", ingestionApi, "validate_event_envelope", "事件接入未检查撤销状态", "企业事件接入必须在写入前检查已知 revoked 凭证或身份。");
  }
  if (fileExists(server) && (!readText(server).includes("/v1/bootstrap/credentials/") || !readText(server).includes("/revoke"))) {
    addFinding("P1", server, "do_POST", "HTTP 撤销路由缺失", "server.py 必须暴露 POST /v1/bootstrap/credentials/{bootstrap_id}/revoke。");
  }
  if (fileExists(validator)) {
    const text = readText(validator);
    for (const needle of [
      "revocationFieldsMatchStatus",
      "reissue_credential",
      "revoked 必须阻断后续签名测试和企业事件接入",
      "summary.revoked"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", validator, "credentialHandoffIsSafe", "前端撤销态 validator 不完整", `validator 必须包含 ${needle}，否则 revoked 行可能被篡改成 active 展示。`);
      }
    }
  }
  if (fileExists(view)) {
    const text = readText(view);
    for (const needle of ["已撤销", "重新签发凭证", "撤销原因", "撤销范围"]) {
      if (!text.includes(needle)) {
        addFinding("P2", view, "凭证联调", "撤销态中文界面信号不足", `页面必须展示“${needle}”，让运维人员明确撤销和重新签发边界。`);
      }
    }
  }
  if (fileExists(contractTest)) {
    const text = readText(contractTest);
    for (const needle of [
      "test_ao20_ct_001_revoke_credentials_updates_agentops_status",
      "test_ao20_ct_002_revoked_signature_test_event_is_rejected",
      "test_ao20_ct_003_revoked_known_enterprise_event_is_rejected",
      "test_ao20_ct_003b_revoked_duplicate_identity_is_rejected_after_active_match",
      "test_ao20_ct_004_unknown_revocation_schema_is_rejected",
      "test_ao20_ct_005_http_revoke_route_returns_json_and_cors",
      "test_ao20_ct_006_revocation_not_found_returns_stable_error",
      "EVENT_CREDENTIAL_REVOKED",
      "CREDENTIAL_REVOCATION_SCHEMA_UNSUPPORTED"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", contractTest, "test_ao20", "AO20 撤销传播契约测试覆盖不足", `AO20 测试必须覆盖 ${needle}。`);
      }
    }
  }
  if (fileExists(openapi)) {
    const text = readText(openapi);
    for (const needle of [
      "/v1/bootstrap/credentials/{bootstrap_id}/revoke",
      "CredentialRevocationRequest",
      "CredentialRevocationResponse",
      "agentops_credential_revocation.v1",
      "reissue_credential"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", openapi, "CredentialRevocation", "OpenAPI 未声明撤销契约", `OpenAPI 必须包含 ${needle}。`);
      }
    }
  }
}

function checkCredentialReissueAfterRevocation() {
  const credentialsApi = "src/agentops/api/credentials.py";
  const repository = "src/agentops/storage/repository.py";
  const server = "src/agentops/api/server.py";
  const validator = "apps/agentops-console/src/data/agentOpsApiClient.js";
  const view = "apps/agentops-console/src/views/CredentialHandoffView.js";
  const contractTest = "tests/contract/test_ao21_ct_credential_reissue_after_revocation.py";
  const spec = "specs/021-credential-reissue-after-revocation/spec.md";
  const openapi = "specs/001-agentops-trusted-loop/contracts/agentops-api.openapi.yaml";
  for (const path of [credentialsApi, repository, server, validator, view, contractTest, spec, openapi]) {
    requireFile(path, "P1", "缺少 credential reissue after revocation 契约", `${path} 是 AgentOps 021 凭证撤销后重新签发的必要证据。`);
  }
  if (fileExists(credentialsApi)) {
    const text = readText(credentialsApi);
    for (const needle of [
      "agentops_credential_reissue.v1",
      "reissue_credentials",
      "CREDENTIAL_REISSUE_SOURCE_NOT_REVOKED",
      "CREDENTIAL_REISSUE_TARGET_INVALID",
      "CREDENTIAL_REISSUE_HANDOFF_MISMATCH",
      "send_signature_test_event",
      "display_only_no_active_inference",
      "not_asserted"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", credentialsApi, "reissue_credentials", "凭证重新签发 API 契约不完整", `credentials API 必须包含 ${needle}。`);
      }
    }
  }
  if (fileExists(repository)) {
    const text = readText(repository);
    for (const needle of [
      "def mark_credentials_reissued",
      "def remove_unissued_bootstrap_session",
      "revocation_resolution",
      "reissued_bootstrap_id",
      "replacement_token_matches",
      "EVENT_CREDENTIAL_REVOKED"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", repository, "mark_credentials_reissued", "仓储 reissue 状态传播不完整", `repository 必须包含 ${needle}，否则旧凭证可能绕过撤销或留下半成品 session。`);
      }
    }
  }
  if (fileExists(server)) {
    const text = readText(server);
    for (const needle of ["/reissue", "reissue_credentials", "Idempotency-Key"]) {
      if (!text.includes(needle)) {
        addFinding("P1", server, "do_POST", "HTTP 重新签发路由缺失", `server.py 必须包含 ${needle}。`);
      }
    }
  }
  if (fileExists(validator)) {
    const text = readText(validator);
    for (const needle of [
      "reissueFieldsMatchResolution",
      "summary.reissued",
      "revocation_resolution",
      "reissued_bootstrap_id",
      "旧 token 仍必须被拒绝"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", validator, "credentialHandoffIsSafe", "前端 reissue validator 不完整", `validator 必须包含 ${needle}，否则 reissued 行可能被篡改展示。`);
      }
    }
  }
  if (fileExists(view)) {
    const text = readText(view);
    for (const needle of ["已重新签发", "重新签发状态", "新启动会话", "新凭证"]) {
      if (!text.includes(needle)) {
        addFinding("P2", view, "凭证联调", "重新签发中文界面信号不足", `页面必须展示“${needle}”，让运维人员明确替代 credential 边界。`);
      }
    }
  }
  if (fileExists(contractTest)) {
    const text = readText(contractTest);
    for (const needle of [
      "test_ao21_ct_001_reissue_revoked_credential_returns_new_agentops_credential",
      "test_ao21_ct_001b_reissue_uses_new_bootstrap_for_replacement_ids",
      "test_ao21_ct_002_reissued_credential_passes_signature_test_but_old_token_stays_revoked",
      "test_ao21_ct_003_reissue_requires_new_nonce_and_new_bootstrap",
      "test_ao21_ct_003b_reissue_rejects_reused_nonce_without_orphan_session",
      "test_ao21_ct_004_reissue_rejects_non_revoked_source",
      "test_ao21_ct_005_reissue_retry_returns_same_result",
      "test_ao21_ct_006_http_reissue_route_returns_json_and_cors",
      "test_ao21_ct_007_reissued_identity_requires_replacement_token",
      "BOOTSTRAP_REPLAY_DETECTED",
      "EVENT_CREDENTIAL_REVOKED"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", contractTest, "test_ao21", "AO21 重新签发契约测试覆盖不足", `AO21 测试必须覆盖 ${needle}。`);
      }
    }
  }
  if (fileExists(openapi)) {
    const text = readText(openapi);
    for (const needle of [
      "/v1/bootstrap/credentials/{bootstrap_id}/reissue",
      "CredentialReissueRequest",
      "CredentialReissueResponse",
      "agentops_credential_reissue.v1"
    ]) {
      if (!text.includes(needle)) {
        addFinding("P1", openapi, "CredentialReissue", "OpenAPI 未声明重新签发契约", `OpenAPI 必须包含 ${needle}。`);
      }
    }
  }
}

function stripSafeNegations(value) {
  return value
    .replace(/不自动批准/g, "")
    .replace(/不自动写回/g, "")
    .replace(/不自动下架/g, "")
    .replace(/不自动降推荐/g, "")
    .replace(/不触发自动生命周期动作/g, "")
    .replace(/不执行自动生命周期动作/g, "")
    .replace(/低置信不自动下架/g, "");
}

function checkUnsafeLifecycleText(paths) {
  const sourcePaths = paths.filter((path) =>
    /^(src|apps\/agentops-console\/src)\//.test(path) &&
    !path.endsWith("agentOpsApiClient.js")
  );
  for (const path of sourcePaths) {
    if (!fileExists(path)) {
      continue;
    }
    const lines = readText(path).split("\n");
    lines.forEach((line, index) => {
      const redline = stripSafeNegations(line);
      if (/自动(?:批准|写回|下架|降推荐|发布|合并|执行)|写回 Agent Store|写回AgentStore/.test(redline)) {
        findings.push({
          priority: "P1",
          file: path,
          line: index + 1,
          title: "发现可能的自动生命周期动作",
          body: "AgentOps 当前阶段只允许只读复核和人工申请路径，不能在前端或后端业务视图中引入自动批准、自动写回或自动生命周期动作。"
        });
      }
    });
  }
}

function checkWorkflowItself(paths) {
  if (!paths.includes(".github/workflows/agentops-adversarial-pr-review.yml")) {
    return;
  }
  const path = ".github/workflows/agentops-adversarial-pr-review.yml";
  const text = readText(path);
  for (const needle of ["pull-requests: write", "issues: write", "node scripts/agentops-pr-review.mjs", "Adversarial Review Result"]) {
    if (!text.includes(needle)) {
      addFinding("P1", path, "permissions", "云端 Review Bot 工作流不完整", `自建云端 review 必须包含 ${needle}，否则无法像 review 机器人一样回写 PR 或形成强制检查。`);
    }
  }
}

function buildMarkdown(paths) {
  const blockerCount = findings.filter((item) => ["P0", "P1"].includes(item.priority)).length;
  const header = blockerCount
    ? `发现 ${blockerCount} 个阻断级问题`
    : "未发现 P0/P1 阻断问题";
  const lines = [
    REVIEW_MARKER,
    "## AgentOps 云端对抗 Review",
    "",
    `结论：**${header}**`,
    "",
    "审查范围：",
    `- Base：\`${baseRef}\``,
    `- Head：\`${headRef}\``,
    `- 变更文件数：${paths.length}`,
    "",
    "审查规则：",
    "- Evidence Vault 原文访问红线：不得出现原文、下载链接、raw URL、PR 原文、diff 或代码片段。",
    "- 状态绑定红线：`permission_denied` 和 `redaction_failed` 不能被篡改为 active/approved 授权态。",
    "- 审批 Grant 红线：`pending`、`escalated`、`revoked` 不得被篡改为有效 Grant 或已授权态。",
    "- 连接器健康红线：`materialized/unverified` 不得被当作 `verified_loaded`，降级连接器不得提升为健康态，DLQ/Outbox Replay 不得在 Console 执行。",
    "- Ai_AutoSDLC 红线：Reporter active、Outbox delivered 和 L5 healthy 必须由 verified_loaded 机器证明支撑。",
    "- 生命周期红线：不得自动批准、自动写回、自动下架、自动发布或自动合并。",
    "- 前端体验红线：大陆用户界面以中文为主，Evidence Vault、人工审批工作台、连接器健康工作台与 Ai_AutoSDLC 运行工作台必须展示申请、授权、审计轨迹、DLQ、回放和只读边界。",
    ""
  ];

  if (findings.length) {
    lines.push("### Findings", "");
    findings
      .sort((left, right) => priorityRank(left.priority) - priorityRank(right.priority))
      .forEach((finding) => {
        lines.push(`- **${finding.priority} ${finding.title}**`);
        lines.push(`  - 位置：\`${finding.file}:${finding.line}\``);
        lines.push(`  - 说明：${finding.body}`);
      });
  } else {
    lines.push("### Findings", "", "- 未发现需要阻断合入的问题。");
  }
  lines.push("", "_该报告由仓库内 `scripts/agentops-pr-review.mjs` 在 GitHub Actions 云端生成。_");
  return lines.join("\n");
}

function priorityRank(priority) {
  return { P0: 0, P1: 1, P2: 2, P3: 3 }[priority] ?? 9;
}

async function githubRequest(method, url, body) {
  const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
  if (!token) {
    throw new Error("GITHUB_TOKEN/GH_TOKEN is required to post review comments");
  }
  const response = await fetch(url, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "X-GitHub-Api-Version": "2022-11-28"
    },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${method} ${url} failed: ${response.status} ${text}`);
  }
  return response.json();
}

async function postOrUpdateComment(markdown) {
  const repository = process.env.GITHUB_REPOSITORY;
  if (!repository || !prNumber) {
    return;
  }
  const apiBase = process.env.GITHUB_API_URL || "https://api.github.com";
  const commentsUrl = `${apiBase}/repos/${repository}/issues/${prNumber}/comments`;
  const comments = await githubRequest("GET", commentsUrl);
  const existing = comments.find((comment) =>
    comment.user?.type === "Bot" &&
    typeof comment.body === "string" &&
    comment.body.includes(REVIEW_MARKER)
  );
  if (existing) {
    await githubRequest("PATCH", existing.url, { body: markdown });
    return;
  }
  await githubRequest("POST", commentsUrl, { body: markdown });
}

async function main() {
  const paths = changedFiles();
  checkEvidenceVaultBackend();
  checkEvidenceVaultFrontendValidator();
  checkEvidenceVaultUi();
  checkEvidenceVaultTestsAndContracts();
  checkApprovalWorkbenchBackend();
  checkApprovalWorkbenchFrontendValidator();
  checkApprovalWorkbenchUi();
  checkApprovalWorkbenchTestsAndContracts();
  checkConnectorWorkbenchBackend();
  checkConnectorWorkbenchFrontendValidator();
  checkConnectorWorkbenchUi();
  checkConnectorWorkbenchTestsAndContracts();
  checkSdlcRunWorkbenchBackend();
  checkSdlcRunWorkbenchFrontendValidator();
  checkSdlcRunWorkbenchUi();
  checkSdlcRunWorkbenchTestsAndContracts();
  checkCrossProjectCredentialHandoff();
  checkSignedTestEventActivation();
  checkAgentStoreCredentialStatusQuery();
  checkConsoleCredentialHandoffWorkbench();
  checkCredentialRevocationPropagation();
  checkCredentialReissueAfterRevocation();
  checkUnsafeLifecycleText(paths);
  checkWorkflowItself(paths);

  const markdown = buildMarkdown(paths);
  console.log(markdown);

  if (shouldPostComment) {
    try {
      await postOrUpdateComment(markdown);
    } catch (error) {
      console.warn(`PR review comment skipped: ${error.message}`);
    }
  }

  const blockerCount = findings.filter((finding) => ["P0", "P1"].includes(finding.priority)).length;
  if (blockerCount > 0) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
