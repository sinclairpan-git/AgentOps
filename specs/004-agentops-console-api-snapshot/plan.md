# 实施计划：AgentOps Console API 快照与联调闭环

**功能编号**：`004-agentops-console-api-snapshot`  
**日期**：2026-05-06  
**输入**：`spec.md`、003 Console MVP、001/002 后端契约

## 技术上下文

- 后端：Python 3.11+，仅使用标准库 HTTP server，不新增运行时依赖。
- 前端：Vue 2 + Vite + SDLC 企业 Vue2 组件库白名单 Provider。
- 数据：本阶段为 Console snapshot 聚合模型，不接入生产数据库。
- 验证：Python contract/unit tests + 前端 Node contract test + Vite build。

## 架构决策

1. **标准库优先**：使用 `http.server.ThreadingHTTPServer` 实现最小 HTTP API，降低 Windows/Linux/macOS 兼容成本。
2. **snapshot 而非多接口聚合**：本阶段先提供 `/v1/console/snapshot`，让前端在一个请求内拿到已冻结信息架构，避免 premature API fan-out。
3. **API 优先、mock 回退**：前端 runtime data adapter 先请求 API；失败后保留可运营界面，但必须让用户知道当前是样例数据。
4. **安全红线内置测试**：任何 `raw_payload` 泄露、dry-run 伪装 `verified_loaded` 都作为阻断失败。

## 批次

### Batch 1：契约与后端快照

- 新增 `contracts/console-api-contract.md`。
- 新增 `agentops.api.console_snapshot`。
- 新增 Python contract tests。

### Batch 2：HTTP API 入口

- 新增 `agentops.api.server`。
- `/v1/health`、`/v1/console/snapshot`、404 JSON、CORS。
- 支持 `--host`、`--port`。

### Batch 3：Vue2 runtime data adapter

- 新增 `src/data/agentOpsApiClient.js`。
- `App.js` 支持 loading/source/degraded 状态。
- 保持中文界面和 mock fallback。

### Batch 4：验证、对抗评审与 close

- 跑 Python/前端测试与 build。
- 对抗评审无 P0/P1 后记录开发总结。
- 走 PR、`@codex review`、GitHub checks 和主线合入。

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| 标准库 HTTP 能力不足 | 本阶段只承载 JSON snapshot；生产化接口后续可单独设计 |
| 前端 API 不可用导致空白 | 强制 mock fallback + 中文降级提示 |
| mock 被误认为真实事实 | snapshot/source 明确 `api_snapshot` 或 `mock_fallback` |
| verified_loaded 误表达 | Python 和前端双侧契约测试 |
