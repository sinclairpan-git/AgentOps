# 017 Tasks

- [x] T17-01 定义 signed test event 激活契约。
- [x] T17-02 扩展 EventEnvelope payload 校验。
- [x] T17-03 实现 Ingestion 与 credential/token/device binding 校验。
- [x] T17-04 补充 AO17-CCT-004 contract tests。
- [x] T17-05 更新云端 review 检查信号。
- [x] T17-06 执行本地验证并准备 PR。

## 验收

- `credential_issued` 后只有有效 `signature_test_event` 能推进 `signature_verified`。
- signed test event 必须绑定 `bootstrap_id`、`credential_id`、`token_id`、`device_key_id`、`installation_id`、`device_id`。
- token、device key 或 identity 不匹配时拒绝，且不推进状态。
- 重放同一 `idempotency_key` 不重复写入事件。
- `signature_verified` 不等于 `verified_loaded` 或 L5。
