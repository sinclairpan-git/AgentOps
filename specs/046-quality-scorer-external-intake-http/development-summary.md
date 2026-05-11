# 开发总结：Quality Scorer External Intake HTTP

**编号**：`046-quality-scorer-external-intake-http`  
**日期**：2026-05-11  
**状态**：已完成

## 已完成

- 创建 046 formal docs，承接 AO45 external scorer intake 的 HTTP/webhook 边界。
- 登记 `quality_scorer_external_intake_http.v1` contract。
- 实现 `POST /v1/quality/scorers/external-intake`。
- `create_app()` 已声明新 route。
- 生产模式新增 `quality.scorer.intake.write` scope。
- HTTP route 支持 body/header 中的 `idempotency_key`、signature 和 source trust metadata，并委托 045 core intake。
- accepted/rejected/denied 均写最小 audit record，audit 不记录 request body。
- 增加 AO46 contract tests，覆盖 registry、accepted HTTP intake、header fallback、missing envelope、raw rejection/no-body audit、production scope denial。

## 验证

- `uv run pytest tests/contract/test_ao46_ct_quality_scorer_external_intake_http.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py tests/unit/test_runtime_contracts.py::test_runtime_contract_registry_covers_p0_contracts -q`：通过，23 passed。

## 边界

- 不执行 scorer。
- 不读取 raw evidence/prompt/diff/terminal。
- 不自动 rollout、Store write 或 notification。
