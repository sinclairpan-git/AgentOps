# 016 Plan

1. 引入 Agent Store 008 的 cross-project fixtures，作为 AgentOps consumer contract truth。
2. 更新 Credential Issue validator，支持 `agentops_credential_handoff.v1`、`signed_installation_assertion.v1` 和 `device_proof.v1`。
3. 移除 assertion/device proof algorithm 必须相等的旧约束，保留各自 algorithm、canonicalization、key_id、nonce、TTL、revocation 和身份绑定校验。
4. 补齐 credential response echo 字段和 idempotency conflict 语义。
5. 更新 OpenAPI、契约测试、工程 review 规则和执行日志。
