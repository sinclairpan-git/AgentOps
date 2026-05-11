# 功能规格：Quality Scorer External Intake Readback

**功能编号**：`047-quality-scorer-external-intake-readback`  
**创建日期**：2026-05-11  
**状态**：已冻结  
**输入**：承接 046 已完成的 external scorer intake HTTP route，为外部 scorer retry/replay/排障提供只读 receipt readback。继续禁止 AgentOps 执行 scorer、读取 raw evidence/prompt/diff/terminal、自动 rollout、自动 Store 写回或发送通知。参考：`specs/045-quality-scorer-external-intake/spec.md`、`specs/046-quality-scorer-external-intake-http/spec.md`。

**范围**：新增 `GET /v1/quality/scorers/external-intake` 只读查询，按 `agent_id`、`version`、`idempotency_key` 返回已有 `quality_scorer_external_intake.v1` receipt。HTTP readback 必须要求完整 agent/version scope，避免 key-only 跨 scope 暴露。

## 用户场景与测试

### 用户故事 1 - 外部 scorer 查询已接收 receipt（优先级：P1）

作为外部 scorer 集成方，我希望在 retry 或 webhook 超时后通过 HTTP 查询某个 `idempotency_key` 的接收结果，以便确认 AgentOps 是否已经接受或去重，而不是重复提交 payload。

**独立测试**：先通过 046 POST 写入 receipt，再通过 047 GET 按完整 `agent_id/version/idempotency_key` 查询，断言返回同一 receipt 且不新增 execution evidence。

### 用户故事 2 - 查询边界必须只读且最小审计（优先级：P1）

作为治理负责人，我希望 receipt readback 拒绝缺少 query scope、缺少生产权限或不存在的 receipt，并写入不含 idempotency payload/raw body 的最小 audit。

**独立测试**：缺少 `agent_id/version/idempotency_key` 返回 `400`；不存在返回 `404`；生产模式缺 scope 返回 `403`；audit 不包含 raw marker，且任何失败都不创建 execution evidence。

## 边界情况

- `idempotency_key`、`agent_id`、`version` 均必须通过 query string 提供。
- key-only 或 partial-scope readback 必须拒绝，不调用 repository 的 ambiguous lookup 路径。
- 查询返回的 receipt 必须保持 summary-only，不返回 external_result、raw payload、prompt、diff、terminal、URL 或 secret。
- readback 只读，不执行 scorer、不重放 external result、不写 Store、不发通知、不创建新的 execution evidence。

## 需求

### 功能需求

- **FR-001**：系统必须登记 `quality_scorer_external_intake_readback.v1` contract，声明 route、required query、状态码/error code 和 AO47 contract tests。
- **FR-002**：HTTP readback 必须通过 `agent_id`、`version`、`idempotency_key` 查询已有 receipt；缺任一字段返回 `QUALITY_SCORER_INTAKE_RECEIPT_QUERY_REQUIRED`。
- **FR-003**：未找到 receipt 必须返回 `QUALITY_SCORER_INTAKE_RECEIPT_NOT_FOUND`，不得伪造空 receipt。
- **FR-004**：生产模式必须要求 `quality.scorer.intake.read` scope，并对 accepted/rejected/denied 写最小 audit record。
- **FR-005**：`create_app()` 必须声明 readback route，方便外部 scorer 和运维工具发现。
- **FR-006**：readback 不得改变 repository 中的 execution evidence 数量，不得触发任何自动动作。

### 关键实体

- **QualityScorerExternalIntakeReadbackRequest**：只读 query envelope，包含 agent/version/idempotency key。
- **QualityScorerExternalIntakeReceipt**：045 已定义的 receipt，readback 原样返回 summary-only 存量 receipt。
- **QualityScorerExternalIntakeReadAudit**：HTTP 只读边界最小 audit，包含 action/outcome/resource/error/scope，不包含 body 或 raw marker。

## 成功标准

- **SC-001**：AO47 contract tests 覆盖 registry/app route、successful readback、query-required、not-found、production scope denial 和 no-body/no-raw audit。
- **SC-002**：AO45/AO46/AO47 定向回归通过，证明 readback 不新增 execution evidence。
- **SC-003**：`uv run ruff check`、`uv run ruff format --check`、`uv run pytest -q`、`uv run ai-sdlc verify constraints` 和 047 close-check 通过。
