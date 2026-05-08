# 开发摘要：023 Production Runtime Boundary

## 交付内容

- 新增 production-mode HTTP auth boundary，默认本地模式保持兼容。
- 新增 `src/agentops/api/auth.py`，消费上游 `X-AgentOps-Principal`、roles、scopes、request_id 和 audit_id。
- 生产模式保护写接口：`POST /v1/events`、credential revoke、credential reissue。
- 生产模式保护敏感读接口：Console snapshot、credential status、Agent Store summary。
- 鉴权失败稳定返回 `UPSTREAM_IDENTITY_REQUIRED` 或 `AGENTOPS_SCOPE_DENIED`，并包含 `request_id`、`audit_id`、`denied_scope`。
- `create_app()` route manifest 声明 production auth boundary。
- 补齐 frontend generation artifacts：`recipe.yaml`、`exceptions.yaml`，并把 generation artifact 集迁移到 AI-SDLC loader 兼容结构。

## 边界声明

- AgentOps 不自建 IAM、JWT/OIDC、统一登录或生产密钥服务。
- 本阶段只消费上游可信身份与 RBAC/scope header。
- 未启用 `require_auth` 时，既有本地联调和契约测试保持兼容。
- 拒绝响应不包含 raw payload、token、device key、credential secret 或原文链接。

## 验证

- `uv run pytest tests/contract/test_ao23_ct_production_runtime_boundary.py -q`：通过，AI-SDLC loader optional test 在项目 uv 环境跳过。
- `uv run pytest tests/contract/test_ao4_ct_console_api.py tests/contract/test_ao18_ct_agent_store_credential_status.py tests/contract/test_ao22_ct_agent_store_summary_http_contract.py -q`：通过。
- `uv run ruff check src tests`：通过。
- `uv run ruff format --check src tests`：通过。
- `uv run ai-sdlc program status`：通过。
- `uv run ai-sdlc program validate`：PASS，保留 `prd_path is empty` 非阻断提示。
- `npm test`（apps/agentops-console）：通过。
- `npm run build`（apps/agentops-console）：通过。

## 后续生产级切片

- 生产数据库/持久化审计。
- 真实 IAM/JWT/OIDC 校验适配器。
- 多租户数据隔离和 ABAC attribute mapping。
- 完整质量评分引擎与生命周期建议。
