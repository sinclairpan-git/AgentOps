# 016 Cross-Project Credential Handoff Consumer

## 背景

Agent Store 008 已合入 `agentops_credential_handoff.v1` producer fixtures 与外部 assertion adapter。AgentOps 当前 Credential Issue 仍是早期本地契约，尚未按共享 appendix 消费 `signed_installation_assertion.v1`、`device_proof.v1`，也缺少 `bootstrap_status` 和 `next_action` 响应字段。

## 范围

- 在 AgentOps 引入与 Agent Store 008 同名的 cross-project fixtures。
- Credential Issue API 必须消费 `agentops_credential_handoff.v1`。
- `installation_assertion` 必须使用 `signed_installation_assertion.v1` 外部字段名。
- `device_proof` 必须使用 `device_proof.v1`，并绑定 `installation_id`、`device_id`、`assertion_hash`。
- AgentOps response 必须包含 `credential_id`、`token_id`、`device_key_id`、`status`、`bootstrap_status`、`installation_id`、`device_id`、`expires_at`、`next_action`。
- 同一 idempotency key 与同一身份必须幂等返回；同一 idempotency key 搭配不同身份必须稳定冲突。

## 非目标

- 不写 Agent Store 的 agent/version/package/installation/device binding 注册事实。
- 不生成 Ai_AutoSDLC device proof。
- 不实现真实 KMS、HSM 或生产签名验签系统。
- 不把 credential issued 或 dry-run 状态提升为 `verified_loaded` 或 L5。

## 契约测试

- AO16-CCT-001：AgentOps 接受 Agent Store 008 的 `signed_installation_assertion.v1` fixture，无需测试内字段适配。
- AO16-CCT-002：device proof 必须绑定 installation、device 和 assertion_hash。
- AO16-CCT-003：AgentOps 作为 credential response producer 输出 appendix 要求的 echo 字段。
- AO16-CCT-006：未知 major schema version 必须返回 explainable unsupported-schema 错误。
