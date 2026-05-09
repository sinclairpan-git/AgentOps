---
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Runtime_项目_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_AgentOps_AiSDLC_应用底座顶层规划_PRD.md"
---
# 任务分解：AgentOps Runtime Governance Foundation

**编号**：`031-agentops-runtime-governance-foundation` | **日期**：2026-05-09  
**来源**：`spec.md` + `research.md` + `data-model.md` + `plan.md`  
**当前阶段**：decompose 完成，等待 execute 授权

## 分批策略

```text
Batch 1: AI-SDLC formal baseline and contract tests
Batch 2: Contract / Schema / State / Error Registry
Batch 3: Runtime Ingestion API v1
Batch 4: Run Detail and Trace Timeline projections
Batch 5: Console contract integration and verification
```

## Batch 1：AI-SDLC formal baseline and contract tests

### Task 1.1 冻结 031 formal docs

- **状态**：已完成
- **优先级**：P0
- **依赖**：无
- **文件**：`spec.md`、`research.md`、`data-model.md`、`plan.md`、`tasks.md`、`task-execution-log.md`、`development-summary.md`
- **对应需求**：SC-001、SC-005、SC-006
- **验收标准**：031 工作项符合 refine/design/decompose 产物要求，且引用三份新 PRD。

### Task 1.2 冻结 AO31 contract tests 草案

- **状态**：已完成
- **优先级**：P0
- **依赖**：T31-01
- **文件**：`contracts/contract-tests.md`
- **对应需求**：FR-017、AO31-CT-001 到 AO31-CT-008
- **验收标准**：每个 contract test 均包含正例、反例/错误码、幂等或兼容断言。

### Task 1.3 归档 AgentOps P0-P2 需求池

- **状态**：已完成
- **优先级**：P0
- **依赖**：T31-01
- **文件**：`agentops-p0-p2-backlog.md`、`spec.md`、`tasks.md`、`development-summary.md`、`task-execution-log.md`
- **对应需求**：用户补充要求：归档 P0 到 P2 所有需求，避免后续重新归纳
- **验收标准**：P0/P1/P2 需求包均有稳定编号、目标、阶段归属和后续工作项建议。

## Batch 2：Contract / Schema / State / Error Registry

### Task 2.1 实现 Runtime 契约 Registry

- **状态**：待执行
- **优先级**：P0
- **依赖**：T31-02
- **文件**：`src/agentops/core/runtime_contracts.py`、`src/agentops/models/runtime.py`
- **对应需求**：FR-001、FR-002、FR-003、FR-004
- **验收标准**：`RuntimeRun`、`TraceSpan`、`EventEnvelope`、`PolicyDecision`、`CapabilityGrant`、`Approval`、`EvidenceSummary`、`HealthSummary` 均有 owner、required fields、state/error 映射。

### Task 2.2 增加 Registry 单元测试与契约测试

- **状态**：待执行
- **优先级**：P0
- **依赖**：T31-11
- **文件**：`tests/unit/test_runtime_contracts.py`、`tests/contract/test_ao31_ct_runtime_governance_foundation.py`
- **对应需求**：AO31-CT-001、AO31-CT-008
- **验收标准**：缺 owner、未知枚举、状态展示冲突均能失败并返回预期错误码。

## Batch 3：Runtime Ingestion API v1

### Task 3.1 实现 Runtime Ingestion 规范化核心

- **状态**：待执行
- **优先级**：P0
- **依赖**：T31-11
- **文件**：`src/agentops/core/runtime_ingestion.py`、`src/agentops/storage/repository.py`
- **对应需求**：FR-005、FR-006、FR-007、FR-008、FR-009、FR-010
- **验收标准**：有效 RuntimeRun/TraceSpan 批次写入事实；重复批次 deduplicated；parent 缺失 timeline degraded。

### Task 3.2 暴露 Runtime Ingestion API

