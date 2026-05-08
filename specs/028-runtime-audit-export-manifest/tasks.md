# 任务分解：Runtime Audit Export Manifest

**编号**：`028-runtime-audit-export-manifest` | **日期**：2026-05-08
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: freeze manifest contract, add contract tests, implement, verify, archive
```

---

## Batch 1：manifest contract + implementation

### Task 1.1 冻结 runtime audit export manifest 正式真值

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, task-execution-log.md
- **可并行**：否
- **验收标准**：
  1. 028 明确覆盖 metadata-only export manifest。
  2. 028 明确不新增数据库、SIEM、通知、下载文件、tenant ABAC 或 raw audit export。
- **验证**：文档对账 + `uv run ai-sdlc verify constraints`

### Task 1.2 新增 AO28 contract tests

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T11
- **文件**：tests/contract/test_ao28_ct_runtime_audit_export_manifest.py
- **可并行**：否
- **验收标准**：
  1. 覆盖有权限 manifest 响应和稳定 digest。
  2. 覆盖 denied/rejected durable audit evidence。
  3. 覆盖 anti-leak 和 no download URL 边界。
- **验证**：`uv run pytest tests/contract/test_ao28_ct_runtime_audit_export_manifest.py -q`

### Task 1.3 实现 runtime audit export manifest route

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T21
- **文件**：src/agentops/api/server.py
- **可并行**：否
- **验收标准**：
  1. 新增 `GET /v1/audit/runtime/export-manifest`。
  2. route 复用 `runtime.audit.read` scope、filters 和 limit semantics。
  3. 响应只包含 metadata manifest，不包含 raw records、raw path 或下载能力。
- **验证**：AO28 contract tests 通过。

### Task 1.4 回归验证与归档

- **任务编号**：T31
- **优先级**：P0
- **依赖**：T22
- **文件**：development-summary.md, task-execution-log.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. AO23-AO28 contract regression 通过。
  2. ruff、constraints、close-check 通过。
  3. execution log 和 development summary 记录实际验证结果。
- **验证**：`uv run pytest ...AO23...AO28... -q`、`uv run ruff check src tests`、`uv run ai-sdlc verify constraints`、`uv run ai-sdlc workitem close-check --wi specs/028-runtime-audit-export-manifest`
