# 开发摘要：022 Agent Store Summary HTTP Contract

## 交付内容

- 新增 `GET /v1/store-summary/{agent_id}` HTTP route。
- route 基于 repository run events 计算 evidence summary，并复用 AgentOps `build_agent_store_echo_summary`。
- 请求必须指定 `version` 和 `run_id`，可选 `schema_version` 默认 `1.0`。
- Summary 增加 `agentops_fact_owner`、`agent_store_consumer_boundary`、`quality_state`、`raw_access_state`、`redaction_policy` 和 `data_classification`。
- OpenAPI 补齐 Store Summary query、error responses 和 summary schema。
- AO22 契约测试覆盖成功、L5 降级、缺参、unsupported schema、run mismatch、display-only boundary 和敏感字段隔离。

## 边界声明

- AgentOps 是 summary 中 evidence、risk、approval、quality 和 policy requirement 的事实源。
- Agent Store 只消费展示 summary、deep links 和允许的 display actions。
- Console/Agent Store 不读取 raw payload，不展示 token，不推导 active、`verified_loaded` 或 L5。

## 验证

- `uv run pytest tests/contract/test_ao22_ct_agent_store_summary_http_contract.py tests/contract/test_ao6_ct_agent_store_discovery_audit.py tests/contract/test_ao7_ct_agent_store_console_audit_workbench.py -q`：通过。
- `uv run pytest tests/contract/test_ao22_ct_agent_store_summary_http_contract.py tests/contract/test_ao_ct_005_store_summary.py -q`：通过。
- `uv run ruff check src tests`：通过。
- `uv run pytest tests -q`：通过。
- `uv run ai-sdlc verify constraints`：no BLOCKERs。
- `uv run ai-sdlc program validate`：PASS，保留 `prd_path is empty` 非阻断提示。
- `uv run ai-sdlc recover --reconcile`：已将 checkpoint 对齐到 022。
- `uv run ai-sdlc run --dry-run`：Stage close PASS。
- `uv run ai-sdlc program truth sync --execute --yes`：truth snapshot ready，110/110 mapped。
- `uv run ai-sdlc workitem close-check --wi specs/022-agent-store-summary-http-contract --json`：提交前仅剩 git committed close-out 阻断，提交后复核。
