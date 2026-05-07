# 018 Plan

1. 定义 Agent Store credential status query spec/tasks/summary。
2. 在 Credential API 增加 `get_credential_status` 只读函数。
3. 在 HTTP server 暴露 `GET /v1/bootstrap/credentials/{bootstrap_id}`。
4. 更新 OpenAPI、app assembly 和云端 adversarial review guard。
5. 补充 AO18 contract tests 并执行统一验证。
