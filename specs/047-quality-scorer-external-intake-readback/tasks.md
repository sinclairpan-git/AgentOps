---
related_plan: "specs/047-quality-scorer-external-intake-readback/plan.md"
related_doc:
  - "specs/045-quality-scorer-external-intake/spec.md"
  - "specs/046-quality-scorer-external-intake-http/spec.md"
---
# 任务分解：Quality Scorer External Intake Readback

**功能编号**：`047-quality-scorer-external-intake-readback` | **日期**：2026-05-11  
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: HTTP receipt readback contract and implementation
```

---

## Batch 1：HTTP receipt readback contract and implementation

### Task 1.1 冻结 formal docs

- **任务编号**：T11
- **优先级**：P1
- **依赖**：046-quality-scorer-external-intake-http
- **文件**：specs/047-quality-scorer-external-intake-readback/*
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. 047 canonical docs 已直接位于 `specs/047-quality-scorer-external-intake-readback/`
  2. scope 明确为只读 receipt readback，不包含 scorer execution、payload replay 或自动动作
  3. key-only/partial-scope HTTP readback 明确为非目标
- **验证**：文档对账 + `uv run ai-sdlc verify constraints`

### Task 1.2 登记 AO47 readback contract

- **任务编号**：T12
- **优先级**：P1
- **依赖**：T11
- **文件**：src/agentops/core/runtime_contracts.py, tests/contract/test_ao47_ct_quality_scorer_external_intake_readback.py
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. `quality_scorer_external_intake_readback.v1` 存在 required fields、enum fields、error codes 和 AO47 contract tests
  2. contract 声明完整 query scope 和 read-only 边界
  3. registry validation 通过
- **验证**：AO47 registry test + runtime contract registry regression

### Task 1.3 实现 HTTP readback route

- **任务编号**：T13
- **优先级**：P1
- **依赖**：T12
- **文件**：src/agentops/api/server.py, src/agentops/api/app.py
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. `GET /v1/quality/scorers/external-intake` 按 `agent_id/version/idempotency_key` 返回已有 receipt
  2. 缺少 query 字段返回 `QUALITY_SCORER_INTAKE_RECEIPT_QUERY_REQUIRED`
  3. 未命中返回 `QUALITY_SCORER_INTAKE_RECEIPT_NOT_FOUND`
  4. 查询不新增 execution evidence
- **验证**：AO47 readback success/query/not-found tests

### Task 1.4 增加生产 read scope 与 audit

- **任务编号**：T14
- **优先级**：P1
- **依赖**：T13
- **文件**：src/agentops/api/auth.py, src/agentops/api/server.py, tests/contract/test_ao47_ct_quality_scorer_external_intake_readback.py
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. 生产模式要求 `quality.scorer.intake.read`
  2. accepted/rejected/denied readback 写最小 audit
  3. audit 不包含 request body、raw payload、prompt、URL、token、credential secret 或 device key
- **验证**：AO47 production scope denial 与 no-raw audit tests

### Task 1.5 回归验证与 close

- **任务编号**：T15
- **优先级**：P1
- **依赖**：T14
- **文件**：specs/047-quality-scorer-external-intake-readback/*
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. AO45/AO46/AO47 定向回归通过
  2. 完整 pytest、ruff check、ruff format check 通过
  3. AI-SDLC truth sync、constraints、close-check 通过或仅剩提交前允许的 git closure 状态
- **验证**：统一验证命令见 task-execution-log.md

---

## 完成定义

- AO47 contract tests 通过。
- AO45/AO46/AO47 定向回归通过。
- `uv run pytest -q` 通过。
- `uv run ruff check` 与 `uv run ruff format --check` 通过。
- `python -m ai_sdlc program truth sync --execute --yes` 已同步。
- `uv run ai-sdlc verify constraints` 无 BLOCKER。
- `python -m ai_sdlc workitem close-check --wi specs/047-quality-scorer-external-intake-readback --json` 通过或仅剩提交前 git closure 挡板。
