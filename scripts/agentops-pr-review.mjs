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
    "- 生命周期红线：不得自动批准、自动写回、自动下架、自动发布或自动合并。",
    "- 前端体验红线：大陆用户界面以中文为主，Evidence Vault 必须展示申请、限时授权、审计轨迹和默认不展示原文。",
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
  checkUnsafeLifecycleText(paths);
  checkWorkflowItself(paths);

  const markdown = buildMarkdown(paths);
  console.log(markdown);

  if (shouldPostComment) {
    await postOrUpdateComment(markdown);
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
