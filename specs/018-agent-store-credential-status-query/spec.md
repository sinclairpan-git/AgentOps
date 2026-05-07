# 018 Agent Store Credential Status Query

## 背景

016 已提供 AgentOps Credential Issue response，017 已在 signed test event 成功写入后推进 `bootstrap_status=signature_verified`。Agent Store 009 需要消费 AgentOps 的事实回显，但不能靠本地缓存或字段推导 `active`、ReporterCredential、IngestionToken 或 DeviceKey。

## 范围

- 新增 AgentOps 只读 credential/bootstrap status query。
- 查询结果必须由 AgentOps repository 中的 bootstrap session 与 credential facts 组装。
- 查询结果必须包含 `schema_version=agentops_credential_status.v1`、`bootstrap_id`、`bootstrap_status`、`next_action`、`installation_id`、`device_id`、`credential_id`、`token_id`、`device_key_id`。
- 查询结果必须包含 Agent Store consumer boundary，明确 Store 只能展示 `credential_issued`、`signature_verified` 和 `next_action`，不得本地推导 `active` 或签发 credential。
- HTTP 层提供 `GET /v1/bootstrap/credentials/{bootstrap_id}` 只读路由。

## 非目标

- 不修改 Agent Store 代码。
- 不把 query 做成 credential issue 或 refresh 接口。
- 不返回 token 明文、私钥、签名原文、raw payload 或下载链接。
- 不把 `signature_verified`、query 成功、CLI dry-run 或 adapter materialized 状态提升为 `verified_loaded` 或 L5。

## 契约测试

- AO18-CCT-003：`credential_issued` 状态查询返回 AgentOps 事实字段和 `next_action=send_signature_test_event`。
- AO18-CCT-003B：signed test event 成功后，状态查询返回 `signature_verified` 和 `next_action=display_activation_result`。
- AO18-CCT-003N：未知 bootstrap 返回 `CREDENTIAL_STATUS_NOT_FOUND`。
- AO18-CCT-003S：响应不得包含 `token_value`、`private_key`、`raw_payload`、`download_url` 等危险字段。
- AO18-CCT-HTTP：HTTP route 返回 JSON、CORS header 和 404 错误语义。
