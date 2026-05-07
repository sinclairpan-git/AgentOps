# 规格：Console Credential Handoff Workbench

**功能编号**：`019-console-credential-handoff-workbench`

## 背景

016 到 018 已经打通 Agent Store producer fixtures、AgentOps credential issue、签名测试事件和 Agent Store 只读状态查询。Agent Store 009 将消费 AgentOps 的 `agentops_credential_status.v1` 回显，但 AgentOps 控制台目前还缺少面向联调、运维和审计人员的可视化工作台。

## 目标

- 在 Console 增加“凭证联调”页面，中文展示 bootstrap、credential、签名测试事件和 Agent Store 消费边界。
- 后端 `agentops.console.snapshot.v1` 增加 `credentialHandoff` 只读视图模型。
- 前端 validator 必须拒绝危险快照：不得包含 token 值、私钥、原始载荷、下载链接或 raw URL。
- 页面必须明确 `signature_verified` 只表示签名测试事件通过，不构成 `verified_loaded` 或 L5。

## 非目标

- 不修改 Agent Store 仓库。
- 不签发额外 credential、token 或 device key。
- 不让 Agent Store 或 Console 本地推导 active。
- 不展示 assertion/device proof 的 signature 原文、token 值、私钥或原始 payload。

## 验收契约

- AO19-CT-001：Console snapshot 必须声明 `credential-handoff` 路由和 `credentialHandoff` 工作台形状。
- AO19-CT-002：credential issued 状态必须展示 AgentOps fact owner、display-only 边界和 Agent Store 禁止动作。
- AO19-CT-003：signature verified 必须切换为 `display_activation_result`，但 `verified_loaded` 和 `l5_status` 仍为 `not_asserted`。
- AO19-CT-004：工作台不得暴露 `token_value`、`private_key`、`raw_payload`、`download_url`、`raw_url` 或 `signature`。

## 落地结果

本阶段完成后，AgentOps 可以在控制台里解释 Agent Store 009 将要消费的 AgentOps 事实回显，降低跨项目联调时“凭证已签发”和“治理已激活”被混淆的风险。
