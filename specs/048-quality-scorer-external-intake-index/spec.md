# 功能规格：Quality Scorer External Intake Index

**功能编号**：`048-quality-scorer-external-intake-index`  
**创建日期**：2026-05-11  
**状态**：已冻结  
**输入**：承接 047 已完成的 external scorer intake receipt readback，为外部 scorer 运维与 Quality Center 排障提供最近 receipt 的只读索引。继续禁止 AgentOps 执行 scorer、读取 raw evidence/prompt/diff/terminal、自动 rollout、自动 Store 写回或发送通知。

**范围**：新增 `GET /v1/quality/scorers/external-intake/index`，按完整 `agent_id`、`version` scope 返回最近 `quality_scorer_external_intake.v1` receipts。该索引不支持 key-only 或跨 agent/version 查询，不回放 payload，不创建 execution evidence。

## 用户场景与测试

### 用户故事 1 - 运维查看最近外部 scorer 上报 receipt（优先级：P1）

作为 AgentOps 运维人员，我希望按 agent/version 查看最近外部 scorer intake receipts，以便排查 webhook 重试、延迟或重复上报，而不需要知道单个 idempotency key。

**独立测试**：先通过 046 POST 写入多条 receipt，再通过 048 index 按 agent/version/limit 查询，断言返回最近 receipt 且不新增 execution evidence。

### 用户故事 2 - 索引边界必须 scope 完整且 summary-only（优先级：P1）

作为治理负责人，我希望 receipt index 拒绝缺少 agent/version、无生产读取权限或非法 limit 的请求，并写入不含 query payload/raw marker 的最小 audit。

**独立测试**：缺少 `agent_id` 或 `version` 返回 `400`；生产模式缺 `quality.scorer.intake.read` 返回 `403`；非法 limit 返回 `400`；audit 不包含 raw URL/token marker。

## 边界情况

- `agent_id` 与 `version` 均必须通过 query string 提供。
- `limit` 可选，默认 25，最大 100；非正数或非整数必须拒绝。
- 返回结果只包含已存 receipt 摘要，不返回 external_result、raw payload、prompt、diff、terminal、URL 或 secret。
- index 只读，不执行 scorer、不重放 external result、不写 Store、不发通知、不创建新的 execution evidence。

## 需求

### 功能需求

- **FR-001**：系统必须登记 `quality_scorer_external_intake_index.v1` contract，声明 route、required query、状态码/error code 和 AO48 contract tests。
- **FR-002**：repository 必须支持按完整 agent/version scope 列出最近 external intake receipts，并按最近 intake sequence 排序。
- **FR-003**：HTTP index 必须要求 `agent_id` 和 `version`；缺任一字段返回 `QUALITY_SCORER_INTAKE_INDEX_QUERY_REQUIRED`。
- **FR-004**：HTTP index 必须校验 `limit`，非法值返回 `QUALITY_SCORER_INTAKE_INDEX_LIMIT_INVALID`。
- **FR-005**：生产模式必须要求 `quality.scorer.intake.read` scope，并对 accepted/rejected/denied 写最小 audit record。
- **FR-006**：`create_app()` 必须声明 index route，方便外部 scorer 运维工具发现。

### 关键实体

- **QualityScorerExternalIntakeIndexRequest**：只读 query envelope，包含 agent/version 和可选 limit。
- **QualityScorerExternalIntakeIndex**：最近 receipt 列表，包含 returned、limit、receipts 和 no-auto-action summary。
- **QualityScorerExternalIntakeReceipt**：045 已定义的 summary-only receipt，index 仅返回存量 receipt。

## 成功标准

- **SC-001**：AO48 contract tests 覆盖 registry/app route、successful scoped index、query-required、production scope denial、invalid limit no-query-payload audit 和 repository scoped listing。
- **SC-002**：AO45/AO46/AO47/AO48 定向回归通过，证明 index 不新增 execution evidence。
- **SC-003**：`uv run ruff check`、`uv run ruff format --check`、`uv run pytest -q`、`uv run ai-sdlc verify constraints` 和 048 close-check 通过。
