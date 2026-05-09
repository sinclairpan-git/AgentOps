---
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Runtime_项目_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_项目_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_AgentOps_AiSDLC_应用底座顶层规划_PRD.md"
---
# 任务分解：AgentOps Evidence and Health Summary Loop

**编号**：`032-evidence-health-summary-loop` | **日期**：2026-05-09  
**来源**：spec.md + plan.md + contracts/contract-tests.md

## 分批策略

```text
Batch 1: AI-SDLC formal baseline and contract tests
Batch 2: EvidenceSummary projection
Batch 3: HealthSummary aggregation
Batch 4: Agent Store runtime summary echo
Batch 5: P0 end-to-end acceptance and close
```

## Batch 1：AI-SDLC formal baseline and contract tests

### Task 1.1 冻结 032 真实规格与计划

- **任务编号**：T11
- **优先级**：P0
- **覆盖需求**：AO-P0-05、AO-P0-06、AO-P0-11、AO-P0-13
- **依赖**：无
- **文件**：`specs/032-evidence-health-summary-loop/spec.md`、`plan.md`、`research.md`、`data-model.md`
- **可并行**：否
- **验收标准**：
  1. spec/plan/data-model/research 均为业务真实内容，不保留占位模板。
  2. 不修改 001-031 已关闭工作项语义。
- **验证**：`uv run ai-sdlc gate refine`、`uv run ai-sdlc gate design`

### Task 1.2 冻结 AO32 contract tests 草案

- **任务编号**：T12
- **优先级**：P0
- **覆盖需求**：FR-001 到 FR-012
- **依赖**：T11
- **文件**：`specs/032-evidence-health-summary-loop/contracts/contract-tests.md`
- **可并行**：否
- **验收标准**：
  1. AO32-CT-001 到 AO32-CT-006 均有正例、反例和覆盖需求。
  2. contract tests 明确 AO22/AO31 回归要求。
- **验证**：`uv run ai-sdlc gate decompose`

## Batch 2：EvidenceSummary projection

### Task 2.1 实现 Runtime EvidenceSummary builder

- **任务编号**：T21
- **优先级**：P0
- **覆盖需求**：FR-001、FR-002、FR-003
- **依赖**：T12
- **文件**：`src/agentops/core/runtime_summary.py`、`src/agentops/api/runtime.py`
- **可并行**：否
- **验收标准**：
  1. 完整 succeeded run + trace spans 生成 `evidence_level=L5`。
  2. 缺 trace 时降级为 `L3` 并记录 `trace_pending`。
  3. `source_event_ids` 来自 RuntimeRun / TraceSpan event_id，不凭空生成。
- **验证**：AO32-CT-001

### Task 2.2 实现 raw access summary 边界

- **任务编号**：T22
- **优先级**：P0
- **覆盖需求**：FR-010
- **依赖**：T21
- **文件**：`src/agentops/core/runtime_summary.py`、`tests/contract/test_ao32_ct_evidence_health_summary_loop.py`
- **可并行**：否
- **验收标准**：
  1. 默认只返回 summary/hash/ref。
  2. raw 请求无权限时返回 `RAW_ACCESS_REQUIRED`、audit_id、request_access_url、denied_scope。
- **验证**：AO32-CT-002

## Batch 3：HealthSummary aggregation

### Task 3.1 实现 agent/version runtime run 查询 helper

- **任务编号**：T31
- **优先级**：P0
- **覆盖需求**：FR-004
- **依赖**：T21
- **文件**：`src/agentops/storage/repository.py`
- **可并行**：否
- **验收标准**：
  1. 可按 agent_id/version 返回最近窗口 runtime runs。
  2. 返回值为 deep copy，不泄露 repository 内部可变状态。
- **验证**：AO32-CT-003

### Task 3.2 实现 Runtime HealthSummary builder

- **任务编号**：T32
- **优先级**：P0
- **覆盖需求**：FR-005、FR-006
- **依赖**：T31
- **文件**：`src/agentops/core/runtime_summary.py`
- **可并行**：否
- **验收标准**：
  1. success_rate/failure_rate/policy_block_count/evidence_completeness 计算稳定。
  2. sample_size=0 不除零，返回 watching/expired。
  3. recommended_action 映射符合 registry 枚举。
- **验证**：AO32-CT-003

## Batch 4：Agent Store runtime summary echo

### Task 4.1 接入 Store summary runtime 优先路径

- **任务编号**：T41
- **优先级**：P0
- **覆盖需求**：FR-007、FR-008
- **依赖**：T32
- **文件**：`src/agentops/api/store_summary.py`、`src/agentops/api/app.py`
- **可并行**：否
- **验收标准**：
  1. runtime facts 存在时 Store summary 包含 evidence_summary、health_summary、recommended_action、ops_detail_url。
  2. runtime facts 不存在时仍兼容 AO22 SDLC audit event summary。
- **验证**：AO32-CT-004 + AO22 回归

### Task 4.2 实现 expiry 语义

- **任务编号**：T42
- **优先级**：P0
- **覆盖需求**：FR-009
- **依赖**：T41
- **文件**：`src/agentops/core/runtime_summary.py`、`src/agentops/api/store_summary.py`
- **可并行**：否
- **验收标准**：
  1. valid_until 已过期时 Store recommended_action 覆盖为 `expired`。
  2. expired 响应不声称 healthy/usable。
- **验证**：AO32-CT-005

## Batch 5：P0 end-to-end acceptance and close

### Task 5.1 实现 P0 端到端 contract test

- **任务编号**：T51
- **优先级**：P0
- **覆盖需求**：FR-011、FR-012
- **依赖**：T41、T42
- **文件**：`tests/contract/test_ao32_ct_evidence_health_summary_loop.py`
- **可并行**：否
- **验收标准**：
  1. Runtime ingestion -> Run Detail -> Trace Timeline -> EvidenceSummary -> Store Summary 全链路通过。
  2. Store summary 序列化结果不包含 raw/secrets。
- **验证**：AO32-CT-006

### Task 5.2 全量回归与 AI-SDLC 收口

- **任务编号**：T52
- **优先级**：P0
- **覆盖需求**：SC-001 到 SC-006
- **依赖**：T51
- **文件**：`specs/032-evidence-health-summary-loop/task-execution-log.md`、`development-summary.md`
- **可并行**：否
- **验收标准**：
  1. AO22/AO31/AO32 contract tests 通过。
  2. `ai-sdlc verify constraints` 和 `ai-sdlc run --dry-run` 通过。
  3. 执行日志记录实际验证命令和结果。
- **验证**：计划中 Phase 4 的验证命令
