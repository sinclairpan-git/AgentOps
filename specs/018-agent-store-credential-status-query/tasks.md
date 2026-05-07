# 018 Tasks

- [x] T18-01 定义 Agent Store credential status query 契约。
- [x] T18-02 实现只读 `get_credential_status`。
- [x] T18-03 暴露 HTTP GET route。
- [x] T18-04 更新 OpenAPI、app assembly 和 adversarial review guard。
- [x] T18-05 补充 AO18 contract tests。
- [x] T18-06 执行统一验证并准备 PR。

## 验收

- Agent Store 可查询 AgentOps 写事实，不需要本地推导状态。
- `credential_issued` 和 `signature_verified` 有稳定响应。
- 响应明确 Store 只能 display-only，不得签发 credential 或推导 active。
- 响应不包含 token 明文、私钥、raw payload、download URL。
- 查询成功不构成 `verified_loaded` 或 L5。
