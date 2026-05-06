# 计划：Console 处置审计时间线

## 设计决策

- 复用 `actionWorkbench.details`，不新增独立页面，避免把处置上下文拆散。
- 时间线和审计包摘要由后端 snapshot 生成，前端只做只读展示。
- 审计包是 `summary_only` 视图模型，不提供下载 URL、原文链接或写操作按钮。
- Agent Store gap 仍按保护路径优先生成，避免运营入口可达但详情缺失。

## 批次

### Batch 1：规格与契约

- 新增 010 spec/plan/tasks/contract。
- 明确 AO10-CT-001 到 AO10-CT-005。

### Batch 2：后端视图模型

- 扩展 `_action_detail`，生成 `timeline` 与 `audit_packet`。
- 覆盖审批、证据、风险、Agent Store gap 四类处置详情。

### Batch 3：前端只读展示

- 在 `AppShell` 处置详情抽屉展示时间线和审计包摘要。
- 更新 schema validator 和 mock 数据。

### Batch 4：验证与评审

- 新增 AO10 契约测试。
- 跑后端契约、前端契约、构建、ruff、AI-SDLC 约束和 program validate。
- 对抗评审通过后提交 PR。

## 风险

| 风险 | 控制 |
|---|---|
| 用户误以为可以导出原文 | 文案固定为只读复核包，不提供下载 URL |
| 时间线被理解为真实生产动作记录 | 节点说明标注“快照生成/只读建模/待复核” |
| action detail 体积变大 | 只生成摘要字段，禁止 raw payload |
