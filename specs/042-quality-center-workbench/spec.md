---
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "specs/040-quality-lifecycle-analytics/spec.md"
  - "specs/041-quality-scorer-versioning/spec.md"
---
# 功能规格：Quality Center Workbench

**功能编号**：`042-quality-center-workbench`  
**创建日期**：2026-05-11  
**状态**：草案  
**输入**：承接 AgentOps PRD 信息架构中的 Quality Center：质量评分、置信度、评分模板、趋势、解释链；复用 040 Quality Lifecycle Analytics 与 041 Quality Scorer Versioning。

**范围**：本工作项第一批只实现 AgentOps 本体的 summary-only Quality Center backend contract 与投影函数；不做浏览器 UI、不执行真实 scorer、不自动 rollout、不自动下架、不写回 Store、不发布月报。

## 用户场景与测试

### 用户故事 1 - Quality Center 需要统一质量摘要（优先级：P1）

作为质量负责人，我希望按 Agent/version 查看 score、quality_state、confidence、missing_evidence、score_template_id 和 explanation 摘要，以便快速识别需要补证据或人工复核的对象。

**独立测试**：构建 `quality_center_workbench.v1`，验证每个 agent summary 包含 040 quality score 字段，且缺失证据不按 0 分处理。

### 用户故事 2 - Scorer rollout 审批应进入工作台队列（优先级：P1）

作为平台 Owner，我希望 Quality Center 显示 scorer candidate 与 baseline 的 comparison state、safety impact 和 manual approval 状态，以便人工决定是否推进 rollout。

**独立测试**：对带 EvalCase 的 agent 构建 Quality Center，验证 scorer rollout panel、review queue 和 no automatic rollout guardrail。

### 用户故事 3 - 生命周期与月度趋势只能形成摘要建议（优先级：P1）

作为 Agent Owner，我希望 Quality Center 聚合 lifecycle recommendation 和 monthly trend summary，但不自动写 Store、下架、发布或通知。

**独立测试**：验证 workbench summary 中 `automatic_rollout_enabled=false`、`automatic_lifecycle_action=false`、`store_write_performed=false`、`automatic_publish_performed=false`。

## 边界情况

- agent_refs 为空时返回 `empty` 状态，不伪造分数或趋势。
- agent_refs 非对象时返回 `QUALITY_CENTER_WORKBENCH_UNAVAILABLE`。
- Candidate scorer 不足样本、needs_human_review 或 negative safety impact 时必须进入 review queue。
- 输出不得包含 raw evidence、prompt、diff、terminal、PR 原文、secret、download/raw URL。
- Quality Center 只汇总可展示摘要，不执行 Store write、rollout、lifecycle action 或 notification。

## 需求

### 功能需求

- **FR-001**：系统必须登记 contract：`quality_center_workbench.v1`。
- **FR-002**：Quality Center workbench 必须输出 agent_summaries、scorer_rollout_panel、review_queue、trend_summary、summary 和 audit id。
- **FR-003**：agent_summaries 必须包含 040 quality score 字段和 041 scorer comparison 摘要。
- **FR-004**：scorer_rollout_panel 必须统计 candidate、ready_for_manual_approval、needs_human_review 和 insufficient_evidence 数量。
- **FR-005**：review_queue 必须为缺证据、低置信、scorer human review 和 lifecycle manual review 生成人工队列项。
- **FR-006**：所有新增 projection 必须禁止 raw payload、prompt、diff、terminal、secret、download/raw URL。
- **FR-007**：042 必须回归 AO40/AO41，证明 Quality Center 汇总层未破坏质量生命周期与 scorer 版本基线。

### 关键实体

- **QualityCenterWorkbench**：Quality Center 页面可消费的 summary-only 聚合。
- **QualityCenterAgentSummary**：单个 Agent/version 的质量、生命周期、scorer comparison 摘要。
- **QualityCenterReviewQueue**：需要人工复核或 rollout 审批的队列项。

## 成功标准

- **SC-001**：`tests/contract/test_ao42_ct_quality_center_workbench.py` 覆盖 registry、summary aggregation、review queue、malformed input 和 no raw leak。
- **SC-002**：新增 projection 不包含 raw payload、prompt、raw diff、terminal、token secret、credential secret、device key 或 raw/download URL。
- **SC-003**：AO40/AO41/AO42 定向回归通过。
- **SC-004**：`uv run ai-sdlc verify constraints` 与 042 close-check 通过。
