# 开发总结：Quality Center External Intake Portfolio HTTP

**编号**：`052-quality-center-external-intake-portfolio-http`  
**日期**：2026-05-12  
**分支**：`codex/052-quality-center-external-intake-portfolio-http`

## 交付内容

- 新增 `quality_center_external_intake_portfolio_http.v1` contract 和错误码定义。
- 新增 `GET /v1/quality/center/external-intake/portfolio` route discovery。
- 实现只读 HTTP route，支持 repeated `scope=agent_id@version`、`required_scope=agent_id@version` 和 scope limit。
- 生产模式要求 `quality.scorer.intake.read` scope，并对 accepted/rejected/denied 写最小 audit。
- 增加 AO52 contract tests，覆盖 successful portfolio、required missing scopes、query-required、invalid scope/limit、production denial 和 URI no-raw echo。

## 安全与治理边界

- 不执行 scorer，不创建新的 execution evidence。
- 不 replay external result，不返回 raw payload/prompt/diff/terminal。
- 不自动 rollout/template switch，不写 Store，不发通知。
- Route 不读取 request body，不在 audit 中记录 query 原文；URI-style identity 仅用于 hash lookup，response 使用 safe label/redaction 和 hash identity。

## 验证

- `uv run pytest tests/contract/test_ao50_ct_quality_center_external_intake_health.py tests/contract/test_ao51_ct_quality_center_external_intake_portfolio.py tests/contract/test_ao52_ct_quality_center_external_intake_portfolio_http.py -q`：通过，15 tests passed。
- `uv run pytest tests/contract/test_ao50_ct_quality_center_external_intake_health.py tests/contract/test_ao51_ct_quality_center_external_intake_portfolio.py tests/contract/test_ao52_ct_quality_center_external_intake_portfolio_http.py tests/contract/test_ao31_ct_runtime_governance_foundation.py::test_ao31_ct_001_contract_registry_has_required_runtime_governance_entries tests/unit/test_runtime_contracts.py::test_runtime_contract_registry_covers_p0_contracts -q`：通过，17 tests passed。
- `uv run ruff check src/agentops/api/app.py src/agentops/api/server.py src/agentops/core/runtime_contracts.py tests/contract/test_ao52_ct_quality_center_external_intake_portfolio_http.py`：通过。
- `uv run ruff format --check src/agentops/api/app.py src/agentops/api/server.py src/agentops/core/runtime_contracts.py tests/contract/test_ao52_ct_quality_center_external_intake_portfolio_http.py`：通过。
- `python -m ai_sdlc verify constraints`：通过，无 BLOCKER。
- `uv run ai-sdlc verify constraints`：通过，无 BLOCKER。
- `uv run pytest -q`：通过。
- `python -m ai_sdlc program truth sync --execute --yes`：通过，52/52 mapped。

## 非目标

- 未新增 Console UI。
- 未执行 external scorer 或自动 rollout。
