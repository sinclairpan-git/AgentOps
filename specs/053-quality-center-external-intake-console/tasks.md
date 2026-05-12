# 任务清单：Quality Center External Intake Console

related_plan: "specs/053-quality-center-external-intake-console/plan.md"
depends_on:
  - "specs/052-quality-center-external-intake-portfolio-http/spec.md"

**功能编号**：`053-quality-center-external-intake-console` | **日期**：2026-05-12  
**目标**：把 external intake health/panel/portfolio 接入 Console Quality Center 页面，保持 summary-only、只读和 no-auto-action 边界。

## 任务

- [x] T001 冻结 053 canonical spec/plan/tasks。
- [x] T002 扩展 Console snapshot external intake fields 和 AO4 contract tests。
- [x] T003 扩展前端 API client validation/legacy fallback。
- [x] T004 扩展 Quality Center 页面 external intake metrics、portfolio 和 per-agent columns。
- [x] T005 运行 pytest、npm test、ruff、Browser smoke、AI-SDLC constraints/truth/close-check。
- [x] T006 记录开发总结与恢复包。

## 验证命令

```bash
uv run pytest tests/contract/test_ao4_ct_console_api.py tests/contract/test_ao42_ct_quality_center_workbench.py tests/contract/test_ao50_ct_quality_center_external_intake_health.py tests/contract/test_ao51_ct_quality_center_external_intake_portfolio.py tests/contract/test_ao52_ct_quality_center_external_intake_portfolio_http.py -q
npm test --prefix apps/agentops-console
uv run ruff check src/agentops/api/console_snapshot.py tests/contract/test_ao4_ct_console_api.py
uv run ruff format --check src/agentops/api/console_snapshot.py tests/contract/test_ao4_ct_console_api.py
python -m ai_sdlc workitem close-check --wi specs/053-quality-center-external-intake-console --json
```
