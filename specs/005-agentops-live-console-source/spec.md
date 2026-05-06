# 功能规格：AgentOps Console 运行事实数据源

**功能编号**：`005-agentops-live-console-source`  
**日期**：2026-05-06  
**需求类型**：`new_requirement`  
**上游基线**：顶层 PRD `agent-platform-baseline-2026-05-v1.4.2`、AgentOps 项目 PRD、`004-agentops-console-api-snapshot`

## 1. 目标

本阶段把 AgentOps Console 从“可连接后端快照 API”推进到“可由 AgentOps 可执行内核运行事实生成快照”。完成后，平台必须能够证明：

1. `/v1/events` 可接收符合 EventEnvelope v1 的本地开发事件批次。
2. `/v1/console/snapshot` 可从 AgentOps 仓库事实生成运行记录、证据摘要、质量信号、风险和连接器状态。
3. 前端仍只展示脱敏摘要、哈希和状态，不暴露 `raw_payload`。
4. `verified_loaded` 仍必须依赖机器可验证证明；仓库可用、CLI 预演或 AGENTS.md 均不得被表达为治理激活成功。

## 2. 范围

- 新增本地开发用事件接入 HTTP 入口。
- 扩展 Console snapshot builder，使其支持 repository-backed 模式。
- 维持 004 的九页信息架构、中文状态文案、mock fallback 和 CORS 白名单。
- 增加契约测试，覆盖事件上报后快照可见、空仓库快照、原文安全红线和 adapter truth 红线。

## 3. 非目标

- 不引入生产 PostgreSQL、Redis、队列、FastAPI/Flask/Uvicorn。
- 不实现统一登录、生产 IAM、ABAC/RBAC、多租户权限后端。
- 不实现真实 Evidence Vault 原文查询。
- 不把 `/v1/console/snapshot` 拆成生产多接口聚合方案。

## 4. 用户故事

### US-001：管理员查看真实上报事实

作为 AgentOps 管理员，我希望事件上报后刷新控制台即可看到运行记录和证据摘要，以便确认 Console 不是只展示静态样例。

### US-002：安全负责人识别降级事实

作为安全/IAM 负责人，我希望缺失 L5 核心事件、policy_state_unknown 或 adapter 未验证时显示为降级/阻断，而不是误报健康。

### US-003：AI-SDLC 维护者验证接入闭环

作为 Ai_AutoSDLC 维护者，我希望通过本地事件批次上报验证 Ingestion -> Repository -> Snapshot -> Console 的最小闭环。

## 5. 功能需求

- **FR-001**：系统必须提供 `POST /v1/events`，请求体为 `{ "events": [...] }`。
- **FR-002**：`POST /v1/events` 必须复用既有 EventEnvelope v1 校验、签名语义、幂等语义和错误码。
- **FR-003**：`/v1/console/snapshot` 必须在 repository-backed 模式下从仓库事实构建数据，不读取或透出 raw payload。
- **FR-004**：快照必须包含 `source_detail.mode=repository_backed`，让前端能用中文区分“后端事实快照”与普通样例快照。
- **FR-005**：空仓库必须返回结构完整的安全空状态，不允许返回非法 schema 或导致前端崩溃。
- **FR-006**：L5 完整事件链必须显示为健康；缺失核心事件必须显示降级并给出缺失证据摘要。
- **FR-007**：前端必须继续拒绝未知状态、非法 shape、`raw_payload` 和缺少机器证明的 `verified_loaded`。

## 6. 验收标准

| 编号 | 验收项 |
|---|---|
| AO5-CT-001 | 完整 L5 事件写入仓库后，repository-backed snapshot 展示 1 条健康运行和 1 条证据摘要 |
| AO5-CT-002 | HTTP `POST /v1/events` 后，`GET /v1/console/snapshot` 可看到新运行 |
| AO5-CT-003 | 空仓库 snapshot schema 完整，前端 validator 接受 `empty` 状态 |
| AO5-CT-004 | snapshot 任意层级不得包含 `raw_payload` |
| AO5-CT-005 | adapter proof 仍为 materialized/unverified，不因仓库可用而变成 verified_loaded |
| AO5-CT-006 | `POST /v1/events` 对非法 JSON、缺 `events`、重复幂等键、mixed batch 和 CORS 均返回可解释 JSON |
| AO5-CT-007 | API assembly truth 必须声明实际 HTTP 接入口 `POST /v1/events` |
