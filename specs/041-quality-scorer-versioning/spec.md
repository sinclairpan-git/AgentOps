---
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "specs/037-p1-evidence-eval-cost-operations/spec.md"
  - "specs/040-quality-lifecycle-analytics/spec.md"
---
# 功能规格：Quality Scorer Versioning

**功能编号**：`041-quality-scorer-versioning`  
**创建日期**：2026-05-10  
**状态**：草案  
**输入**：承接 AgentOps PRD 16.6 P1 Eval Flywheel：EvalCase、基础 scorer、失败样本沉淀、版本对比；复用 037 EvalCase 与 040 Quality Score Projection。

**范围**：本工作项第一批只实现 AgentOps 本体的 summary-only scorer version 与 scorer comparison contracts；不执行真实 scorer、不读取 raw evidence/prompt/diff/terminal、不自动 rollout、不自动下架或写回 Store。

## 用户场景与测试

### 用户故事 1 - Scorer 版本必须有可审计模板边界（优先级：P1）

作为质量负责人，我希望 AgentOps 输出 scorer version 的模板、证据需求、输入边界和 rollout 状态，以便人工评估 scorer 版本是否可用于质量评分。

**独立测试**：构建 `quality_scorer_version.v1`，验证模板 id、scorer id、version、required evidence、input boundary、rollout state 和 audit id，且不包含 raw prompt/config。

### 用户故事 2 - Scorer 版本对比只消费 EvalCase 摘要（优先级：P1）

作为质量 Owner，我希望比较 baseline scorer 与 candidate scorer 在失败样本摘要上的 coverage、alignment 和 safety impact，以便决定是否进入人工 rollout 审批。

**独立测试**：构建 `quality_scorer_comparison.v1`，验证只使用 EvalCase 摘要字段，输出 source_eval_cases、baseline/candidate scorer、comparison_state、alignment_delta、recommendation 和 manual approval 状态。

### 用户故事 3 - 低样本或低置信不得进入自动采纳（优先级：P1）

作为平台 Owner，我希望样本不足、证据缺失或 candidate 风险较高时只返回 collect_more_samples/needs_human_review，不会自动切换评分模板或触发生命周期动作。

**独立测试**：没有足够 EvalCase 时 comparison 返回 `insufficient_evidence`；candidate 不满足门槛时返回 `needs_human_review`；所有输出 `automatic_rollout_enabled=false`。

## 边界情况

- EvalCase 不足时不得伪造版本对比结论。
- Scorer comparison 不能读取 raw evidence、raw prompt、raw diff、terminal output、secret 或 raw/download URL。
- Candidate scorer 版本不能自动替换 040 `quality_score_projection.v1` 默认模板。
- Scorer comparison 只能给人工审批建议，不执行 rollout、Store write、lifecycle action 或通知发送。

## 需求

### 功能需求

- **FR-001**：系统必须登记 contracts：`quality_scorer_version.v1`、`quality_scorer_comparison.v1`。
- **FR-002**：Quality scorer version 必须输出 scorer_id、scorer_version、score_template_id、rollout_state、required_evidence、input_boundary、summary 和 audit id。
- **FR-003**：Scorer version 必须声明 raw input 禁止、deterministic summary projection、manual approval requirement。
- **FR-004**：Quality scorer comparison 必须按 agent/version 过滤 EvalCase 摘要，输出 source_eval_cases、sample_size、baseline_scorer、candidate_scorer、comparison_state、alignment_delta、safety_impact、recommendation、summary 和 audit id。
- **FR-005**：Comparison 必须支持 min_eval_cases 门槛；门槛非法时返回 `SCORER_COMPARISON_UNAVAILABLE`。
- **FR-006**：所有新增 projection 必须禁止 raw payload、prompt、diff、terminal、secret、download/raw URL。
- **FR-007**：041 必须回归 AO37/AO40，证明 EvalCase 与 Quality Lifecycle 基线未被破坏。

### 关键实体

- **QualityScorerVersion**：scorer 模板与版本治理摘要。
- **QualityScorerComparison**：baseline/candidate scorer 在 EvalCase 摘要集上的对比摘要。

## 成功标准

- **SC-001**：`tests/contract/test_ao41_ct_quality_scorer_versioning.py` 覆盖新增 contracts、scorer version、comparison 和低样本保护。
- **SC-002**：新增 projection 不包含 raw payload、prompt、raw diff、terminal、token secret、credential secret、device key 或 raw/download URL。
- **SC-003**：AO37/AO40/AO41 定向回归通过。
- **SC-004**：`uv run ai-sdlc verify constraints` 与 041 close-check 通过。
