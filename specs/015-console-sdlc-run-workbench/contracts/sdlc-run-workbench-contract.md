# Ai_AutoSDLC Run Workbench Contract

## AO15-CT-001 sdlcRunWorkbench 数据域

`GET /v1/console/snapshot` 返回的 `consoleData.sdlcRunWorkbench` 必须只包含：

- `summary`
- `reporter`
- `outbox`
- `eligibility`
- `guardrails`

`reporter`、`outbox` 和 `eligibility` 三类行必须与 `consoleData.sdlcRuns[]` 一一绑定。

## AO15-CT-002 Reporter 摘要

Reporter 行必须包含运行标识、命令、Reporter 状态、接入模式、凭证状态、签名状态、身份可信度、治理状态、证明来源、下一步动作和安全说明。`active` 必须由 machine-verifiable proof 支撑。

## AO15-CT-003 Outbox 摘要

Outbox 行必须包含投递状态、序列状态、待投递事件、最旧待办年龄、回放边界、证据影响、审计编号和安全说明。Console 不得执行 Outbox Replay 或事件重放。

## AO15-CT-004 L5 条件摘要

Eligibility 行必须包含证据等级、L5 结果、failed_conditions、policy_state_known、governance_loaded、verification_fresh、outbox_delivered、下一步动作和安全说明。缺失条件不得展示为 healthy。

## AO15-CT-005 verified_loaded 红线

`verified_loaded` 只能由非待采集、非 AGENTS.md、非 CLI 预演的机器证明支撑。否则 Reporter、Credential、source_signed、governance_loaded 和 Outbox delivered 都必须保持未验证或 pending。

## AO15-CT-006 前端校验

前端 validator 必须拒绝 malformed `sdlcRunWorkbench`、危险字段、缺失绑定行、伪 Reporter active、伪 Outbox delivered 和伪 L5 结果。
