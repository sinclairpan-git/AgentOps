---
related_doc:
  - "specs/042-quality-center-workbench/spec.md"
  - "specs/040-quality-lifecycle-analytics/spec.md"
  - "specs/041-quality-scorer-versioning/spec.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
---
# 功能规格：Quality Center Console UI

**功能编号**：`043-quality-center-console-ui`
**创建日期**：2026-05-11
**状态**：草案
**输入**：承接 042 Quality Center Workbench 的 summary-only backend contract，在浏览器 Console 中展示质量摘要、scorer rollout 人工审批状态、review queue 与趋势摘要。

**范围**：本工作项实现 Console 可消费的 `qualityCenterWorkbench` 快照字段、前端安全校验/legacy fallback 和 Quality Center 页面渲染。不执行真实 scorer，不自动 rollout，不自动下架，不写回 Agent Store，不发布通知，不展示 raw evidence、prompt、diff、terminal、PR 原文或下载链接。

## 用户场景与测试

### 用户故事 1 - 质量负责人查看统一工作台（优先级：P1）

作为质量负责人，我希望在 Quality Center 页面看到 agent/version 质量分、置信度、证据等级、缺失证据和 lifecycle 建议，以便快速定位需要补证据或复核的对象。

**独立测试**：Console snapshot 必须包含 `qualityCenterWorkbench.agent_summaries`，前端页面必须渲染 agent summaries 表格和 summary-only 说明。

### 用户故事 2 - 平台 Owner 审核 scorer rollout（优先级：P1）

作为平台 Owner，我希望看到 scorer candidate 的 comparison state、safety impact、manual approval queue size 和 review queue，以便人工决定是否推进 rollout。

**独立测试**：前端校验 `scorer_rollout_panel.automatic_rollout_enabled=false`，并拒绝自动 rollout/批准/写回文案。

### 用户故事 3 - 旧版快照保持安全空态（优先级：P1）

作为 Console 使用者，我希望旧版后端未提供 `qualityCenterWorkbench` 时，页面仍能从既有 quality/adoption 摘要生成只读 fallback，而不是崩溃或推导自动动作。

**独立测试**：删除 `qualityCenterWorkbench` 的 API snapshot 仍可通过 legacy default，fallback 只包含安全摘要和人工复核动作。

## 边界情况

- `agent_summaries` 为空时展示 empty 状态，不伪造分数。
- 低置信、缺证据、scorer insufficient evidence 或 lifecycle review 只进入人工队列。
- UI 不展示 raw payload、prompt、diff、terminal、secret、download/raw URL。
- Console 不提供自动 rollout、自动批准、自动下架、Store write 或通知发送按钮。

## 需求

### 功能需求

- **FR-001**：后端 Console snapshot 必须包含 `qualityCenterWorkbench`，字段对齐 AO42 summary-only contract。
- **FR-002**：前端 API client 必须验证 `qualityCenterWorkbench` 结构、安全边界和 legacy fallback。
- **FR-003**：Quality Center 页面必须展示 summary metrics、scorer rollout panel、agent summaries、review queue、trend summary 和 guardrails。
- **FR-004**：所有 Quality Center UI 文案和校验必须拒绝自动 rollout、自动 lifecycle action、Store write、自动发布/通知。
- **FR-005**：043 必须回归 AO42 与 Console contract，证明 UI 接入未破坏既有 Quality Center backend contract。

### 关键实体

- **QualityCenterWorkbench**：Console 可消费的 AO42 summary-only 聚合字段。
- **QualityCenterAgentSummary**：单个 agent/version 的质量分、证据、scorer comparison 和 lifecycle 摘要。
- **QualityCenterReviewQueue**：需要人工复核或 rollout 审批的队列项。

## 成功标准

- **SC-001**：`build_console_snapshot()` 输出包含安全的 `qualityCenterWorkbench`，且不含 raw payload。
- **SC-002**：`apps/agentops-console/tests/console-contract.test.mjs` 覆盖有效快照、legacy fallback、非法自动动作和非法 raw URL。
- **SC-003**：Quality Center 页面显示 AO42 工作台字段，而不是只显示旧 adoption/quality 表。
- **SC-004**：`uv run pytest tests/contract/test_ao4_ct_console_api.py tests/contract/test_ao42_ct_quality_center_workbench.py`、Console npm contract、ruff 和 AI-SDLC constraints 通过。
