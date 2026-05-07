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
    "- 生命周期红线：不得自动批准、自动写回、自动下架、自动发布或自动合并。",
    "- 前端体验红线：大陆用户界面以中文为主，Evidence Vault、人工审批工作台与连接器健康工作台必须展示申请、授权、审计轨迹、DLQ、回放和只读边界。",
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
