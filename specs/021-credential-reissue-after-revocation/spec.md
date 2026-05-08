# 规格：Credential Reissue After Revocation

**功能编号**：`021-credential-reissue-after-revocation`

## 背景

020 已经让 AgentOps 成为 credential revocation 的事实源，并在状态查询中返回 `next_action=reissue_credential`。但 `reissue_credential` 还只是展示建议；下一步需要由 AgentOps 本体完成撤销后的替代 credential 签发，同时继续保证旧 token、旧 credential 和旧 device key 不会被重新激活。

## 目标

- 新增 `agentops_credential_reissue.v1`，通过 `POST /v1/bootstrap/credentials/{bootstrap_id}/reissue` 对已撤销 source credential 重新签发替代 credential。
- 重新签发必须提交新的 `agentops_credential_handoff.v1`，使用新的 `new_bootstrap_id`、assertion nonce 和 device nonce；复用旧 nonce 必须被拒绝且不能留下未签发 session。
- 新 credential 由 AgentOps 生成 ReporterCredential、IngestionToken 和 DeviceKey，状态为 `credential_issued`，下一步仍为 `send_signature_test_event`。
- 撤销 source status 必须记录 `revocation_resolution=reissued`、`reissue_id`、`reissued_bootstrap_id` 和 `reissued_credential_id`。
- 新 credential 可通过签名测试事件推进到 `signature_verified`；旧 token 继续稳定拒绝。
- 同一 installation/device 在 reissue 后只允许使用替代 credential 的 token 接入企业托管事件。
- Console 凭证联调工作台展示 reissued 事实，但仍保持 Agent Store display-only 边界。

## 非目标

- 不修改 Agent Store 仓库。
- 不允许 Agent Store 或 Console 签发 credential、推导 active 或生成 device proof。
- 不把 `reissued`、`credential_issued` 或 `signature_verified` 提升为 `verified_loaded` 或 L5。
- 不处理 `installation` 范围撤销后的同安装重签；该场景需要新的 installation handoff。

## 验收契约

- AO21-CT-001：已撤销 source credential 可重新签发新的 AgentOps-owned credential，并返回 `send_signature_test_event`。
- AO21-CT-001b：替代 credential id 和 token id 必须绑定新的 bootstrap id，不能依赖旧 installation id 复用旧 token。
- AO21-CT-001c：已完成 reissue resolution 的 source credential 只能幂等返回同一个 replacement，不允许创建第二个 replacement。
- AO21-CT-002：新 credential 的签名测试事件可通过，旧 token 仍被拒绝。
- AO21-CT-003：reissue 必须使用新的 bootstrap id。
- AO21-CT-003b：复用旧 nonce 必须稳定返回 replay 错误，且不能留下未签发 bootstrap session。
- AO21-CT-004：非 revoked source credential 不允许 reissue。
- AO21-CT-005：同一 reissue 请求可幂等重试并返回相同结果。
- AO21-CT-006：HTTP reissue route 必须返回 JSON、CORS 和 `agentops_credential_reissue.v1`。
- AO21-CT-007：reissued 后同一 identity 的企业托管事件必须使用替代 credential token。
- AO21-CT-008：多次轮换时，revoked ancestor 必须追踪到最新 active replacement，允许最新 token 并拒绝中间 stale token。

## 落地结果

本阶段完成后，AgentOps 可以把 020 的 `reissue_credential` 下一步动作闭环为实际的替代 credential 签发，同时旧 credential 的撤销事实继续有效，Agent Store 和 Console 仍只消费 AgentOps 回显。
