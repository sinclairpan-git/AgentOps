# 开发总结：P2 Replay Simulation Optimizer

**编号**：`038-p2-replay-simulation-optimizer`  
**日期**：2026-05-10  
**状态**：实现中

## 已完成

- 新增 AO38 P2-A contracts：
  - `safe_replay_plan.v1`
  - `experiment_plan.v1`
  - `optimizer_recommendation.v1`
  - `policy_simulation_projection.v1`
- 新增后端 projection builders 与 API wrappers：
  - safe replay plan：terminal run -> no-execution simulation plan
  - experiment plan：variant ref/hash/risk only
  - optimizer recommendation：EvalCase summary -> human-review action
  - policy simulation projection：sample run summary -> dry-run impact
- 扩展 `InMemoryRepository` 存储 replay/experiment plan records。
- 新增 AO38 contract tests，当前聚焦测试 8 passed。

## 未进入本批

- 真实 Runtime replay executor。
- 实验执行与自动 rollout。
- 自动配置改写、model/tool 自动切换。
- Console UI。
- policy 发布或 active policy 修改。

## 验证

- `uv run pytest tests/contract/test_ao38_ct_p2_replay_simulation_optimizer.py`：8 passed。
- 完整 ruff、pytest、AI-SDLC verify/close-check 等待 close-out 阶段执行。
