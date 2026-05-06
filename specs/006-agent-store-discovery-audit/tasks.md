# 任务分解：Agent Store 接入、未注册发现与运行审计

**功能编号**：`006-agent-store-discovery-audit`

## Batch 1：契约与文档

### T11 冻结 006 规格

- **状态**：已完成
- **文件**：`spec.md`、`plan.md`、`contracts/agent-store-discovery-audit-contract.md`
- **验收**：AO6-CT-001 到 AO6-CT-008 明确。

## Batch 2：Agent Store 元数据消费

### T21 元数据快照缓存

- **状态**：已完成
- **文件**：`src/agentops/storage/repository.py`、`src/agentops/core/agent_store.py`
- **验收**：AgentOps 可消费 Agent Store 元数据但不改注册事实源。

## Batch 3：未注册发现与运行审计

### T31 Discovery 与 Audit 内核

- **状态**：已完成
- **文件**：`src/agentops/core/agent_store.py`、`src/agentops/api/agent_store.py`
- **验收**：未注册 Agent/Skill 可发现；run audit 有 deep links 且不暴露 raw payload。

### T32 Store 回显摘要

- **状态**：已完成
- **文件**：`src/agentops/api/store_summary.py`
- **验收**：summary 含 policy_requirement、discovery_gap_ids、run_audit。

## Batch 4：Console 与验证

### T41 Console 风险回显

- **状态**：已完成
- **文件**：`src/agentops/api/console_snapshot.py`
- **验收**：Agent Store 缺元数据时 connector degraded，Risk Triage 出现 Agent Store 风险。

### T42 契约与回归测试

- **状态**：已完成
- **命令**：`uv run pytest tests/contract/test_ao6_ct_agent_store_discovery_audit.py -q`、`uv run pytest tests -q`、`uv run ruff check src tests`、`npm test`、`npm run build`、`uv run ai-sdlc verify constraints`
- **验收**：AO6 契约、后端全量、前端契约、前端构建和约束验证均通过。
