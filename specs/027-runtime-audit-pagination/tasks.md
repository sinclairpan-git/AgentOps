# 任务分解：Runtime Audit Pagination

**编号**：`027-runtime-audit-pagination` | **日期**：2026-05-08
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: formal baseline freeze
Batch 2: cursor pagination implementation
Batch 3: regression, archive and PR handoff
```

---

## Batch 1：formal baseline freeze

### Task 1.1 冻结 runtime audit pagination 正式真值

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：specs/027-runtime-audit-pagination/spec.md, plan.md, tasks.md, task-execution-log.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. 027 明确 cursor contract、filter binding、错误码和响应字段。
  2. 027 明确不新增数据库、SIEM、通知、导出或租户 ABAC。
- **验证**：文档对账 + `uv run ai-sdlc program truth sync --execute --yes`

---

## Batch 2：cursor pagination implementation

### Task 2.1 实现 opaque cursor 与 page_info

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T11
- **文件**：src/agentops/api/server.py, tests/contract/test_ao27_ct_runtime_audit_pagination.py
- **可并行**：否
- **验收标准**：
  1. `GET /v1/audit/runtime?limit=...` 返回 `page_info.has_more` 与 `page_info.next_cursor`。
  2. 使用 `cursor` 可读取后续匹配记录，不重复第一页。
  3. 缺少 cursor 时保持 026 query response fields 兼容。
- **验证**：`uv run pytest tests/contract/test_ao27_ct_runtime_audit_pagination.py -q`

### Task 2.2 实现 cursor 安全拒绝与审计

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T21
- **文件**：src/agentops/api/server.py, tests/contract/test_ao27_ct_runtime_audit_pagination.py
- **可并行**：否
- **验收标准**：
  1. malformed cursor 返回 `AUDIT_CURSOR_INVALID`。
  2. cursor 与 filters 不匹配返回 `AUDIT_CURSOR_INVALID`。
  3. 非法 cursor 写入 `runtime.audit.read/rejected` durable audit record，且不泄露 path/secret/token marker。
- **验证**：`uv run pytest tests/contract/test_ao27_ct_runtime_audit_pagination.py -q`

---

## Batch 3：regression, archive and PR handoff

### Task 3.1 完成跨阶段回归与归档

- **任务编号**：T31
- **优先级**：P1
- **依赖**：T21, T22
- **文件**：specs/027-runtime-audit-pagination/task-execution-log.md, development-summary.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. AO23-AO27 合同回归通过。
  2. `ruff`、`verify constraints` 和 `program truth sync` 通过。
  3. execution log 与 development summary 记录实际命令和结果。
- **验证**：`uv run pytest tests/contract/test_ao23_ct_production_runtime_boundary.py tests/contract/test_ao24_ct_durable_audit_log.py tests/contract/test_ao25_ct_production_audit_coverage.py tests/contract/test_ao26_ct_runtime_audit_query.py tests/contract/test_ao27_ct_runtime_audit_pagination.py -q`
