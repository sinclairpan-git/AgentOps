# 任务分解：Runtime Audit Query

**编号**：`026-runtime-audit-query` | **日期**：2026-05-08
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: formal scope freeze
Batch 2: runtime audit query route
Batch 3: verification and archive
```

---

## Batch 1：formal scope freeze

### Task 1.1 冻结 runtime audit query 正式真值

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, task-execution-log.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. 026 明确只新增受保护只读 audit query route。
  2. 026 明确不新增数据库、SIEM、通知、租户 ABAC 或导出能力。
- **验证**：文档对账 + `ai-sdlc program truth sync --execute --yes`

## Batch 2：runtime audit query route

### Task 2.1 新增 runtime.audit.read scope 与 route

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T11
- **文件**：src/agentops/api/auth.py, src/agentops/api/server.py, src/agentops/api/app.py, tests/contract/test_ao26_ct_runtime_audit_query.py
- **可并行**：否
- **验收标准**：
  1. `agentops-operator`/`agentops-admin` 可读 runtime audit。
  2. `agentops-viewer` 默认被拒绝，`denied_scope=runtime.audit.read`。
  3. manifest 声明 runtime audit query route。
- **验证**：`uv run pytest tests/contract/test_ao26_ct_runtime_audit_query.py -q`

### Task 2.2 实现 filters、limit 和 metadata-only response

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T21
- **文件**：src/agentops/api/server.py, tests/contract/test_ao26_ct_runtime_audit_query.py
- **可并行**：否
- **验收标准**：
  1. 支持 audit_id、request_id、action、outcome、limit filters。
  2. 默认 limit 50，最大 limit 200，非法 limit 返回 `AUDIT_LIMIT_INVALID`。
  3. 响应不包含 raw path 或敏感材料。
- **验证**：`uv run pytest tests/contract/test_ao26_ct_runtime_audit_query.py -q`

## Batch 3：verification and archive

### Task 3.1 完成生产边界回归和归档

- **任务编号**：T31
- **优先级**：P1
- **依赖**：T22
- **文件**：task-execution-log.md, development-summary.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. AO23/AO24/AO25/AO26 联跑通过。
  2. ruff 与 AI-SDLC constraints 通过。
  3. execution log 与 development summary 记录实际验证。
- **验证**：`uv run pytest tests/contract/test_ao23_ct_production_runtime_boundary.py tests/contract/test_ao24_ct_durable_audit_log.py tests/contract/test_ao25_ct_production_audit_coverage.py tests/contract/test_ao26_ct_runtime_audit_query.py -q`
