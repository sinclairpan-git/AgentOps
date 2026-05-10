# 开发总结：P0 End-to-End Acceptance Gate

**工作项**：`035-p0-end-to-end-acceptance-gate`  
**日期**：2026-05-09  
**状态**：实现中

## 变更摘要

- 新增 `p0_acceptance_gate.v1` contract，作为 P0 端到端闭环的机器可判定结果。
- 新增只读 `build_p0_acceptance_gate()` projection，复用现有 Runtime、Evidence、Health、Policy、Grant、Guardrail、SDLC bridge 和 Store echo 能力。
- 新增 AO35 contract tests，覆盖完整闭环通过、缺口失败和 no raw leak。

## 边界确认

- AgentOps 仍只接收、校验、投影和验收事实，不执行 Agent 或 Runtime。
- Gate 不持久化历史结果，不新增 HTTP route，不读取 Evidence Vault 原文。
- Outbox receipt、dry-run 或局部 summary 单独成功不构成 P0 pass，必须所有 required checks 通过。

## 验证

- `uv run pytest tests/contract/test_ao35_ct_p0_acceptance_gate.py -q`：PASS。
- `ai-sdlc program truth sync --execute --yes`：ready，source inventory 35/35 mapped。
- `uv run pytest tests/contract/test_ao31_ct_runtime_governance_foundation.py tests/contract/test_ao32_ct_evidence_health_summary_loop.py tests/contract/test_ao33_ct_policy_grant_guardrail_control.py tests/contract/test_ao34_ct_runtime_outbox_sdlc_trace_bridge.py tests/contract/test_ao35_ct_p0_acceptance_gate.py -q`：PASS。
- `uv run ruff check src tests`：PASS。
- `uv run ai-sdlc verify constraints`：PASS，no BLOCKERs。
- `uv run pytest -q`：PASS。

## Review Fixes

- 修复 Codex Review P1：P0 policy check 现在要求 `constraints.agentops_executes_runtime` 显式存在且为 `False`，缺失约束不会被默认视为合规。
- 修复 Codex Review P2：summary-only raw leak check 改为按敏感字段名递归检查，避免普通 metadata 中出现 `prompt` 字样导致误失败。
