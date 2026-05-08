# 任务分解：Runtime Audit Export Bundle

**编号**：`029-runtime-audit-export-bundle` | **日期**：2026-05-08
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: formal truth, contract tests, implementation, verification
```

---

## Batch 1：runtime audit export bundle

### Task 1.1 冻结 runtime audit export bundle 正式真值

- **任务编号**：T11
- **优先级**：P0
- **依赖**：028-runtime-audit-export-manifest
- **文件**：specs/029-runtime-audit-export-bundle/spec.md, plan.md, tasks.md
- **可并行**：否
- **验收标准**：
  1. 029 明确覆盖 manifest-gated metadata-only export bundle。
  2. 029 明确不新增数据库、SIEM、通知、签名 URL、对象存储、tenant ABAC 或 raw audit export。
  3. 029 明确新增专用 `runtime.audit.export` scope。
- **验证**：文档对账 + `uv run ai-sdlc program truth sync --execute --yes`

### Task 1.2 新增 AO29 export bundle 合同测试

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：tests/contract/test_ao29_ct_runtime_audit_export_bundle.py
- **可并行**：否
- **验收标准**：
  1. 测试覆盖 manifest 匹配成功生成 bundle。
  2. 测试覆盖 viewer / read-only scope denied。
  3. 测试覆盖 manifest mismatch rejected。
  4. 测试覆盖敏感 marker 不外泄和 route manifest。
- **验证**：`uv run pytest tests/contract/test_ao29_ct_runtime_audit_export_bundle.py -q`

### Task 1.3 实现 runtime audit export bundle route

- **任务编号**：T13
- **优先级**：P0
- **依赖**：T12
- **文件**：src/agentops/api/auth.py, src/agentops/api/server.py, src/agentops/api/app.py
- **可并行**：否
- **验收标准**：
  1. `POST /v1/audit/runtime/export-bundle` 要求 `runtime.audit.export`。
  2. route 校验 manifest id/digest 与当前 filtered metadata 一致。
  3. response 返回 bounded sanitized metadata records 和 bundle digest。
  4. accepted/denied/rejected 均写入 durable audit。
- **验证**：`uv run pytest tests/contract/test_ao29_ct_runtime_audit_export_bundle.py -q`

### Task 1.4 回归验证与归档

- **任务编号**：T14
- **优先级**：P1
- **依赖**：T13
- **文件**：specs/029-runtime-audit-export-bundle/task-execution-log.md, development-summary.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. AO23-AO29 contract regression 通过。
  2. ruff 与 AI-SDLC constraints 通过。
  3. workitem close-check ready。
- **验证**：`uv run pytest ...AO23...AO29... -q`、`uv run ruff check src tests`、`uv run ai-sdlc verify constraints`、`uv run ai-sdlc workitem close-check --wi specs/029-runtime-audit-export-bundle`
