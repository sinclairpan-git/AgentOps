# 规格：Credential Revocation Propagation

**功能编号**：`020-credential-revocation-propagation`

## 背景

016 到 019 已经形成 Agent Store producer、AgentOps credential issue、签名测试事件、状态查询和控制台凭证联调工作台。下一步需要补齐撤销传播：当 AgentOps 事实源确认 credential revoked 后，签名测试事件和企业托管事件都不能继续凭同一 credential 或同一已知身份接入。

## 目标

- 增加 `agentops_credential_revocation.v1` 撤销 API，AgentOps 作为唯一事实源写入 revoked 状态。
- `GET /v1/bootstrap/credentials/{bootstrap_id}` 在 revoked 后返回 `bootstrap_status=revoked`、`credential_status=revoked`、`next_action=reissue_credential` 和撤销摘要。
- 已撤销凭证必须阻断后续签名测试事件和已知企业托管事件，稳定返回 `EVENT_CREDENTIAL_REVOKED`。
- Console 凭证联调工作台展示“已撤销”和“重新签发凭证”，但仍保持 Agent Store display-only 边界，不推导 active。

## 非目标

- 不修改 Agent Store 仓库。
- 不签发新 credential、ingestion token 或 device key。
- 不实现 Ai_AutoSDLC device proof 生成。
- 不把 revoked、credential issued 或 signature verified 提升为 `verified_loaded` 或 L5。

## 验收契约

- AO20-CT-001：撤销 API 必须更新 AgentOps-owned 状态和状态查询回显。
- AO20-CT-002：已撤销 credential 的签名测试事件必须被拒绝。
- AO20-CT-003：已知企业托管事件命中 revoked credential 或 identity 时必须被拒绝。
- AO20-CT-004：未知撤销 schema version 必须稳定返回 unsupported schema 错误。
- AO20-CT-005：HTTP revoke route 必须返回 JSON、CORS 和 `reissue_credential`。
- AO20-CT-006：不存在的 bootstrap 撤销必须返回稳定 not found 错误。

## 落地结果

本阶段完成后，AgentOps 可以向 Agent Store 009 提供撤销事实回显，并保证已撤销凭证不会继续通过签名测试或企业事件接入链路。
