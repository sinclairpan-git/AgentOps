# 任务执行日志：Console Evidence Vault 访问工作台

**功能编号**：`012-console-evidence-vault-workbench`
**执行日期**：2026-05-07
**状态**：本地实现完成，待 PR 评审

## 执行记录

| 任务 | 状态 | 说明 |
|---|---|---|
| T11 冻结 012 规格 | 完成 | 已新增规格、计划、任务与契约 |
| T21 扩展 Console snapshot | 完成 | 已新增 `evidenceVault` 数据域 |
| T31 新增 Evidence Vault 访问工作台 | 完成 | 证据检索页已展示申请、限时授权、审计轨迹和保护规则 |
| T41 契约与回归测试 | 完成 | 后端契约、前端契约、构建、ruff、AI-SDLC 约束和 program validate 已通过 |

## 统一验证命令

- **验证画像**：code-change
- **改动范围**：`src/agentops/api/console_snapshot.py`、`tests/contract/test_ao12_ct_console_evidence_vault_workbench.py`、`apps/agentops-console/src/*`、`apps/agentops-console/tests/console-contract.test.mjs`、`specs/012-console-evidence-vault-workbench/*`
- `uv run pytest tests/contract/test_ao12_ct_console_evidence_vault_workbench.py -q`
- `uv run pytest tests -q`
- `uv run ruff check src tests`
- `npm test`
- `npm run build`
- `uv run ai-sdlc verify constraints`
- `uv run ai-sdlc program truth sync --execute --yes`
- `uv run ai-sdlc program validate`
- `uv run ai-sdlc run --dry-run`

## 当前边界

- 本阶段只生成 Evidence Vault 访问申请、授权和审计摘要。
- 不展示 Evidence Vault 原文。
- 不生成下载链接、raw URL 或 `raw_payload`。
- 不接真实 IAM、多租户权限或生产存储访问。
- 不自动批准、不自动写回、不触发生产动作。

## 代码审查

- 自检结论：Evidence Vault 工作台为只读访问治理摘要，不实现真实原文读取。
- 安全边界：validator 递归拒绝 raw 字段、下载 URL、原文 URL、PR 原文、diff、patch 和代码片段。
- 状态绑定：`permission_denied`、`redaction_failed`、`approved_limited`、`summary_only` 已与 request/grant/audit 状态强绑定，只有 `approved_limited` 可展示 active 限时授权。
- UX 对抗评审：未发现 P0/P1 阻断项，复核通过。
- AI-Native 对抗评审 P1：初版未把 Vault 状态绑定回 `evidence.raw_access_state`，可能接受拒绝态被篡成授权态。已修复为按 evidence_id 反查并强绑定状态/动作/TTL，补充前端负例；复核通过。

## 已完成验证

- `uv run pytest tests/contract/test_ao12_ct_console_evidence_vault_workbench.py -q`：通过。
- `uv run pytest tests -q`：通过。
- `uv run ruff check src tests`：通过。
- `npm test`：通过。
- `npm run build`：通过。
- `uv run ai-sdlc verify constraints`：通过。
- `uv run ai-sdlc program validate`：PASS，保留 `prd_path is empty` 非阻断提示。
- `uv run ai-sdlc run --dry-run`：PASS，adapter 仍为 `materialized/unverified`。
