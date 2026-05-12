# 任务清单：P2 Ecosystem Governance Console

related_plan: "specs/054-p2-ecosystem-governance-console/plan.md"
depends_on:
  - "specs/039-p2-ecosystem-governance/spec.md"

**功能编号**：`054-p2-ecosystem-governance-console` | **日期**：2026-05-12  
**目标**：把 AO39 P2-B ecosystem governance projections 接入 Connector Status Console，保持 summary-only、只读和 no-auto-action 边界。

## 任务

- [x] T001 冻结 054 canonical spec/plan/tasks。
- [x] T002 扩展 Console snapshot ecosystem governance fields 和 AO4 contract tests。
- [x] T003 扩展前端 API client validation/legacy fallback。
- [x] T004 扩展 Connector Status 页面 ecosystem metrics 和 tables。
- [x] T005 运行 pytest、npm test/build、ruff、AI-SDLC constraints/truth/close-check。
- [x] T006 记录开发总结与恢复包。

## 验证命令

```bash
uv run pytest tests/contract/test_ao4_ct_console_api.py tests/contract/test_ao39_ct_p2_ecosystem_governance.py -q
npm test --prefix apps/agentops-console
npm run build --prefix apps/agentops-console
uv run ruff check src/agentops/api/console_snapshot.py tests/contract/test_ao4_ct_console_api.py
uv run ruff format --check src/agentops/api/console_snapshot.py tests/contract/test_ao4_ct_console_api.py
python -m ai_sdlc workitem close-check --wi specs/054-p2-ecosystem-governance-console --json
```
