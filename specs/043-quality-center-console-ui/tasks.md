---
related_doc:
  - "specs/043-quality-center-console-ui/spec.md"
  - "specs/043-quality-center-console-ui/plan.md"
  - "specs/042-quality-center-workbench/spec.md"
---
# 任务分解：Quality Center Console UI

**编号**：`043-quality-center-console-ui` | **日期**：2026-05-11  
**来源**：plan.md + spec.md

## 分批策略

```text
Batch 1: formal baseline + Console snapshot contract
Batch 2: frontend validation + Quality Center UI
Batch 3: focused verification + close-out docs
```

## Batch 1：formal baseline + Console snapshot contract

### Task 1.1 冻结 043 formal baseline

- **任务编号**：T11
- **状态**：已完成
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. 043 文档承接 042 未进入本批的浏览器 UI。
  2. program truth 映射 043 spec/plan/tasks/log。
- **验证**：`python -m ai_sdlc program truth sync --execute --yes`

### Task 1.2 后端 snapshot 暴露 Quality Center workbench

- **任务编号**：T12
- **状态**：已完成
- **优先级**：P0
- **依赖**：T11
- **文件**：src/agentops/api/console_snapshot.py, tests/contract/test_ao4_ct_console_api.py
- **可并行**：否
- **验收标准**：
  1. `build_console_snapshot()` 输出 `qualityCenterWorkbench`。
  2. 输出字段包含 agent_summaries、scorer_rollout_panel、review_queue、trend_summary、summary、audit_id。
  3. summary 标记 no automatic rollout/lifecycle action/store write/publish/notification。
- **验证**：AO4 Console API contract

## Batch 2：frontend validation + Quality Center UI

### Task 2.1 前端 API client 校验与 legacy fallback

- **任务编号**：T21
- **状态**：已完成
- **优先级**：P0
- **依赖**：T12
- **文件**：apps/agentops-console/src/data/agentOpsApiClient.js, apps/agentops-console/src/data/mockAgentOpsData.js
- **可并行**：否
- **验收标准**：
  1. 新版 snapshot 校验 `qualityCenterWorkbench`。
  2. 旧版 snapshot 缺字段时生成安全 fallback。
  3. 自动 rollout/批准/写回/发布/通知文案被拒绝。
- **验证**：Console npm contract

### Task 2.2 Quality Center 页面渲染 AO42 工作台

- **任务编号**：T22
- **状态**：已完成
- **优先级**：P1
- **依赖**：T21
- **文件**：apps/agentops-console/src/views/QualityCenterView.js, apps/agentops-console/src/styles.css
- **可并行**：否
- **验收标准**：
  1. 页面展示 summary metrics、scorer rollout panel、agent summaries、review queue、trend summary、guardrails。
  2. 空态、低置信、缺证据和人工审批队列布局稳定。
  3. 页面文案不暗示自动执行动作。
- **验证**：Console npm contract + browser smoke（如本地服务可用）

## Batch 3：focused verification + close-out docs

### Task 3.1 回归与归档

- **任务编号**：T31
- **状态**：已完成
- **优先级**：P0
- **依赖**：T22
- **文件**：tasks.md, task-execution-log.md, development-summary.md
- **可并行**：否
- **验收标准**：
  1. AO4、AO42、Console npm contract 通过。
  2. ruff 和 AI-SDLC verify constraints 通过。
  3. 执行日志与任务状态同步。
- **验证**：见 task-execution-log.md
