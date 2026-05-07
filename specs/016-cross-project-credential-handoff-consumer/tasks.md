# 016 Tasks

- [x] T16-01 定义 AgentOps cross-project consumer 契约。
- [x] T16-02 引入共享 fixtures。
- [x] T16-03 更新 Credential Issue API validator 与 response。
- [x] T16-04 补充 CCT-001/CCT-002/CCT-003/CCT-006 测试。
- [x] T16-05 更新 OpenAPI 和云端 review 检查。
- [x] T16-06 执行本地验证并准备 PR。

## 验收

- AgentOps 可直接消费 `agentops_credential_handoff.v1` fixture。
- device proof 与 assertion 的 installation/device/assertion_hash 不一致时拒绝。
- assertion/device proof 使用不同 algorithm 时不再被误拒。
- response 包含 `bootstrap_status=credential_issued` 和 `next_action=send_signature_test_event`。
- unknown major schema version 返回 unsupported-schema 错误。
