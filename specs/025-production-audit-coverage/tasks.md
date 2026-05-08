# 任务分解：Production Audit Coverage

**编号**：`025-production-audit-coverage` | **日期**：2026-05-08
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: formal scope freeze
Batch 2: protected read route audit
Batch 3: credential write route audit and verification
```

---

## Batch 1：formal scope freeze

### Task 1.1 冻结 production audit coverage 正式真值

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, task-execution-log.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. 025 明确只扩展生产受保护 route audit coverage。
  2. 025 明确不新增数据库、audit query API、IAM/OIDC 或多租户权限。
- **验证**：文档对账 + `ai-sdlc program truth sync --execute --yes`

## Batch 2：protected read route audit

### Task 2.1 为受保护读路由补 accepted/rejected audit

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T11
- **文件**：src/agentops/api/server.py, tests/contract/test_ao25_ct_production_audit_coverage.py
- **可并行**：否
- **验收标准**：
  1. Console snapshot 成功读取写入 `console.snapshot.read/accepted`。
  2. Store summary query 缺失写入 `store.summary.read/rejected`。
  3. Credential status success/not-found 写入 `credential.read` accepted/rejected。
- **验证**：`uv run pytest tests/contract/test_ao25_ct_production_audit_coverage.py -q`

## Batch 3：credential write route audit and verification

### Task 3.1 为 revoke/reissue 补 accepted/rejected audit

- **任务编号**：T31
- **优先级**：P1
- **依赖**：T21
- **文件**：src/agentops/api/server.py, tests/contract/test_ao25_ct_production_audit_coverage.py
- **可并行**：否
- **验收标准**：
  1. Credential revoke 成功写入 `credential.revoke/accepted`。
  2. Credential reissue not-found 写入 `credential.reissue/rejected`。
  3. Audit JSONL 不包含 credential secret、token、device key、raw payload。
- **验证**：`uv run pytest tests/contract/test_ao25_ct_production_audit_coverage.py -q`

### Task 3.2 完成生产边界回归和归档

- **任务编号**：T32
- **优先级**：P1
- **依赖**：T31
- **文件**：task-execution-log.md, development-summary.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. AO23/AO24/AO25 联跑通过。
  2. ruff 与 AI-SDLC constraints 通过。
  3. execution log 与 development summary 记录实际验证。
- **验证**：`uv run pytest tests/contract/test_ao23_ct_production_runtime_boundary.py tests/contract/test_ao24_ct_durable_audit_log.py tests/contract/test_ao25_ct_production_audit_coverage.py -q`
