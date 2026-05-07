# 规格：Console 质量与采纳洞察

**功能编号**：`011-console-quality-adoption-insights`

**依赖**：`010-console-audit-timeline`

## 目标

承接 AgentOps PRD 中“质量评分、置信度、缺失证据、采纳分析和风险归因”的目标，把 Quality Center 从信号列表增强为只读洞察工作台。用户必须能看到质量解释链、采纳保留情况、返工/评审信号和低置信处理边界。

## 范围

- Console snapshot 新增 `adoption` 只读数据域。
- `adoption` 必须包含采纳指标、质量解释链、分组洞察、复核信号和安全边界。
- Quality Center 页面展示采纳概览、解释链、分组洞察和复核队列。
- 所有文案面向中国大陆用户；固定名词 AgentOps、Agent Store、PR、CI、L5 可保留。
- 不暴露代码片段、差异内容、PR 原文或用户私密信息。

## 非目标

- 不实现完整质量评分引擎。
- 不自动下架、不自动降推荐、不写 Agent Store。
- 不接 Git/PR/CI/Test 生产 Connector，只展示安全摘要。
- 不用低置信度自动触发生命周期建议。

## 验收标准

- AO11-CT-001：snapshot 必须包含 `adoption.metrics`、`adoption.explanationChains`、`adoption.segments`、`adoption.reviewSignals` 和 `adoption.guardrails`。
- AO11-CT-002：采纳指标必须包含生成行数、保留行数、人工修改行数、删除行数、返工轮次、PR review 问题、CI 失败类型的摘要字段。
- AO11-CT-003：质量解释链必须包含 score_template_id、evidence_level、confidence、missing_evidence、explanation，不得将缺失证据按 0 分处理。
- AO11-CT-004：低置信度或缺失证据只允许进入人工复核/申诉路径，不允许出现自动下架或自动写回动作。
- AO11-CT-005：前端必须展示中文“采纳概览”“质量解释链”“复核队列”“低置信不自动下架”等文案，并在 schema 异常时安全回退。
