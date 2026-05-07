# 计划：020 Credential Revocation Propagation

1. 扩展 Credential API：新增撤销 schema、撤销服务函数、状态查询 revoked 回显。
2. 扩展 Repository 和 Ingestion：记录撤销状态，并在签名测试事件、已知企业托管事件写入前阻断。
3. 扩展 HTTP/OpenAPI：增加 `POST /v1/bootstrap/credentials/{bootstrap_id}/revoke`。
4. 扩展 Console：凭证联调页展示已撤销数量、撤销摘要和重新签发建议。
5. 扩展契约测试和云端对抗 review guard：覆盖 AO20-CT-001 到 AO20-CT-006。
6. 执行统一验证、AI-SDLC constraints、program validate、truth sync 和 close-check。
