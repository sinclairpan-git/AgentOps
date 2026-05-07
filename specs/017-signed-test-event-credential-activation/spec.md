# 017 Signed Test Event Credential Activation

## 背景

016 已让 AgentOps 消费 Agent Store 008 的 `agentops_credential_handoff.v1`，并在 Credential Issue response 中返回 `bootstrap_status=credential_issued` 与 `next_action=send_signature_test_event`。但 `credential_issued` 只代表 ReporterCredential、IngestionToken 和 DeviceKey 已签发，不能证明 Reporter 已经可用，也不能等同于 `verified_loaded` 或 L5。

## 范围

- 定义 `signature_test_event` 作为 Credential Issue 后的运行态激活事件。
- Ingestion 必须校验该事件与已签发 credential 的 `bootstrap_id`、`credential_id`、`token_id`、`device_key_id`、`installation_id`、`device_id` 绑定。
- 有效 signed test event 进入 managed event path 后，AgentOps 将 bootstrap session 推进为内部 `verified`，并记录外部可回显的 `bootstrap_status=signature_verified`。
- 缺签名、token 不匹配、credential 不存在、device key 非 active、身份不匹配、payload 字段缺失或幂等重放都必须有稳定结果。

## 非目标

- 不修改 Agent Store 代码。
- 不修改 Ai_AutoSDLC CLI。
- 不实现真实生产密钥服务、KMS/HSM 或密码学验签。
- 不把 `signature_verified`、CLI dry-run 或 adapter materialized 状态提升为 `verified_loaded`。
- 不让 Agent Store 本地推导 `active`、签发 credential 或生成 DeviceKey。

## 契约测试

- AO17-CCT-004：有效 `signature_test_event` 必须绑定 active credential、token、device key 和 installation/device identity，并推进 bootstrap 到 `signature_verified`。
- AO17-CCT-004-N1：缺 credential 或 token 不匹配必须拒绝，且不推进状态。
- AO17-CCT-004-N2：device key 非 active 或 installation/device 不匹配必须拒绝。
- AO17-CCT-004-N3：同一 idempotency key 重放必须 deduplicated，不重复写事件。
- AO17-CCT-004-N4：payload 缺少 CCT 字段必须返回 `EVENT_PAYLOAD_INVALID`。
