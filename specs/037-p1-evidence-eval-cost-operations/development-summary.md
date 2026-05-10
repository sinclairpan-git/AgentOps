# Development Summary：P1 Evidence Eval Cost Operations

**工作项**：`037-p1-evidence-eval-cost-operations`  
**日期**：2026-05-10  
**状态**：实现完成，等待 PR 收口

## 完成内容

- 已将 037 formal docs 从模板替换为 P1-B 真实业务规格，承接 AO-P1-04 到 AO-P1-12。
- 已登记 P1-B contracts：Evidence access operation、EvalCase、runtime budget summary、DLQ operations projection、exporter operation、runtime SLO summary、Store governance projection。
- 已新增 `agentops.core.operations` 与 `agentops.api.operations`，提供 summary-only projection builders。
- Evidence raw access operation 只返回 request/audit/hash/ref，不返回原文；redaction failed 会排队 owner notification。
- EvalCase 只允许 failed/timeout/blocked/cancelled/degraded run 进入失败样本池，succeeded run 被拒绝。
- Runtime budget 从 TraceSpan summary 字段汇总 token、cost、latency；DLQ projection 只展示 retry/discard candidates 和 error stats。
- Exporter operation 固定 dry-run/no-write；Runtime SLO 和 Store governance projection 只提供 display-only 推荐动作。

## 验证结果

- `uv run pytest tests/contract/test_ao37_ct_p1_evidence_eval_cost_operations.py -q`：10 passed。
- `uv run pytest tests/contract/test_ao32_ct_evidence_health_summary_loop.py tests/contract/test_ao34_ct_runtime_outbox_sdlc_trace_bridge.py tests/contract/test_ao35_ct_p0_acceptance_gate.py tests/contract/test_ao37_ct_p1_evidence_eval_cost_operations.py -q`：35 passed。
- `uv run pytest -q`：PASS。
- `uv run ruff check ...`：All checks passed。
- `uv run ruff format --check ...`：通过。

## 非目标

- 不做 Console UI。
- 不发送 OTLP/OpenInference 网络写入。
- 不读取或返回 Evidence Vault 原文。
- 不执行 replay、discard、disable、publish 或 Runtime action。

## 下一步

- 完成完整本地回归、AI-SDLC verify/close-check、提交、推送并创建 PR。

## PR Review Fix

- 修复 Codex Review P1：Runtime SLO 现在会接收并传递 token/cost/latency budget thresholds，预算超限会进入 `at_risk/review_budget`。
- 修复 Codex Review P1：Runtime SLO 的 DLQ backlog 现在按当前 agent/version 过滤，其他 agent 的 DLQ 不会污染健康 agent 的 SLO。
- 新增 AO37 回归：预算阈值传递、unrelated DLQ isolation。
