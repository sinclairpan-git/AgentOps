# 任务清单：Quality Center External Intake Portfolio

related_plan: "specs/051-quality-center-external-intake-portfolio/plan.md"
depends_on:
  - "specs/050-quality-center-external-intake-health/spec.md"

**功能编号**：`051-quality-center-external-intake-portfolio` | **日期**：2026-05-12  
**目标**：把 external intake 跨 agent/version portfolio 汇总接入 Quality Center workbench，保持 summary-only、只读和 no-auto-action 边界。

## 任务

- [x] T001 冻结 051 canonical spec/plan/tasks。
- [x] T002 登记 `quality_center_external_intake_portfolio.v1` contract，并扩展 `quality_center_workbench.v1` required fields。
- [x] T003 扩展 Quality Center workbench：输出顶层 `external_intake_portfolio`。
- [x] T004 新增 AO51 contract tests，覆盖 multi-scope portfolio、required missing scopes、URI no-raw echo 和 no-auto-action。
- [x] T005 运行 AO50/AO51 定向回归、ruff、AI-SDLC constraints/close-check。
- [x] T006 记录开发总结与恢复包。

## 验证命令

```bash
uv run pytest tests/contract/test_ao50_ct_quality_center_external_intake_health.py tests/contract/test_ao51_ct_quality_center_external_intake_portfolio.py -q
uv run ruff check src/agentops/core/operations.py src/agentops/core/runtime_contracts.py src/agentops/api/operations.py tests/contract/test_ao51_ct_quality_center_external_intake_portfolio.py
uv run ruff format --check src/agentops/core/operations.py src/agentops/core/runtime_contracts.py src/agentops/api/operations.py tests/contract/test_ao51_ct_quality_center_external_intake_portfolio.py
python -m ai_sdlc workitem close-check --wi specs/051-quality-center-external-intake-portfolio --json
```
