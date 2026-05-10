---
related_doc:
  - "specs/035-p0-end-to-end-acceptance-gate/spec.md"
  - "specs/035-p0-end-to-end-acceptance-gate/plan.md"
---
# 任务分解：P0 End-to-End Acceptance Gate

**编号**：`035-p0-end-to-end-acceptance-gate` | **日期**：2026-05-09

## 分批策略

```text
Batch 1: formal baseline + contract registry
Batch 2: acceptance projection + contract tests
Batch 3: verification, archive, PR close-out
```

## Batch 1：formal baseline + contract registry

### Task 1.1 冻结 AO35 formal docs

- **任务编号**：T11
- **优先级**：P0
- **文件**：spec.md, plan.md, tasks.md, task-execution-log.md, development-summary.md, program-manifest.yaml
- **验收标准**：
  1. 明确承接 AO-P0-13
  2. 明确 gate 只读、不执行 Runtime、不读取 raw payload
  3. manifest 映射新工作项
- **验证**：`uv run ai-sdlc verify constraints`

### Task 1.2 登记 P0 acceptance contract

- **任务编号**：T12
- **优先级**：P0
- **文件**：src/agentops/core/runtime_contracts.py
- **验收标准**：
  1. 登记 `p0_acceptance_gate.v1`
  2. required_fields 包含 gate_id/run_id/agent_id/version/gate_status/required_checks/summary/audit_id
  3. gate_status enum 只允许 passed/failed
- **验证**：AO35 contract registry test

## Batch 2：acceptance projection + contract tests

### Task 2.1 实现只读 acceptance projection

- **任务编号**：T21
- **优先级**：P0
- **文件**：src/agentops/api/acceptance.py
- **验收标准**：
  1. 聚合 outbox、run detail、timeline、evidence、health、policy、grant、guardrail、SDLC bridge 和 Store echo
  2. 所有 required checks 通过时 gate_status=passed
  3. 任一检查失败时 gate_status=failed 并列出 failed_check_ids
- **验证**：AO35 pass/fail contract tests

### Task 2.2 固化 no raw leak 验收

- **任务编号**：T22
- **优先级**：P0
- **文件**：src/agentops/api/acceptance.py, tests/contract/test_ao35_ct_p0_acceptance_gate.py
- **验收标准**：
  1. Gate 序列化结果不包含 raw_payload/prompt/token_secret/credential_secret/device_key
  2. Gate 只返回 summary、引用、状态、错误码和 audit_id
- **验证**：AO35 no raw leak assertion

## Batch 3：verification, archive, PR close-out

### Task 3.1 验证、归档、提交和 PR

- **任务编号**：T31
- **优先级**：P0
- **文件**：task-execution-log.md, development-summary.md
- **验收标准**：
  1. AO35 + AO31/AO32/AO33/AO34 定向回归通过
  2. ruff 和 AI-SDLC constraints 通过
  3. PR 创建后按项目固定规则触发 review/checks/heartbeat 收口
- **验证**：收口命令集合
