# 任务清单：SDLC v0.7.18 Executable Task Runtime Bridge

## Batch 1：契约与样例

### Task 1.1 冻结双边 Runtime Bridge contract

- **文件**：
  - `specs/056-sdlc-v0-7-18-executable-task-runtime-bridge/contracts/ai-sdlc-agentops-runtime-bridge-vnext.md`
  - `contracts/cross-project/ai-sdlc-agentops-runtime-bridge-vnext.md`
- **目标**：
  1. 定义 Ai_AutoSDLC producer 与 AgentOps consumer 责任。
  2. 定义 `runtime.ingestion.v1` batch、SDLC event payload、receipt、错误码和 Console 映射。
  3. 明确 `verified_loaded` 只作为 adapter diagnostic。
- **验证**：文档对账，确认无 raw payload、replay button 或 Store 中转要求。

### Task 1.2 增加 executable task bridge fixture

- **文件**：
  - `contracts/cross-project/fixtures/ai_sdlc_executable_task_runtime_batch.v1.json`
- **目标**：
  1. 提供 task ready + guard allowed 的正例。
  2. 包含 `executable_task` 与 `code_guard` SDLC runtime events。
  3. 使用 summary-only refs 和 hash。
- **验证**：AO56 contract tests 复用该 fixture。

## Batch 2：Runtime ingestion 与 contract tests

### Task 2.1 先写 failing contract tests

- **文件**：
  - `tests/contract/test_ao56_ct_sdlc_executable_task_runtime_bridge.py`
- **目标**：
  1. 无 executable task 时 readiness 失败。
  2. adapter `verified_loaded` 单独存在时不能推出 actual L5。
  3. guard blocked 时阻断 L5。
- **验证**：首次运行出现预期失败，随后实现通过。

### Task 2.2 实现 runtime contract registry 扩展

- **文件**：
  - `src/agentops/core/runtime_contracts.py`
  - `src/agentops/core/runtime_ingestion.py`
- **目标**：
  1. 支持 executable task / task guard SDLC event。
  2. 保持 canonical envelope、signature、idempotency、sequence 和 DLQ 语义。
  3. 不保存 raw payload。
- **验证**：AO56 + AO34 tests 通过。

## Batch 3：Evidence readiness 与 Console

### Task 3.1 改造 Evidence / L5 readiness

- **文件**：
  - `src/agentops/core/l5_gate.py`
  - `src/agentops/api/console_snapshot.py`
- **目标**：
  1. 将主条件从 adapter_state 改为 task guard / receipt / evidence chain。
  2. `verified_loaded` 仅进入 diagnostics。
  3. legacy run 不误升 actual L5。
- **验证**：L5 单测和 AO56 contract tests。

### Task 3.2 重构 Console SDLC workbench

- **文件**：
  - `apps/agentops-console/src/views/SdlcRunsView.js`
  - `apps/agentops-console/src/data/mockAgentOpsData.js`
  - `apps/agentops-console/tests/console-contract.test.mjs`
- **目标**：
  1. 展示 `taskGuard`、`outboxReceipts`、`evidenceReadiness`、`adapterDiagnostics`。
  2. 前端 validator 拒绝 `ADAPTER_DIAGNOSTIC_OVERREACH`。
  3. 不提供 Outbox Replay 操作。
- **验证**：`npm test`、`npm run build`。

## Batch 4：联调与收口

### Task 4.1 端到端联调

- **文件**：
  - `tests/contract/test_ao56_ct_sdlc_executable_task_runtime_bridge.py`
  - `specs/056-sdlc-v0-7-18-executable-task-runtime-bridge/task-execution-log.md`
- **目标**：
  1. 用 fixture 验证 `/v1/runtime/events` 到 Console snapshot 的链路。
  2. 覆盖 task ready、task missing、guard blocked、receipt diagnostics。
  3. 记录与 Ai_AutoSDLC vNext 的 producer 对接状态。
- **验证**：
  - `python -m ai_sdlc run --dry-run`
  - `uv run pytest tests/contract/test_ao56_ct_sdlc_executable_task_runtime_bridge.py -q`
  - `npm test --prefix apps/agentops-console`
