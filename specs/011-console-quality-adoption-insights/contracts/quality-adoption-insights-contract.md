# 契约：Console 质量与采纳洞察

## AO11-CT-001 adoption 数据域

`consoleData.adoption` 必须包含：

- `metrics`
- `explanationChains`
- `segments`
- `reviewSignals`
- `guardrails`

## AO11-CT-002 采纳指标

`metrics` 必须包含以下摘要字段：

- `generated_lines`
- `retained_lines`
- `human_modified_lines`
- `deleted_lines`
- `rework_rounds`
- `pr_review_findings`
- `ci_failure_types`

不得包含代码片段、差异内容、PR 原文、下载 URL 或 `raw_payload`。

## AO11-CT-003 质量解释链

每条解释链必须包含：

- `score_template_id`
- `evidence_level`
- `confidence`
- `missing_evidence`
- `explanation`
- `appeal_path`

缺失证据必须以 `missing_evidence` 展示，不得按 0 分处理。

## AO11-CT-004 安全边界

低置信度和缺失证据只能进入人工复核或申诉路径。`guardrails` 和用户可见动作不得包含自动下架、自动降推荐、自动写回 Agent Store。

## AO11-CT-005 前端中文展示

Quality Center 必须展示：

- 采纳概览
- 质量解释链
- 复核队列
- 低置信不自动下架
- 申诉路径
