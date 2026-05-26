# 功能规格：SDLC v0.7.18 Executable Task Runtime Bridge

**功能编号**：`056-sdlc-v0-7-18-executable-task-runtime-bridge`  
**创建日期**：2026-05-25  
**状态**：待实现  
**输入**：Ai_AutoSDLC v0.7.18 release notes、`Ai_AutoSDLC_框架改造_PRD.md` 2026-05-25 更新、`specs/034-runtime-outbox-sdlc-trace-bridge`、`specs/015-console-sdlc-run-workbench`。

## 背景

Ai_AutoSDLC v0.7.18 已将 IDE adapter verification 降级为诊断能力：`verified_loaded` 不再是普通用户主路径、代码修改授权或 AgentOps L5 的主门禁。新的主路径是 executable task -> task guard -> signed runtime facts -> AgentOps outbox receipt / Trace / Evidence / Policy / freshness。

AgentOps 当前已具备 `/v1/runtime/events`、`runtime_outbox_receipt.v1` 和 `sdlc_trace_event.v1` 的基础接收能力，但 Console 和 L5 相关投影仍以 SDLC adapter proof / `verified_loaded` 为主要解释轴。本工作项将 AgentOps 升级为消费 Ai_AutoSDLC v0.7.18 的 executable-task-aware 运行事实。

## 用户故事与验收场景

### 用户故事 1 - 接收 SDLC executable task 运行事实（P0）

作为 AgentOps 管理员，我希望 SDLC 上报的运行事实能绑定到明确的 executable task，以便 Console 和 EvidenceSummary 能解释“本次代码修改对应哪个可执行任务”，而不是只看 adapter 是否加载。

**验收场景**：

1. Given Ai_AutoSDLC 上报 `executable_task_prepared`，When AgentOps 接收 runtime batch，Then 返回 `runtime_outbox_receipt.v1`，并将 task guard 输入写入 summary-only Trace / Evidence 输入。
2. Given Ai_AutoSDLC 上报 `code_change_guard_result=blocked`，When Console 展示 SDLC run，Then 显示阻断原因和候选修复，不显示 run ready 或 L5 candidate。
3. Given batch 缺少 `executable_task_id` 但包含代码修改事件，When AgentOps 计算 evidence readiness，Then 标记 `task_linkage_missing`。

### 用户故事 2 - `verified_loaded` 仅作为诊断（P0）

作为平台 Owner，我希望 `verified_loaded` 不再决定 SDLC run 是否 ready 或 L5，以免 IDE adapter 诊断状态被误当作交付治理证明。

**验收场景**：

1. Given 事件包含 `adapter_ingress_state=verified_loaded` 但没有 executable task linkage，When AgentOps 构建 EvidenceSummary，Then 不进入 actual L5。
2. Given adapter diagnostic 为 `materialized` 或 `unsupported`，但 executable task、签名事件链、outbox receipt、policy 和 evidence 都完整，When AgentOps 计算 readiness，Then adapter diagnostic 不单独阻断普通证据接入。
3. Given Console `sdlcRunWorkbench` 展示 adapter diagnostic，Then 该字段只出现在诊断区，不作为主动作或主状态。

### 用户故事 3 - Console 从 adapter proof workbench 升级为 task / receipt / evidence workbench（P0）

作为 SDLC 负责人，我希望 Console 按任务绑定、上报回执、证据链和诊断分区展示，以便快速判断下一步是修 tasks、重试 outbox、补 evidence，还是排查 adapter。

**验收场景**：

1. Given `runtime_outbox_receipt.v1` 包含 accepted/deduplicated/stale/rejected/dlq 计数，When Console 展示 outbox 区，Then 显示 summary-only receipt 状态和 audit_id。
2. Given receipt delivered 但 task guard blocked，When Console 展示 readiness，Then 不显示 L5 ready。
3. Given stale 或 rejected item result，When Console 展示 diagnostics，Then 只显示 error_code/state/retryable，不暴露 raw payload。

## 功能需求

- **FR-001**：AgentOps 必须登记并接收 `executable_task_prepared.v1` 和 `code_change_guard_result.v1` payload，或在 `sdlc_trace_event.v1` 中稳定区分这两类 SDLC event type。
- **FR-002**：涉及代码修改、验证、artifact 或 L5 eligibility 的 SDLC 事件必须能携带 `workitem`、`executable_task_id`、`task_guard_state`。
- **FR-003**：`code_change_guard_result=blocked` 必须阻断 AgentOps readiness / actual L5，不得仅作为普通诊断。
- **FR-004**：`adapter_ingress_state`、`adapter_diagnostic_state`、`verified_loaded` 只能作为诊断字段，不得单独推出 L5、Reporter active、Outbox delivered 或 run ready。
- **FR-005**：Console `sdlcRunWorkbench` 必须重构为 `taskGuard`、`outboxReceipts`、`evidenceReadiness`、`adapterDiagnostics`、`guardrails`。
- **FR-006**：Outbox delivered 必须来自 `runtime_outbox_receipt.v1` 或等价持久 receipt，不得由 dry-run、AGENTS.md、adapter diagnostic 或 mock proof 推导。
- **FR-007**：AgentOps Store summary / Console summary 只能回显 SDLC receipt 和 evidence 摘要，不展示 raw payload、diff、patch、PR 原文或下载链接。
- **FR-008**：AgentOps 必须支持 Ops-direct producer identity，不要求所有 Ai_AutoSDLC enterprise events 都带 Agent Store `installation_id`；但不得伪造 Store 安装事实。

## 非目标

- 不实现 Ai_AutoSDLC producer。
- 不新增 Console replay 按钮。
- 不让 AgentOps 执行或调度 SDLC。
- 不把 adapter diagnostic 删除；只降级为诊断面。
- 不改变 Agent Store 的分发/安装职责。

## 成功标准

- **SC-001**：新增 contract tests 覆盖 executable task present / missing / malformed / guard blocked。
- **SC-002**：`verified_loaded` 单独存在时不能推出 actual L5、Reporter active 或 Outbox delivered。
- **SC-003**：SDLC v0.7.18 sample batch 经 `/v1/runtime/events` 接收后，Console 可重建 task guard、outbox receipt 和 evidence readiness。
- **SC-004**：AO31/AO34/AO15 回归通过，证明 runtime ingestion、SDLC bridge 和 Console 安全边界未退化。
- **SC-005**：`python -m ai_sdlc run --dry-run`、`npm test`、`npm run build`、相关 `uv run pytest` 均通过。
