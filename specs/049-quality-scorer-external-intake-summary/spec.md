# 功能规格：Quality Scorer External Intake Summary

**功能编号**：`049-quality-scorer-external-intake-summary`  
**创建日期**：2026-05-11  
**状态**：已冻结  
**输入**：承接 048 已完成的 external scorer intake receipt index，为外部 scorer 运维与 Quality Center 提供按 agent/version scope 的 intake health summary。继续禁止 AgentOps 执行 scorer、读取 raw evidence/prompt/diff/terminal、自动 rollout、自动 Store 写回或发送通知。

**范围**：新增 `GET /v1/quality/scorers/external-intake/summary`，按完整 `agent_id`、`version` scope 汇总最近 external intake receipts，返回 receipt_count、health_state、latest receipt 摘要、source trust/intake state counts 和 scorer refs。该 summary 不支持 key-only 或跨 agent/version 查询，不回放 payload，不创建 execution evidence。

## 用户场景与测试

### 用户故事 1 - 运维查看外部 scorer intake 健康摘要（优先级：P1）

作为 AgentOps 运维人员，我希望按 agent/version 查看外部 scorer intake 的最近接收状态、receipt 数量、source trust 分布和最新样本规模，以便快速判断 webhook 接入是否健康，而不需要读取完整 receipt 列表。

**独立测试**：先通过 046 POST 写入多条 receipt，再通过 049 summary 查询，断言返回 `quality_scorer_external_intake_summary.v1`，包含 receiving health、latest receipt、counts 和 scorer refs，且不新增 execution evidence。

### 用户故事 2 - summary 边界必须只读且不泄露 query/raw（优先级：P1）

作为治理负责人，我希望 intake summary 拒绝缺少 agent/version、无生产读取权限或非法 limit 的请求，并写入不含 query payload/raw marker 的最小 audit。

**独立测试**：缺少 `agent_id` 或 `version` 返回 `400`；生产模式缺 `quality.scorer.intake.read` 返回 `403`；非法 limit 返回 `400`；URI-style agent id 可用于 hash lookup，但 response 只回显 `[redacted]`。

## 边界情况

- `agent_id` 与 `version` 均必须通过 query string 提供。
- `limit` 可选，默认 100，最大 250；非正数或非整数必须拒绝。
- 无 receipt 时返回 `health_state=no_receipts` 和空 latest receipt，不伪造接收状态。
- 返回结果只包含 summary-only receipts/metadata，不返回 external_result、raw payload、prompt、diff、terminal、URL 或 secret。
- summary 只读，不执行 scorer、不重放 external result、不写 Store、不发通知、不创建新的 execution evidence。

## 需求

### 功能需求

- **FR-001**：系统必须登记 `quality_scorer_external_intake_summary.v1` contract，声明 route、required query、状态码/error code 和 AO49 contract tests。
- **FR-002**：HTTP summary 必须按完整 agent/version scope 汇总最近 external intake receipts，并返回 `health_state`、`receipt_count`、`latest_receipt`、state/source counts、accepted execution count 和 scorer refs。
- **FR-003**：HTTP summary 必须要求 `agent_id` 和 `version`；缺任一字段返回 `QUALITY_SCORER_INTAKE_SUMMARY_QUERY_REQUIRED`。
- **FR-004**：HTTP summary 必须校验 `limit`，非法值返回 `QUALITY_SCORER_INTAKE_SUMMARY_LIMIT_INVALID`。
- **FR-005**：生产模式必须要求 `quality.scorer.intake.read` scope，并对 accepted/rejected/denied 写最小 audit record。
- **FR-006**：URI-style 或 raw-marker identity 可参与 hash lookup，但 response query echo 必须 redacted，且 audit 不记录 query payload。
- **FR-007**：`create_app()` 必须声明 summary route，方便外部 scorer 运维工具和 Quality Center 集成发现。

### 关键实体

- **QualityScorerExternalIntakeSummaryRequest**：只读 query envelope，包含 agent/version 和可选 limit。
- **QualityScorerExternalIntakeSummary**：汇总视图，包含 health_state、receipt_count、latest receipt、state/source counts、scorer refs 和 no-auto-action summary。
- **QualityScorerExternalIntakeReceipt**：045 已定义的 summary-only receipt，summary 只读取存量 receipt。

## 成功标准

- **SC-001**：AO49 contract tests 覆盖 registry/app route、successful summary、empty health、query-required、production scope denial、invalid limit no-query-payload audit 和 URI no-raw echo。
- **SC-002**：AO45/AO46/AO47/AO48/AO49 定向回归通过，证明 summary 不新增 execution evidence。
- **SC-003**：`uv run ruff check`、`uv run ruff format --check`、`uv run pytest -q`、`uv run ai-sdlc verify constraints` 和 049 close-check 通过。
