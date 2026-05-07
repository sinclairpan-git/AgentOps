# 计划：Console 质量与采纳洞察

## 设计决策

- 将采纳分析放入现有 Quality Center，不新增导航，减少信息架构跳跃。
- 采用 snapshot 派生数据，不接真实 Git/PR/CI/Test Connector。
- 所有指标是摘要视图，不包含代码、差异内容、PR 原文或用户私密信息。
- 低置信度只进入人工复核或申诉路径，不触发自动生命周期动作。

## 批次

### Batch 1：规格与契约

- 新增 011 spec/plan/tasks/contract。
- 明确 AO11-CT-001 到 AO11-CT-005。

### Batch 2：后端视图模型

- 在 Console snapshot 中新增 `adoption`。
- 从现有 runs、quality、risks、agentStore summary 派生只读指标和解释链。

### Batch 3：前端 Quality Center

- 增强 `QualityCenterView`，展示采纳概览、解释链、分组洞察和复核队列。
- 更新前端 validator 与 mock 数据。

### Batch 4：验证与评审

- 新增 AO11 契约测试。
- 跑后端契约、前端契约、构建、ruff、AI-SDLC 约束和 program validate。
- 对抗评审通过后提交 PR。

## 风险

| 风险 | 控制 |
|---|---|
| 用户误解为完整评分引擎 | 页面文案明确“摘要洞察”，不展示自动决策 |
| 低置信误触发生命周期建议 | 契约禁止自动下架和自动写回动作 |
| 采纳指标泄露代码或 PR 原文 | 只展示聚合数和失败类型，不包含差异内容、URL 或原文 |
