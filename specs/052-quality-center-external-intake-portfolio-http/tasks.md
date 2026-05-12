# 任务清单：Quality Center External Intake Portfolio HTTP

related_plan: "specs/052-quality-center-external-intake-portfolio-http/plan.md"
depends_on:
  - "specs/051-quality-center-external-intake-portfolio/spec.md"

**功能编号**：`052-quality-center-external-intake-portfolio-http` | **日期**：2026-05-12  
**目标**：为 Quality Center external intake portfolio 增加只读 HTTP route，保持 summary-only、权限审计和 no-auto-action 边界。

## 任务

- [x] T001 冻结 052 canonical spec/plan/tasks。
- [x] T002 登记 `quality_center_external_intake_portfolio_http.v1` contract 与 `create_app()` route。
- [x] T003 实现 `GET /v1/quality/center/external-intake/portfolio` route、scope/limit 校验、生产读权限和最小 audit。
- [x] T004 新增 AO52 contract tests，覆盖 successful portfolio、required missing scopes、query-required、invalid scope/limit、production denial、URI no-raw echo。
- [x] T005 运行 AO50/AO51/AO52 定向回归、ruff、AI-SDLC constraints/truth/close-check。
- [x] T006 记录开发总结与恢复包。

## 验证命令

```bash
uv run pytest tests/contract/test_ao50_ct_quality_center_external_intake_health.py tests/contract/test_ao51_ct_quality_center_external_intake_portfolio.py tests/contract/test_ao52_ct_quality_center_external_intake_portfolio_http.py -q
uv run ruff check src/agentops/api/app.py src/agentops/api/server.py src/agentops/core/runtime_contracts.py tests/contract/test_ao52_ct_quality_center_external_intake_portfolio_http.py
uv run ruff format --check src/agentops/api/app.py src/agentops/api/server.py src/agentops/core/runtime_contracts.py tests/contract/test_ao52_ct_quality_center_external_intake_portfolio_http.py
python -m ai_sdlc workitem close-check --wi specs/052-quality-center-external-intake-portfolio-http --json
```
