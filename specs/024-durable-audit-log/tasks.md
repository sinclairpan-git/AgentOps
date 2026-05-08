# 任务分解：Durable Audit Log

**编号**：`024-durable-audit-log` | **日期**：2026-05-08
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: formal scope freeze
Batch 2: durable audit adapter
Batch 3: HTTP production boundary integration and verification
```

---

## Batch 1：formal scope freeze

### Task 1.1 冻结 durable audit 正式真值

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, task-execution-log.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. 024 明确覆盖 durable audit log，不漂移为完整数据库迁移。
  2. 024 明确禁止写入 raw payload、token、device key 和 credential secret。
- **验证**：文档对账 + `ai-sdlc program truth sync --execute --yes`

## Batch 2：durable audit adapter

### Task 2.1 实现 JSONL 审计适配器

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T11
- **文件**：src/agentops/storage/audit.py, tests/contract/test_ao24_ct_durable_audit_log.py
- **可并行**：否
- **验收标准**：
  1. `JsonlAuditLog.append()` 自动创建目录并追加一行 JSON。
  2. 新 audit log 实例能读取既有记录。
  3. `AuditRecord` schema 只包含允许字段。
- **验证**：`uv run pytest tests/contract/test_ao24_ct_durable_audit_log.py -q`

## Batch 3：HTTP production boundary integration

### Task 3.1 接入生产授权与事件写入审计

- **任务编号**：T31
- **优先级**：P1
- **依赖**：T21
- **文件**：src/agentops/api/server.py, src/agentops/api/app.py, tests/contract/test_ao24_ct_durable_audit_log.py
- **可并行**：否
- **验收标准**：
  1. 生产鉴权拒绝追加 `outcome=denied` 审计记录。
  2. 授权事件写入追加 `outcome=accepted` 审计记录。
  3. 审计 JSONL 原文不包含敏感字段名和值。
  4. route manifest 声明 durable audit boundary。
- **验证**：`uv run pytest tests/contract/test_ao23_ct_production_runtime_boundary.py tests/contract/test_ao24_ct_durable_audit_log.py -q`

## Batch 4：release verification

### Task 4.1 完成质量门禁与归档

- **任务编号**：T41
- **优先级**：P1
- **依赖**：T31
- **文件**：task-execution-log.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. 定向合同、ruff、AI-SDLC constraints 通过。
  2. task execution log 记录实际命令与结果。
  3. manifest truth sync 后 024 状态可追踪。
- **验证**：`uv run ruff check src tests`、`uv run ai-sdlc verify constraints`
