# 计划：Console Evidence Vault 访问工作台

## 设计决策

- 将 Evidence Vault 工作台放入现有证据检索页，不新增导航，保持证据上下文连续。
- 采用 snapshot 派生数据，不接真实 Evidence Store、IAM 或生产原文访问。
- 原文访问以申请、授权、审计摘要表达，前端和后端契约均拒绝原文 URL、下载 URL 和 `raw_payload`。
- 红线状态只给出只读下一步：脱敏失败只查看哈希告警，权限拒绝只补充申请理由。

## 批次

### Batch 1：规格与契约

- 新增 012 spec/plan/tasks/contract。
- 明确 AO12-CT-001 到 AO12-CT-005。

### Batch 2：后端视图模型

- 在 Console snapshot 中新增 `evidenceVault`。
- 从现有 evidence 摘要派生 requests、grants、auditTrail 和 guardrails。

### Batch 3：前端证据工作台

- 增强 `EvidenceExplorerView`，展示 Evidence Vault 工作台。
- 更新 mock 数据、前端 schema validator 和中文文案契约。

### Batch 4：验证与评审

- 新增 AO12 契约测试。
- 跑后端契约、前端契约、构建、ruff、AI-SDLC 约束和 program validate。
- 对抗评审通过后提交 PR。

## 风险

| 风险 | 控制 |
|---|---|
| 用户误以为可直接查看原文 | 页面和契约明确“默认不展示原文” |
| 前端混入下载链接或 raw URL | validator 递归拒绝危险字段、URL 和 PR 原文 |
| 权限拒绝被误解为自动申请通过 | 只显示补充申请理由，不自动批准 |
| 脱敏失败泄露摘要正文 | 红线状态只展示哈希告警与审计摘要 |
