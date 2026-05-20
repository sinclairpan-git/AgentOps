# 实施计划：P2 Ecosystem Governance Console

**功能编号**：`054-p2-ecosystem-governance-console`  
**日期**：2026-05-12  
**输入**：`specs/039-p2-ecosystem-governance/spec.md`、`specs/014-console-connector-health-workbench/spec.md`、`/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md`

## 概览

AO54 将 AO39 P2-B summary-only projections 接入现有 Connector Status Console。实现只扩展 snapshot/view-model、前端校验和页面展示，不新增真实 MCP/A2A Gateway、不 dispatch exporter、不执行 Runtime、不发送通知。

## 技术上下文

**后端**：`src/agentops/api/console_snapshot.py`  
**既有投影**：`src/agentops/core/operations.py` 的 AO39 builders  
**前端**：`apps/agentops-console/src/data/agentOpsApiClient.js`、`apps/agentops-console/src/views/ConnectorStatusView.js`  
**测试**：`tests/contract/test_ao4_ct_console_api.py`、`apps/agentops-console/tests/console-contract.test.mjs`

## 宪章检查

- Summary-only：只展示 projection 摘要和 hash/ref，不展示 raw config/payload。
- No auto action：不执行 Runtime、MCP/A2A、exporter dispatch、Store write 或 notification。
- Backward compatible：旧快照通过 legacy fallback 获取 empty/not_configured ecosystem governance。
- Contract-first：AO4 和 console contract 先锁定字段、安全边界和 UI 文案。

## 文件影响

```text
src/agentops/api/console_snapshot.py
tests/contract/test_ao4_ct_console_api.py
apps/agentops-console/src/data/agentOpsApiClient.js
apps/agentops-console/src/views/ConnectorStatusView.js
apps/agentops-console/tests/console-contract.test.mjs
program-manifest.yaml
specs/054-p2-ecosystem-governance-console/*
.ai-sdlc/work-items/054-p2-ecosystem-governance-console/resume-pack.yaml
```

## 实施阶段

### Phase 0：formal baseline

冻结 spec/plan/tasks/log/summary，明确 054 只做 Console 展示。

### Phase 1：snapshot + contracts

扩展 Console snapshot `connectorWorkbench.ecosystemGovernance`；AO4 contract 覆盖 sample fixture、repository-backed projection 和 no-auto-action flags。

### Phase 2：frontend validation

扩展 API client validation 和 legacy fallback；拒绝 automatic dispatch、Runtime action、Store action 和 unsafe raw references。

### Phase 3：Connector Status UI

页面增加生态治理 metrics、MCP/A2A、exporter dry-run、handoff 和 risk profile tables。

### Phase 4：verification + close

运行 pytest、npm test/build、ruff、AI-SDLC truth/close-check，记录总结。

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| 页面把 exporter dry-run 误导为已发送 | validation 要求 `external_write_enabled=false` 和 `network_dispatch_performed=false` |
| MCP/A2A endpoint 暴露 URL/secret | 后端 safe text + 前端 unsafe audit reference 拦截 |
| 旧快照缺字段导致 Console 崩溃 | legacy fallback 补 empty ecosystem governance |
| Handoff/risk profile 被误作自动处置 | UI 文案和 flags 明确只读人工复核 |

## 非目标

- 真实 MCP/A2A Gateway。
- 真实 exporter dispatch/network write。
- Runtime handoff 执行、重试或调度。
- 自动 disable、Store write、publish 或 notification。
