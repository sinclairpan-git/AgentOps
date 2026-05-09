# 研究：AgentOps Runtime Governance Foundation

**工作项**：`031-agentops-runtime-governance-foundation`  
**日期**：2026-05-09  
**阶段**：design / research

## 1. 输入基线

本研究只吸收已更新 PRD 中适合 AgentOps P0 的内容，不扩大到 P1/P2 能力。

| 输入 | 本工作项吸收点 |
|---|---|
| AgentOps PRD 第 16 章 | Runtime Trace 接入、EvidenceSummary/HealthSummary 字段、Policy/Grant Owner、TraceSpan 最小枚举 |
| Agent Runtime PRD | RuntimeRun、TraceSpan、Outbox、Policy Check Client、Runtime Trace Export |
| 顶层 PRD 第 14 章 | 四项目边界、统一跨项目契约总表、Contract Registry / Schema Registry 治理、P0 收紧口径 |
| 既有 001-030 specs | 复用 EventEnvelope、credential、policy、approval、console、audit、summary、production auth 等既有能力 |

## 2. 方案对比

### 2.1 契约治理

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| 只补 OpenAPI，不建 Contract Registry | 快 | Owner、Producer/Consumer、状态和错误码容易继续分散 | 不采用 |
| 在代码中硬编码字段校验 | 实现短 | 文档、测试、跨项目契约不可追踪 | 不采用 |
| Contract Registry + Schema Registry 最小治理 | 对齐 PRD，可驱动 contract tests | 初始工作量略大 | 采用 |

决策：P0 使用轻量 registry 结构，先覆盖 owner、字段、枚举、错误码、contract test id，不做复杂 registry 服务。

### 2.2 Runtime 事件接入

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| 复用旧 `/v1/events` 全量接入 | 兼容既有 Ai_AutoSDLC | RuntimeRun / TraceSpan 语义容易和 SDLC event 混在一起 | 仅保留兼容 |
| 新增 Runtime 专用 ingestion route | 边界清晰，便于 contract test | 需要新 API 和 repository 方法 | 采用 |
| 直接消费 Runtime 数据库 | 查询快 | 破坏项目边界，AgentOps 接管 Runtime 存储 | 不采用 |

决策：执行阶段优先新增 Runtime 专用接入层，底层可以复用现有 EventEnvelope / idempotency / signature 能力。

### 2.3 Run Detail / Trace Timeline 投影

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| Console 直接拼装 raw events | 前端快 | 权限、脱敏、降级语义分散 | 不采用 |
| 后端生成 RunDetailProjection / TraceTimelineProjection | 权限和状态统一，前端稳定 | 后端投影多一层 | 采用 |
| 等完整 Evidence/Health 后再做页面 | 更完整 | 阻塞 P0 最小闭环 | 不采用 |

决策：P0 先做运行事实投影，不等待完整 EvidenceSummary / HealthSummary。

### 2.4 Trace 标准

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| 直接采用 OTel/OpenInference | 生态兼容 | 内部 owner、grant、approval、evidence 字段不足 | P1 exporter |
| 自定义内部 TraceSpan + 保留 exporter 兼容字段 | 贴合四项目契约 | 后续需要映射层 | 采用 |

决策：P0 使用内部 `TraceSpanFact`，保留 trace_id、span_id、parent_span_id、span_kind、token_usage、cost_estimate 等可映射字段。

## 3. 复用现有工程能力

| 现有能力 | 复用方式 |
|---|---|
| `src/agentops/core/envelope.py` | 复用 EventEnvelope 校验理念和字段命名 |
| `src/agentops/core/idempotency.py` | 复用幂等防重思路 |
| `src/agentops/core/signature.py` | 复用签名状态和 credential 校验入口 |
| `src/agentops/api/auth.py` | 复用 AO23 生产鉴权边界 |
| `src/agentops/api/view_models.py` | 扩展 Run Detail / Timeline 投影 |
| `apps/agentops-console/src/views/RunsView.js` | 承接运行详情和 trace timeline |
| `tests/contract/*` | 继续按 AOxx-CT contract-first 模式验证 |

## 4. P0 收紧决策

1. AO31 只覆盖 AO-P0-01 到 AO-P0-04。
2. EvidenceSummary 合成、HealthSummary 回写、Approval Center 完整流转不进入 AO31。
3. Runtime 执行和 Outbox 生产不进入 AO31；AgentOps 只消费上报。
4. Console P1 仅做数据契约承接和安全空态，不做复杂交互重构。
5. 所有用户可见状态必须从 State Registry 输出，不允许页面自造文案。

## 5. 风险与控制

| 风险 | 控制 |
|---|---|
| Runtime 和 AgentOps 字段再次漂移 | Contract Registry + AO31-CT-001 |
| Timeline 乱序或缺 parent 被误判成功 | parent integrity + degraded 状态 |
| 未签名事件进入可信事实 | signature_state 必检，高可信写入拒绝 |
| 前端展示原文泄露 | 后端投影只给 payload_ref/hash/脱敏摘要 |
| AO31 范围膨胀 | Health/Evidence/Approval 完整能力后续单独拆分 |
