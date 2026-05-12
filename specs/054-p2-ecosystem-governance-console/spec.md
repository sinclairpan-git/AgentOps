# 功能规格：P2 Ecosystem Governance Console

**功能编号**：`054-p2-ecosystem-governance-console`  
**创建日期**：2026-05-12  
**状态**：已冻结  
**输入**：承接 `039-p2-ecosystem-governance` 的 summary-only P2-B 后端投影，把 MCP/A2A Gateway 要求、exporter dry-run、multi-agent handoff evaluation 和 complex risk profile 展示到既有 Connector Status Console。保持只读、summary-only、no-auto-action 边界；不执行 Runtime、不调用 MCP/A2A、不 dispatch exporter、不写 Store、不发送通知、不展示 raw config/payload/URL/secret。

**范围**：扩展 Console snapshot `connectorWorkbench.ecosystemGovernance`、前端 API client validation/legacy fallback 和 Connector Status 页面。页面展示 MCP/A2A 治理、exporter dry-run、handoff 摘要、复杂风险画像和 guardrails。旧后端缺字段时 fallback 使用安全 empty/not_configured 默认值。

## 用户场景与测试

### 用户故事 1 - Ops 审核 MCP/A2A 必须经 Runtime Gateway（优先级：P1）

作为 Ops 审核者，我希望在连接器状态页看到 MCP/A2A 的 gateway、policy check、evidence state 和 direct connection 禁止标记，以便确认外部工具或多 Agent 通信没有绕过 Runtime Gateway。

**独立测试**：Console snapshot 输出 `ecosystemGovernance.mcp_a2a`；前端渲染“生态治理”“Runtime Gateway”“直连禁止”等中文文案。

### 用户故事 2 - 平台 Owner 查看 exporter dry-run 覆盖（优先级：P1）

作为平台 Owner，我希望看到 OTLP/OpenInference/data lake exporter 的配置状态、hash/ref 和 dispatch state，但页面不发起任何网络写入。

**独立测试**：API validation 要求 `external_write_enabled=false`、`network_dispatch_performed=false`；非法自动 dispatch flag 被拒绝。

### 用户故事 3 - 质量负责人查看 handoff 和复杂风险摘要（优先级：P1）

作为质量负责人，我希望连接器状态页展示 handoff count、failed handoff count、risk profile state 和 recommended action，以便人工决定是否进入 ops review。

**独立测试**：repository-backed snapshot 使用 AO39 projection builder 生成 handoff/risk profile；UI 展示“多 Agent 移交”“复杂风险画像”且不出现自动处置按钮。

## 边界情况

- 旧快照没有 ecosystem governance 字段时，fallback 返回 empty/not_configured，不崩溃、不伪造 configured。
- `mcp/a2a` 只展示 endpoint ref 摘要，不展示 http/raw URL、secret、token 或 raw config。
- Exporter 只展示 configuration_hash/ref，不展示原始 config，不执行网络 dispatch。
- Handoff/risk profile 只读取 TraceSpan summary fields，不重跑 handoff、不执行 Runtime。
- UI 不提供 retry、replay、dispatch、Gateway 配置、Store write 或 notification 控件。

## 需求

### 功能需求

- **FR-001**：Console snapshot `connectorWorkbench` 必须包含 `ecosystemGovernance`，字段覆盖 MCP/A2A、exporters、handoffs、risk profiles、summary 和 guardrails。
- **FR-002**：前端 API client 必须校验 ecosystem no-auto-action flags 和 legacy fallback。
- **FR-003**：Connector Status 页面必须展示 ecosystem metrics、MCP/A2A table、exporter dry-run table、handoff table、risk profile table 和 guardrails。
- **FR-004**：UI 文案必须保持中文且只读，不出现自动 dispatch、自动 Runtime action、Store write 或 notification action。
- **FR-005**：054 必须回归 AO4/AO39 和 Console npm contract。

## 成功标准

- **SC-001**：AO4 contract tests 覆盖 Console snapshot ecosystem governance fields 和 no-auto-action guardrails。
- **SC-002**：Console npm contract 覆盖 API validation、legacy fallback、unsafe ecosystem rejection 和页面中文文案。
- **SC-003**：`npm run build` 证明 Connector Status 页面可构建；若浏览器工具不可用，以 Vite build、HTTP source smoke 和 contract 作为替代 smoke 证据。
- **SC-004**：`uv run pytest` 定向套件、`npm test`、ruff、AI-SDLC constraints/truth/close-check 通过。
