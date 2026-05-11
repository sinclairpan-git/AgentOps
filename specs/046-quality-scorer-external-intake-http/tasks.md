---
related_plan: "specs/046-quality-scorer-external-intake-http/plan.md"
related_doc:
  - "specs/045-quality-scorer-external-intake/spec.md"
  - "specs/044-quality-scorer-execution-evidence/spec.md"
---
# 任务分解：Quality Scorer External Intake HTTP

**功能编号**：`046-quality-scorer-external-intake-http` | **日期**：2026-05-11  
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: HTTP route contract and implementation
```

---

## Batch 1：HTTP route contract and implementation

### Task 1.1 冻结 formal docs

- **任务编号**：T11
- **优先级**：P1
- **依赖**：045-quality-scorer-external-intake
- **文件**：specs/046-quality-scorer-external-intake-http/*
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. 046 canonical formal docs 已直接位于 `specs/046-quality-scorer-external-intake-http/`
  2. scope 明确为 external scorer intake HTTP/webhook 边界，不包含 AgentOps 执行 scorer
  3. no-raw/no-auto-rollout/no-Store-write/no-notification 边界写入 spec/plan/tasks
- **验证**：文档对账 + `uv run ai-sdlc verify constraints`

### Task 1.2 登记 AO46 HTTP contract

- **任务编号**：T12
- **优先级**：P1
- **依赖**：T11
- **文件**：src/agentops/core/runtime_contracts.py, tests/contract/test_ao46_ct_quality_scorer_external_intake_http.py
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. `quality_scorer_external_intake_http.v1` 存在 required fields、enum fields、error codes 和 AO46 contract tests
  2. contract 声明 route/method/status/error/scope 边界
  3. registry validation 通过且不破坏既有 P0 contract registry
- **验证**：AO46 registry test + `tests/unit/test_runtime_contracts.py::test_runtime_contract_registry_covers_p0_contracts`

### Task 1.3 实现 HTTP route

- **任务编号**：T13
- **优先级**：P1
- **依赖**：T12
- **文件**：src/agentops/api/server.py, src/agentops/api/app.py
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. `POST /v1/quality/scorers/external-intake` 接收 `agent_id/version/external_result`
  2. `idempotency_key` 可来自 body 或 `Idempotency-Key` header
  3. signature/source trust 可来自 body 或 scorer-specific headers
  4. route 委托 045 core intake，不复制 scorer 执行或 sample boundary 逻辑
  5. accepted/deduplicated 返回 `202 Accepted`
- **验证**：AO46 accepted HTTP intake 与 header fallback tests

### Task 1.4 增加生产 scope 与 audit

- **任务编号**：T14
- **优先级**：P1
- **依赖**：T13
- **文件**：src/agentops/api/auth.py, src/agentops/api/server.py, tests/contract/test_ao46_ct_quality_scorer_external_intake_http.py
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. 生产模式要求 `quality.scorer.intake.write`
  2. accepted/rejected/denied route 均写最小 audit record
  3. audit record 不包含 request body、raw payload、prompt、URL、token、credential secret 或 device key
  4. scope denial 不写 scorer execution evidence
- **验证**：AO46 production scope denial 与 no-body audit tests

### Task 1.5 回归验证与 close

- **任务编号**：T15
- **优先级**：P1
- **依赖**：T14
- **文件**：tests/contract/test_ao4_ct_console_api.py, specs/046-quality-scorer-external-intake-http/*
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. CORS contract 同步允许 scorer-specific headers 且不放开 wildcard origin
  2. AO45/AO46 定向回归通过
  3. 完整 pytest、ruff check、ruff format check 通过
  4. AI-SDLC truth sync、constraints、close-check 通过或仅剩提交前允许的 git closure 状态
- **验证**：统一验证命令见 task-execution-log.md

---

## 完成定义

- AO46 contract tests 通过。
- AO45/AO46 定向回归通过。
- AO40-AO46 Quality 链路回归通过。
- `uv run pytest -q` 通过。
- `uv run ruff check` 与 `uv run ruff format --check` 通过。
- `python -m ai_sdlc program truth sync --execute --yes` 已同步。
- `uv run ai-sdlc verify constraints` 无 BLOCKER。
- `python -m ai_sdlc workitem close-check --wi specs/046-quality-scorer-external-intake-http --json` 通过或仅剩提交/PR 前 disposition 说明。
