# 计划：021 Credential Reissue After Revocation

1. 扩展 Credential API：新增 `agentops_credential_reissue.v1`、reissue service 和状态查询 reissue 回显字段。
2. 扩展 Repository：记录 source credential 的 reissue resolution，支持失败清理和 reissued identity 的 token 边界。
3. 扩展 HTTP/OpenAPI：增加 `POST /v1/bootstrap/credentials/{bootstrap_id}/reissue`。
4. 扩展 Ingestion 契约：新 credential 可走签名测试，旧 token 和随机 token 仍被 revoked source 阻断。
5. 扩展 Console：凭证联调工作台展示 reissued 数量和新 bootstrap/credential id，不展示 token 值。
6. 补 AO21 契约测试并执行统一验证、AI-SDLC constraints、program validate、truth sync 和 close-check。
