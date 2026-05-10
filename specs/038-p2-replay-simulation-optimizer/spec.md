# 功能规格：P2 Replay Simulation Optimizer

**功能编号**：`038-p2-replay-simulation-optimizer`  
**创建日期**：2026-05-10  
**状态**：草案  
**输入**：承接 `specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md` 中 P2-A：`AO-P2-01` Safe Replay / Simulation、`AO-P2-02` Prompt / Model / Tool Experiment、`AO-P2-07` Optimizer、`AO-P2-10` 治理策略仿真。依赖 032 Evidence/Health、036 Approval/Policy/Grant operations、037 Evidence/Eval/Cost operations。

**范围**：本工作项第一批只实现 AgentOps 本体的 P2-A summary-only planning/projection contracts 与后端函数；不做真实 Runtime replay、不执行实验、不改写 prompt/model/tool、不发布 policy、不做 Console 页面。

## 用户场景与测试

### 用户故事 1 - 历史运行可生成安全重放计划（优先级：P1）

作为 Ops 工程师，我希望从已结束 run 生成安全重放计划，以便后续在沙箱里复现实验前先确认输入证据、沙箱约束和审计记录。

**独立测试**：从 failed run 生成 `safe_replay_plan.v1`，验证只包含 source run、evidence summary、sandbox profile、execution state 和 audit id。

**验收场景**：

1. **Given** run 已 failed 且有 evidence summary，**When** 创建 safe replay plan，**Then** 输出 `runtime_execution_performed=false`、`external_side_effects_enabled=false`。
2. **Given** run 仍处于 running，**When** 创建 safe replay plan，**Then** 返回 `REPLAY_SOURCE_NOT_TERMINAL`。

### 用户故事 2 - 实验计划只能登记安全引用（优先级：P1）

作为质量 Owner，我希望登记 model/tool/config 实验变体，但只保存 hash/ref/risk 摘要，以免 AgentOps 直接持有原始 prompt、密钥或执行材料。

**独立测试**：创建 `experiment_plan.v1`，验证 variants 只有 `config_ref`、`config_hash`、risk 和 execution state，不包含 raw config/payload。

### 用户故事 3 - Optimizer 基于 EvalCase 给出人工可审建议（优先级：P1）

作为平台 Owner，我希望从 EvalCase 摘要生成优化建议，以便决定是否进入实验计划，而不是让系统自动改写配置或切换模型。

**独立测试**：已有 EvalCase 时输出 `prepare_experiment`；无样本时输出 `collect_more_samples`。

### 用户故事 4 - 策略变更可做发布前仿真投影（优先级：P1）

作为 policy owner，我希望在发布前基于历史 run 摘要模拟影响范围，以便确认 deny 优先级和风险样本，而不真正发布策略。

**独立测试**：构建 `policy_simulation_projection.v1`，验证 `dry_run_only=true`、`policy_publish_performed=false`，并按 sample run 统计 succeeded / blocked_or_failed。

## 边界情况

- Safe replay plan 只能对 terminal run 生成计划；running/created/approval_paused 不能进入。
- Experiment plan 不能返回 raw config、raw payload、credential secret、token secret、device key、download/raw URL。
- Optimizer 只能返回人工可审建议，不自动改写配置、不切换 model/tool、不执行 Runtime。
- Policy simulation 只支持已登记的治理变更类型，不发布、不回写、不修改 active policy。

## 需求

### 功能需求

- **FR-001**：系统必须登记 P2-A contracts：`safe_replay_plan.v1`、`experiment_plan.v1`、`optimizer_recommendation.v1`、`policy_simulation_projection.v1`。
- **FR-002**：Safe replay plan 必须绑定 source run、sandbox profile、replay mode、execution state、evidence summary 和 audit id，并固定 summary-only/no-execution。
- **FR-003**：Experiment plan 必须登记 agent/version、owner_team、hypothesis、variant refs/hash/risk、rollout_state 和 audit id。
- **FR-004**：Optimizer recommendation 必须只消费 EvalCase/source run 摘要，输出 recommendation_state、recommended_action 和 source_eval_cases。
- **FR-005**：Policy simulation projection 必须只基于 sample run 摘要输出影响统计，不发布 policy。
- **FR-006**：所有 P2-A projection 必须禁止 raw payload、raw config、credential secret、token secret、device key、download/raw URL。
- **FR-007**：038 必须回归 AO32/AO34/AO35/AO37，证明 P2-A 未破坏 P0/P1 治理基线。

### 关键实体

- **SafeReplayPlan**：历史运行的安全重放计划摘要。
- **ExperimentPlan**：model/tool/config 实验变体的安全引用计划。
- **OptimizerRecommendation**：基于 EvalCase 的人工可审优化建议。
- **PolicySimulationProjection**：policy 发布前的 dry-run 影响投影。

## 成功标准

- **SC-001**：`tests/contract/test_ao38_ct_p2_replay_simulation_optimizer.py` 覆盖所有新增 contracts 和核心投影。
- **SC-002**：新增 projection 序列化结果不包含 raw payload、raw config、token secret、credential secret、device key 或 raw/download URL。
- **SC-003**：AO32/AO34/AO35/AO37 定向回归通过。
- **SC-004**：`uv run ai-sdlc verify constraints` 与 038 close-check 通过。