- **状态**：待执行
- **优先级**：P0
- **依赖**：T31-21
- **文件**：`src/agentops/api/runtime.py`、`src/agentops/api/app.py`、`src/agentops/api/server.py`
- **对应需求**：FR-005、FR-006、FR-016
- **验收标准**：API 返回逐条 accepted/deduplicated/rejected/dlq receipt，生产鉴权沿用 AO23 边界。

### Task 3.3 增加 Ingestion contract tests

- **状态**：待执行
- **优先级**：P0
- **依赖**：T31-21、T31-22
- **文件**：`tests/contract/test_ao31_ct_runtime_governance_foundation.py`
- **对应需求**：AO31-CT-002、AO31-CT-003、AO31-CT-004、AO31-CT-005
- **验收标准**：schema unsupported、invalid run、unsupported span kind、parent missing、idempotent replay 均覆盖。

## Batch 4：Run Detail and Trace Timeline projections

### Task 4.1 实现 Run Detail projection

- **状态**：待执行
- **优先级**：P0
- **依赖**：T31-21
- **文件**：`src/agentops/api/view_models.py`、`src/agentops/api/console_snapshot.py`、`src/agentops/api/runtime.py`
- **对应需求**：FR-011、FR-013、FR-016
- **验收标准**：blocked、approval_paused、trace_pending、policy_unavailable、signature_failed 均有白话状态、主动作、audit_id。

### Task 4.2 实现 Trace Timeline projection

- **状态**：待执行
- **优先级**：P0
- **依赖**：T31-21
- **文件**：`src/agentops/api/view_models.py`、`src/agentops/api/runtime.py`
- **对应需求**：FR-012、FR-014、FR-016
- **验收标准**：span tree、duration、status、input/output ref、error_code、degraded_reason 可查询。

### Task 4.3 增加 Projection contract tests

- **状态**：待执行
- **优先级**：P0
- **依赖**：T31-31、T31-32
- **文件**：`tests/contract/test_ao31_ct_runtime_governance_foundation.py`
- **对应需求**：AO31-CT-006、AO31-CT-007
- **验收标准**：权限不足、trace_pending、raw access required、token/cost 缺失兼容均覆盖。

## Batch 5：Console contract integration and verification

### Task 5.1 更新 Console mock/API client 契约

- **状态**：待执行
- **优先级**：P1
- **依赖**：T31-31、T31-32
- **文件**：`apps/agentops-console/src/data/mockAgentOpsData.js`、`apps/agentops-console/src/data/agentOpsApiClient.js`
- **对应需求**：FR-015
- **验收标准**：Console 可表达 succeeded、blocked、approval_paused、trace_pending、degraded 五类运行状态。

### Task 5.2 更新 RunsView / OverviewView 展示承接

- **状态**：待执行
- **优先级**：P1
- **依赖**：T31-41
- **文件**：`apps/agentops-console/src/views/RunsView.js`、`apps/agentops-console/src/views/OverviewView.js`、`apps/agentops-console/src/styles.css`
- **对应需求**：FR-011、FR-012、FR-013、FR-014
- **验收标准**：Run Detail 与 Trace Timeline 不暴露原文，缺数据有 `trace_pending` 或 degraded 空态。

### Task 5.3 执行验证与归档

- **状态**：待执行
- **优先级**：P0
- **依赖**：T31-12、T31-23、T31-33、T31-42
- **文件**：`task-execution-log.md`、`development-summary.md`
- **对应需求**：SC-001 到 SC-006
- **验收标准**：执行阶段完成后，所有定向测试、全量回归、AI-SDLC constraints 和 dry-run 均通过，且执行日志记录命令和结果。
- **验收命令**：
  - `uv run pytest tests -q`
  - `uv run ruff check src tests`
  - `uv run ruff format --check src tests`
  - `npm test`
  - `npm run build`
  - `uv run ai-sdlc verify constraints`
  - `uv run ai-sdlc run --dry-run`
