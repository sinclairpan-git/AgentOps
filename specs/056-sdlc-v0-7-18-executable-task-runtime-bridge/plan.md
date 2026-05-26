# 实施计划：SDLC v0.7.18 Executable Task Runtime Bridge

## 目标

将 AgentOps 的 Ai_AutoSDLC 集成主轴从 adapter proof / `verified_loaded` 切换到 executable task / task guard / runtime receipt / evidence readiness，同时保留 adapter status 作为只读诊断。

## 技术切片

### Slice 1：双边契约冻结

- 新增 cross-project contract，冻结 producer / consumer、payload、batch、receipt、错误码和 Console 映射。
- 明确 Agent Store 不是 Outbox 运行事实必经中转层。
- 明确 Ops-direct producer identity 与 Store-mediated activation 的差异。

验证：文档审查、contract fixture schema 审查。

### Slice 2：Runtime contract registry 扩展

- 在 runtime contracts 中新增或扩展 SDLC task guard payload。
- 增加 `executable_task_prepared` 与 `code_change_guard_result` 的 required fields / enum fields。
- 更新 ingestion validation，保持 raw payload 隔离。

验证：新增 contract tests 首先红灯，再实现。

### Slice 3：Evidence / L5 readiness 改造

- 从 `_governance_state(adapter_state)` 转向 readiness 输入：
  - executable task linkage
  - task guard state
  - signed event chain
  - outbox receipt state
  - policy / guardrail state
  - freshness / audit
- `verified_loaded` 仅作为 diagnostic，不参与主门禁。

验证：L5 / EvidenceSummary 单测和契约测试。

### Slice 4：Console snapshot 与前端重构

- `sdlcRunWorkbench` 新增 `taskGuard`、`outboxReceipts`、`evidenceReadiness`、`adapterDiagnostics`。
- 保留旧字段兼容 fallback，但不得由旧字段推导 ready。
- 更新 mock data 与 validator。

验证：`npm test`、`npm run build`、AO15/AO56 contract tests。

### Slice 5：端到端联调

- 使用 Ai_AutoSDLC v0.7.18 sample producer batch：
  - task ready
  - task missing
  - guard blocked
  - receipt delivered_with_diagnostics
- 验证 `/v1/runtime/events` -> receipt -> Console snapshot -> Store summary。

验证：定向 pytest + 前端 contract + dry-run。

## 风险与回退

| 风险 | 缓解 |
|---|---|
| 旧 Console 仍显示 verified_loaded 主状态 | 前端 validator 增加 `ADAPTER_DIAGNOSTIC_OVERREACH` 负例 |
| L5 逻辑过度绑定新字段导致历史 run 全部降级 | 保留 legacy run 兼容层，但 legacy 只能显示 diagnostic / historical，不进入新 actual L5 |
| SDLC producer 与 Ops schema 不一致 | 双边 contract fixture 先冻结，两个项目共用样例 |
| Store-mediated 与 Ops-direct identity 混淆 | receipt / summary 明确 `producer_identity_kind`，不得伪造 installation |

## 验证命令

```bash
python -m ai_sdlc run --dry-run
uv run pytest tests/contract/test_ao34_ct_runtime_outbox_sdlc_trace_bridge.py tests/contract/test_ao15_ct_console_sdlc_run_workbench.py -q
npm test --prefix apps/agentops-console
npm run build --prefix apps/agentops-console
```
