# 开发摘要：SDLC v0.7.18 Executable Task Runtime Bridge

## 当前状态

本工作项已完成 AgentOps 侧产品实现和本地验证，等待 Ai_AutoSDLC producer 输出真实 outbox 后做双项目联调。

## 已冻结口径

- Ai_AutoSDLC v0.7.18 后，`verified_loaded` 是 adapter / host ingress 诊断字段，不是 AgentOps 主门禁。
- AgentOps readiness 主轴切换为 executable task、task guard、signed event chain、outbox receipt、EvidenceSummary、Policy / Guardrail 和 freshness。
- Ai_AutoSDLC Outbox 运行事实直接接入 AgentOps `/v1/runtime/events`；Agent Store 不作为必经中转。
- Console 目标形态为 task guard、outbox receipt、evidence readiness、adapter diagnostics 四分区。

## 已落地内容

1. AO56 contract tests 固定 fixture ingestion、task missing、guard blocked 和 Console vNext workbench。
2. Runtime contract registry 支持 `executable_task` / `code_guard` SDLC event。
3. Runtime ingestion 将 task / guard 事件映射为 summary-only trace spans，并持久化 runtime outbox receipt 摘要。
4. L5 readiness 废弃 `verified_loaded` 主路径硬门槛，改用 executable task 与 task guard。
5. Console SDLC workbench 新增 task guard、outbox receipt、evidence readiness、adapter diagnostics 四分区。

## 本地验证

- `python -m ai_sdlc run --dry-run`
- `uv run pytest tests/contract/test_ao34_ct_runtime_outbox_sdlc_trace_bridge.py tests/contract/test_ao56_ct_sdlc_executable_task_runtime_bridge.py tests/unit/test_l5_gate.py -q`
- `uv run ruff check ...`
- `npm test --prefix apps/agentops-console`
- `npm run build --prefix apps/agentops-console`
