# 功能规格：Quality Lifecycle Analytics

**功能编号**：`040-quality-lifecycle-analytics`  
**创建日期**：2026-05-10  
**状态**：草案  
**输入**：承接《AgentOps 项目 PRD》阶段 4/5：Git/PR/CI/Test Connector 采纳分析、质量评分引擎、生命周期建议与月报；复用 032 Evidence/Health、037 Eval/Budget/SLO、039 Complex risk profile。

**范围**：本工作项第一批只实现 AgentOps 本体的 summary-only backend contracts 与投影函数；不做 Console 页面、不自动下架、不写回 Store、不读取 raw evidence / prompt / diff / terminal 原文。

## 用户场景与测试

### 用户故事 1 - 质量评分必须带证据与置信度（优先级：P1）

作为质量负责人，我希望 AgentOps 输出 score、score_template_id、evidence_level、confidence、missing_evidence 和 explanation，以便质量结论可解释、可复核。

**独立测试**：构建 `quality_score_projection.v1`，验证缺失证据不会按 0 分处理，低置信不触发自动生命周期动作。

### 用户故事 2 - 采纳与 ROI 分析只消费摘要指标（优先级：P1）

作为平台 Owner，我希望看到 AI 生成行数、最终保留行数、返工轮次、PR review 和 CI 失败摘要，以便分析采纳趋势，而不是读取 diff 或 PR 原文。

**独立测试**：构建 `adoption_roi_projection.v1`，验证 retention/rework/CI 指标、抽样复核状态和 no raw payload boundary。

### 用户故事 3 - 生命周期建议必须保持人工处置（优先级：P1）

作为 Agent Owner，我希望质量、风险和 Store governance 只能形成人工建议，不会因为低分或低置信自动禁用、下架或写回 Store。

**独立测试**：构建 `lifecycle_recommendation.v1`，验证 recommended_action、owner_notification_state、store_write_performed=false、automatic_lifecycle_action=false。

### 用户故事 4 - 月报摘要聚合质量与采纳趋势（优先级：P2）

作为 AgentOps 管理员，我希望按月看到多个 Agent 的质量、风险和采纳摘要，以便做人工复盘和 Owner 跟进。

**独立测试**：构建 `monthly_quality_report.v1`，验证 report period、agent summaries、trend summary、raw boundary 和 no automatic publishing。

## 边界情况

- 缺失 EvidenceSummary 时 `missing_evidence` 明确列出缺口；score 不被强行归零。
- 低置信质量分只能给出 `manual_review` 或 `collect_more_evidence`，不得自动下架。
- Adoption/ROI 输入若含 raw diff、prompt、PR URL、download/raw URL 或 secret 字段，输出必须脱敏或拒绝暴露。
- Lifecycle recommendation 只提供人工处置建议，不执行 Store write、disable、publish、notify。

## 需求

### 功能需求

- **FR-001**：系统必须登记 contracts：`quality_score_projection.v1`、`adoption_roi_projection.v1`、`lifecycle_recommendation.v1`、`monthly_quality_report.v1`。
- **FR-002**：Quality score projection 必须输出 score、score_template_id、evidence_level、confidence、missing_evidence、explanation、summary 和 audit id。
- **FR-003**：Adoption ROI projection 必须输出 adoption metrics、retention rate、rework risk、review summary、sampling_review_state、summary 和 audit id。
- **FR-004**：Lifecycle recommendation 必须组合 quality score、complex risk profile 和 Store governance projection，输出 lifecycle_state、recommended_action、owner_notification_state、appeal_state 和 no-action summary。
- **FR-005**：Monthly quality report 必须聚合多个 Agent/version 的质量、风险、采纳和 lifecycle 摘要；固定不自动发布。
- **FR-006**：所有 projection 必须禁止 raw payload、prompt、diff、terminal、secret、download/raw URL。
- **FR-007**：040 必须回归 AO32/AO37/AO39，证明质量/采纳层未破坏 Evidence/Health、Operations 和 P2 ecosystem 基线。

### 关键实体

- **QualityScoreProjection**：质量评分与证据解释摘要。
- **AdoptionRoiProjection**：采纳/ROI 指标摘要。
- **LifecycleRecommendation**：人工生命周期建议。
- **MonthlyQualityReport**：月度质量与采纳报告摘要。

## 成功标准

- **SC-001**：`tests/contract/test_ao40_ct_quality_lifecycle_analytics.py` 覆盖新增 contracts 和核心投影。
- **SC-002**：新增 projection 不包含 raw payload、raw diff、prompt、terminal、token secret、credential secret、device key 或 raw/download URL。
- **SC-003**：AO32/AO37/AO39 定向回归通过。
- **SC-004**：`uv run ai-sdlc verify constraints` 与 040 close-check 通过。
