# 功能规格：P2 Ecosystem Governance

**功能编号**：`039-p2-ecosystem-governance`  
**创建日期**：2026-05-10  
**状态**：草案  
**输入**：承接 `specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md` 中 P2-B：`AO-P2-03` MCP / A2A 治理、`AO-P2-06` 多 exporter 生态、`AO-P2-08` 多 Agent handoff 评测、`AO-P2-09` 复杂风险画像。依赖 032 Evidence/Health、034 Outbox/DLQ、037 Operations、038 Replay/Simulation/Optimizer。

**范围**：本工作项第一批只实现 AgentOps 本体的 P2-B summary-only ecosystem governance contracts 与后端投影函数；不做真实 MCP/A2A Gateway、不调用外部 exporter、不调度 Agent handoff、不做 Console 页面。

## 用户场景与测试

### 用户故事 1 - MCP/A2A 外部连接必须经治理投影（优先级：P1）

作为 Ops 审核者，我希望看到 MCP/A2A endpoint 的 gateway、policy check、evidence state 和 audit id，以便外部工具或多 Agent 通信不能绕过 Runtime Gateway。

**独立测试**：构建 `mcp_a2a_governance_projection.v1`，验证 `runtime_gateway_required=true`、`direct_connection_allowed=false`、不执行 Runtime。

### 用户故事 2 - 多 exporter 生态只做 dry-run 汇总（优先级：P1）

作为平台 Owner，我希望登记多个 exporter 的配置摘要与 hash/ref，以便评估生态导出准备度，但不让 AgentOps 直接发出网络写入。

**独立测试**：构建 `exporter_ecosystem_projection.v1`，验证多 exporter 只包含 endpoint_ref/configuration_hash/dispatch_state，且 `external_write_enabled=false`。

### 用户故事 3 - 多 Agent handoff 可按 TraceSpan 摘要评测（优先级：P1）

作为质量 Owner，我希望 AgentOps 从 handoff spans 统计 handoff 数量、失败数和候选摘要，以便定位跨 Agent 责任和失败链路，而不是重跑 handoff。

**独立测试**：导入 handoff spans 后构建 `multi_agent_handoff_evaluation.v1`，验证 `handoff_quality_state` 和失败计数。

### 用户故事 4 - 复杂风险画像聚合健康、DLQ 和 handoff 风险（优先级：P1）

作为治理 Owner，我希望看到跨健康、DLQ、handoff 的风险画像，以便人工决定是否进入 ops review 或 disable recommendation。

**独立测试**：构建 `complex_risk_profile.v1`，验证 risk factors、risk_profile_state、recommended_action 和 no automatic action。

## 边界情况

- MCP/A2A projection 只支持 `mcp`、`a2a`；未知协议返回 `MCP_A2A_PROTOCOL_UNSUPPORTED`。
- Exporter ecosystem 只支持登记类型：OTLP、OpenInference、APM、data lake；未知类型返回 `EXPORTER_ECOSYSTEM_UNSUPPORTED`。
- Handoff evaluation 只读取 TraceSpan summary fields，不读取 input/output 原文。
- Complex risk profile 只做 summary projection，不自动 disable、不写回 Store、不触发 Runtime。

## 需求

### 功能需求

- **FR-001**：系统必须登记 P2-B contracts：`mcp_a2a_governance_projection.v1`、`exporter_ecosystem_projection.v1`、`multi_agent_handoff_evaluation.v1`、`complex_risk_profile.v1`。
- **FR-002**：MCP/A2A governance projection 必须输出 protocol、endpoint_ref、subject_agent_id、gateway_state、policy_check_state、evidence_state、summary 和 audit id。
- **FR-003**：Exporter ecosystem projection 必须支持多 exporter 摘要，但 external write 固定 disabled。
- **FR-004**：Multi-agent handoff evaluation 必须从 `span_kind=handoff` 的 TraceSpan summary 统计数量、失败数、质量状态和候选摘要。
- **FR-005**：Complex risk profile 必须组合 HealthSummary、DLQ summary 和 handoff evaluation，输出 risk factors、risk state 和 recommended action。
- **FR-006**：所有 P2-B projection 必须禁止 raw payload、raw config、credential secret、token secret、device key、download/raw URL。
- **FR-007**：039 必须回归 AO32/AO34/AO37/AO38，证明 P2-B 未破坏 P0/P1/P2-A 治理基线。

### 关键实体

- **McpA2aGovernanceProjection**：MCP/A2A 端点治理摘要。
- **ExporterEcosystemProjection**：多 exporter 配置与 dry-run 状态摘要。
- **MultiAgentHandoffEvaluation**：多 Agent handoff 质量评测摘要。
- **ComplexRiskProfile**：跨健康、DLQ、handoff 的风险画像摘要。

## 成功标准

- **SC-001**：`tests/contract/test_ao39_ct_p2_ecosystem_governance.py` 覆盖所有新增 contracts 和核心投影。
- **SC-002**：新增 projection 序列化结果不包含 raw payload、raw config、token secret、credential secret、device key 或 raw/download URL。
- **SC-003**：AO32/AO34/AO37/AO38 定向回归通过。
- **SC-004**：`uv run ai-sdlc verify constraints` 与 039 close-check 通过。
