# 开发总结：Console Evidence Vault 访问工作台

**功能编号**：`012-console-evidence-vault-workbench`

## 已完成

- Console snapshot 新增 `evidenceVault` 只读数据域。
- Evidence Explorer 新增 Evidence Vault 访问工作台，展示原文访问申请、限时授权、审计轨迹和保护规则。
- 前端 validator 已补充 `evidenceVault` strict schema、旧版 v1 安全空态和危险字段负例。
- AO12 后端契约测试已覆盖数据域、字段、安全红线、拒绝/脱敏失败下一步和空仓库空态。

## 安全边界

- 默认不展示原文，只展示脱敏摘要、哈希和审计引用。
- 不提供原文下载、raw URL、PR 原文、diff、patch 或代码片段。
- 权限拒绝和脱敏失败只进入人工申请/修复路径，不自动批准、不自动写回。

## 已验证

- `uv run pytest tests/contract/test_ao12_ct_console_evidence_vault_workbench.py -q`
- `uv run pytest tests -q`
- `uv run ruff check src tests`
- `npm test`
- `npm run build`
- `uv run ai-sdlc verify constraints`
- `uv run ai-sdlc program validate`
- `uv run ai-sdlc run --dry-run`

## 待完成

- GitHub PR `@codex review` 与 checks。
