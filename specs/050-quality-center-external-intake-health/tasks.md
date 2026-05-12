# 任务清单：Quality Center External Intake Health

related_plan: "specs/050-quality-center-external-intake-health/plan.md"
depends_on:
  - "specs/049-quality-scorer-external-intake-summary/spec.md"

**功能编号**：`050-quality-center-external-intake-health` | **日期**：2026-05-11  
**目标**：把 external scorer intake receipt 健康态接入 Quality Center workbench，保持 summary-only、只读和 no-auto-action 边界。

## 任务

- [x] T001 冻结 050 canonical spec/plan/tasks/log/summary。
- [x] T002 登记 `quality_center_external_intake_health.v1` contract，并扩展 `quality_center_workbench.v1` required fields。
- [x] T003 扩展 Quality Center workbench：每个 agent summary 输出 `external_intake_health`，顶层输出 `external_intake_panel`。
- [x] T004 增加 required external intake 缺失时的 `external_intake` manual review item。
- [x] T005 新增 AO50 contract tests，覆盖 registry、receiving receipts、required absence manual review、URI no-raw echo。
- [x] T006 运行定向回归、ruff、AI-SDLC constraints/truth/close-check。
- [x] T007 记录提交、推送、PR 与 `@codex review` 收口计划。

## 验证命令

```bash
uv run pytest tests/contract/test_ao50_ct_quality_center_external_intake_health.py tests/contract/test_ao42_ct_quality_center_workbench.py tests/contract/test_ao49_ct_quality_scorer_external_intake_summary.py -q
uv run ruff check src/agentops/core/operations.py src/agentops/core/runtime_contracts.py tests/contract/test_ao50_ct_quality_center_external_intake_health.py
uv run ruff format --check src/agentops/core/operations.py src/agentops/core/runtime_contracts.py tests/contract/test_ao50_ct_quality_center_external_intake_health.py
python -m ai_sdlc workitem close-check --wi specs/050-quality-center-external-intake-health --json
```
