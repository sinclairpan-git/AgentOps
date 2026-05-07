# 规格：Console Evidence Vault 访问工作台

**功能编号**：`012-console-evidence-vault-workbench`

**依赖**：`011-console-quality-adoption-insights`

## 目标

承接 AgentOps PRD 中“Evidence Vault 原文访问需要审批、限时授权、审计留痕和脱敏失败可解释”的目标，把证据检索页从摘要列表增强为只读访问工作台。用户必须能看到原文访问申请、限时授权、审计轨迹和安全保护规则，但不能在控制台看到原文、下载链接或生产写动作。

## 范围

- Console snapshot 新增 `evidenceVault` 只读数据域。
- `evidenceVault` 必须包含 `requests`、`grants`、`auditTrail` 和 `guardrails`。
- Evidence Explorer 展示原文访问申请、限时授权、审计轨迹和“默认不展示原文”的保护规则。
- 前端 validator 必须兼容旧版 v1 快照缺失 `evidenceVault` 的情况，并提供安全空态。
- 所有文案面向中国大陆用户；固定名词 AgentOps、Evidence Vault、TTL、L5、Grant 可保留。

## 非目标

- 不展示 Evidence Vault 原文。
- 不生成下载链接、原文 URL、raw access URL。
- 不实现真实 IAM、多租户权限或生产存储访问。
- 不自动批准、不自动写回、不触发生产动作。

## 验收标准

- AO12-CT-001：snapshot 必须包含 `evidenceVault.requests`、`evidenceVault.grants`、`evidenceVault.auditTrail` 和 `evidenceVault.guardrails`。
- AO12-CT-002：每条申请、授权和审计节点必须具备契约字段，并能关联 `evidence_id`、`run_id` 或 `audit_id`。
- AO12-CT-003：`evidenceVault` 不得包含 `raw_payload`、`download_url`、`raw_url`、`raw_access_url`、URL 或 PR 原文类字段。
- AO12-CT-004：`redaction_failed` 与 `permission_denied` 必须给出安全下一步，只能查看哈希告警或补充申请理由。
- AO12-CT-005：前端必须展示中文“原文访问申请”“限时授权”“审计轨迹”“默认不展示原文”等文案，并在 schema 异常时安全回退。
