---
related_plan: "specs/048-quality-scorer-external-intake-index/plan.md"
related_specs:
  - "specs/046-quality-scorer-external-intake-http/spec.md"
  - "specs/047-quality-scorer-external-intake-readback/spec.md"
---

# 任务清单：Quality Scorer External Intake Index

**功能编号**：`048-quality-scorer-external-intake-index` | **日期**：2026-05-11  
**目标**：提供按 agent/version scope 的 external intake receipt index，保持 summary-only、只读和 no-auto-action 边界。

## 任务

- [x] T001 冻结 048 canonical spec/plan/tasks/log/summary。
- [x] T002 登记 `quality_scorer_external_intake_index.v1` contract 与 `create_app()` route。
- [x] T003 新增 repository scoped receipt listing。
- [x] T004 新增 `GET /v1/quality/scorers/external-intake/index` HTTP route、limit 校验和最小 audit。
- [x] T005 新增 AO48 contract tests，覆盖 registry、successful index、query-required、scope denial、invalid limit audit 和 repository scope。
- [x] T006 运行 AO45/AO46/AO47/AO48 定向回归、完整 pytest、ruff、AI-SDLC constraints 和 close-check。

后续 PR 收口动作：提交、推送、创建 PR、触发 `@codex review` 并创建 5 分钟 PR 收口 heartbeat。

## 验收命令

```zsh
uv run pytest tests/contract/test_ao48_ct_quality_scorer_external_intake_index.py tests/contract/test_ao47_ct_quality_scorer_external_intake_readback.py tests/contract/test_ao46_ct_quality_scorer_external_intake_http.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py tests/unit/test_runtime_contracts.py::test_runtime_contract_registry_covers_p0_contracts -q
uv run pytest -q
uv run ruff check src/agentops/api/app.py src/agentops/api/server.py src/agentops/core/runtime_contracts.py src/agentops/storage/repository.py tests/contract/test_ao48_ct_quality_scorer_external_intake_index.py
uv run ruff format --check src/agentops/api/app.py src/agentops/api/server.py src/agentops/core/runtime_contracts.py src/agentops/storage/repository.py tests/contract/test_ao48_ct_quality_scorer_external_intake_index.py
uv run ai-sdlc verify constraints
python -m ai_sdlc workitem close-check --wi specs/048-quality-scorer-external-intake-index --json
```
