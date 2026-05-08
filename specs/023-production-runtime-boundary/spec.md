# 规格：Production Runtime Boundary

**功能编号**：`023-production-runtime-boundary`
**日期**：2026-05-08
**状态**：执行中
**PRD 参考**：`/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md`

## 背景

当前 001-022 已完成 AgentOps 的可信运行、策略/审批/Evidence Vault、Console、Agent Store credential 与 summary 契约闭环。距离生产级平台仍有一类基础缺口：HTTP API 仍以本地联调为默认边界，尚不能在生产模式下消费上游 IAM/RBAC 属性并稳定拒绝未授权请求；同时 `ai-sdlc program status` 会因 `governance/frontend/generation/recipe.yaml` 缺失而崩溃，影响治理面可运行性。

本阶段作为生产级 AgentOps 的第一块增量，先建立“生产运行边界”：生产模式下所有写接口和敏感读接口必须由上游身份/角色/权限证明支撑，拒绝响应必须带 request/audit 线索，且治理命令不能因前端生成 recipe 缺失而中断。

## 目标

- HTTP server 支持显式 `require_auth`/生产模式，由上游网关或 IAM 传入 principal、roles、scopes、request_id、audit_id。
- 生产模式下保护写接口：event ingestion、credential revoke、credential reissue。
- 生产模式下保护敏感读接口：console snapshot、credential status、Agent Store summary。
- 未携带身份返回 `UPSTREAM_IDENTITY_REQUIRED`；身份存在但权限不足返回 `AGENTOPS_SCOPE_DENIED`。
- 所有鉴权拒绝响应必须包含 `request_id`、`audit_id` 和 `denied_scope`，不得回显 token、raw payload、device key 或 credential secret。
- CORS preflight 明确允许上游身份 header 名称，但仍不使用 `*` origin。
- 补齐 `governance/frontend/generation/recipe.yaml` 与 `exceptions.yaml`，使 `ai-sdlc program status` 可执行。

## 非目标

- 不自建统一登录、会话、JWT 校验、OIDC 或 KMS/HSM。
- 不实现生产数据库、多租户数据隔离或持久化审计表。
- 不改变 local/dev 默认兼容性；未启用 `require_auth` 时既有本地契约继续可运行。
- 不让 AgentOps 写 Agent Store 注册、上架、详情或推荐事实。

## 验收契约

- AO23-CT-001：`/v1/health` 在生产模式下仍可匿名读取，便于平台存活探针使用。
- AO23-CT-002：生产模式下未携带上游 principal 调用 `POST /v1/events` 返回 401、`UPSTREAM_IDENTITY_REQUIRED`、`request_id`、`audit_id` 和 `denied_scope=event.ingest`。
- AO23-CT-003：生产模式下 viewer 身份调用 `POST /v1/events` 返回 403、`AGENTOPS_SCOPE_DENIED`，不得写入事件。
- AO23-CT-004：生产模式下 `agentops-ingestor` 或 `event.ingest` scope 可写入事件。
- AO23-CT-005：生产模式下 Agent Store summary 只允许 `agent-store-consumer`、`agentops-viewer`、`agentops-operator` 或 `agentops-admin` 读取。
- AO23-CT-006：鉴权拒绝响应和 CORS header 不暴露 raw payload、token、device key 或 credential secret。
- AO23-CT-007：`create_app()` route manifest 声明 production auth boundary。
- AO23-CT-008：`ai-sdlc program status` 不再因缺失 frontend generation artifacts 崩溃。

## 成功标准

- 本阶段新增契约测试通过，且不破坏 AO4/AO18/AO22 既有本地兼容契约。
- `uv run pytest tests -q` 通过。
- `uv run ruff check src tests` 与 `uv run ruff format --check src tests` 通过。
- `uv run ai-sdlc program status`、`uv run ai-sdlc program validate`、`uv run ai-sdlc run --dry-run` 通过。
