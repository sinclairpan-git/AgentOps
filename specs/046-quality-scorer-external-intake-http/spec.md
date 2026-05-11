# 功能规格：Quality Scorer External Intake HTTP

**功能编号**：`046-quality-scorer-external-intake-http`  
**创建日期**：2026-05-11  
**状态**：已冻结  
**输入**：承接 045 已完成的 external scorer summary intake core/API，把受管外部 scorer 结果接入暴露为 HTTP/webhook 边界。继续禁止 AgentOps 执行 scorer、读取 raw evidence/prompt/diff/terminal、自动 rollout、自动 Store 写回或发送通知。参考：`specs/045-quality-scorer-external-intake/spec.md`、`specs/044-quality-scorer-execution-evidence/spec.md`、`src/agentops/api/server.py`。

**范围**：新增 `POST /v1/quality/scorers/external-intake` 标准库 HTTP route、route contract registry、生产模式 scope/audit 边界和 contract tests。该 route 只解析 HTTP 请求、校验基础 envelope、调用 045 core intake，并返回 summary-only receipt。

## 用户场景与测试

### 用户故事 1 - 外部 scorer 通过 HTTP 上报受管摘要结果（优先级：P1）

作为 AgentOps 管理员，我希望外部受管 scorer 可以通过稳定 HTTP endpoint 上报 signed/verified summary result，以便无需直接调用 Python API 也能进入 Quality Center execution evidence。

**独立测试**：启动本地 HTTP handler，发送 JSON payload 与签名/header，断言返回 `202` 和 `quality_scorer_external_intake.v1` receipt，同时 repository 写入一条 `quality_scorer_execution.v1`。

### 用户故事 2 - HTTP 边界拒绝缺少 envelope、权限或不安全输入（优先级：P1）

作为治理负责人，我希望 HTTP route 拒绝缺少 `agent_id/version/external_result`、生产模式缺 scope、raw marker 或签名失败的请求，并写入不含请求体的最小 audit。

**独立测试**：验证 invalid JSON/missing fields/raw input/unauthorized scope 均不能写 execution evidence；audit record 只包含 action/outcome/resource/error，不包含 raw body。

## 边界情况

- `agent_id`、`version` 和 `external_result` 必须来自 JSON body；`idempotency_key` 可来自 body 或 `Idempotency-Key` header。
- `signature` 可来自 body 或 `X-AgentOps-Scorer-Signature` header；`source_trust` 可来自 body 或 `X-AgentOps-Source-Trust` header。
- 生产模式必须具备 `quality.scorer.intake.write` scope。
- route 必须复用 045 core intake 的幂等、签名、source trust、sample boundary、raw/secret rejection 和 non-finite threshold 行为。
- HTTP audit 不得记录 request body、raw payload、prompt、URL、token、credential secret 或 device key。

## 需求

### 功能需求

- **FR-001**：系统必须登记 `quality_scorer_external_intake_http.v1` contract，声明 route、required fields、状态码/error code 和 AO46 contract tests。
- **FR-002**：HTTP route 必须接受 body/header 混合的 idempotency 与 signature metadata，并调用 045 `ingest_quality_scorer_external_execution`。
- **FR-003**：accepted 或 deduplicated receipt 必须返回 `202 Accepted`；输入缺失返回 `400`；签名失败返回 `401`；source trust/生产 scope 拒绝返回 `403`；幂等冲突返回 `409`。
- **FR-004**：生产模式 route 必须要求 `quality.scorer.intake.write` scope，并对 accepted/rejected/denied 写最小 audit record。
- **FR-005**：HTTP route 不得绕过 045 的 summary-only/no-auto-action guardrails，不得执行 scorer、不写 Store、不发通知。
- **FR-006**：`create_app()` 必须声明新 route，方便 Console/Store/外部 scorer 集成发现。

### 关键实体

- **QualityScorerExternalIntakeHttpRequest**：HTTP request envelope，包含 agent/version、source trust、signature/idempotency metadata、scorer ref 和 external summary result。
- **QualityScorerExternalIntakeReceipt**：045 已定义的 `quality_scorer_external_intake.v1` receipt，HTTP route 直接返回该 summary-only receipt。
- **QualityScorerExternalIntakeAudit**：HTTP 边界最小 audit，包含 action/outcome/resource/error/scope，不包含 body。

## 成功标准

- **SC-001**：AO46 contract tests 覆盖 registry、accepted HTTP intake、header idempotency/signature fallback、missing fields/raw rejection、生产 scope denial 与 no-body audit。
- **SC-002**：AO45/AO46 定向回归通过，并证明 HTTP route 写入的 execution evidence 可被 045/Quality Center 继续消费。
- **SC-003**：`uv run ruff check`、`uv run ruff format --check`、`uv run pytest -q` 和 `uv run ai-sdlc verify constraints` 无 BLOCKER。
