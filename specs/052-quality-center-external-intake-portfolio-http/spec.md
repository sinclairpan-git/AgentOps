# 功能规格：Quality Center External Intake Portfolio HTTP

**功能编号**：`052-quality-center-external-intake-portfolio-http`  
**创建日期**：2026-05-12  
**状态**：已冻结  
**输入**：承接 `051-quality-center-external-intake-portfolio` 的非目标“HTTP route”。继续保持 summary-only、只读、no-auto-action 边界；不执行 scorer、不 replay payload、不读取 raw evidence/prompt/diff/terminal、不自动 rollout、不写 Store、不发送通知。

**范围**：新增 `GET /v1/quality/center/external-intake/portfolio`，通过 query string 中重复的 `scope=agent_id@version` 指定一个或多个 agent/version scope，可选 `required_scope=agent_id@version` 标记必须存在 external intake 的 scope。Route 调用 051 portfolio builder，返回 `quality_center_external_intake_portfolio_http.v1` envelope 和嵌套 `quality_center_external_intake_portfolio.v1`，并在生产模式要求 `quality.scorer.intake.read` scope。

## 用户场景与测试

### 用户故事 1 - 运维通过 HTTP 查询 intake portfolio（优先级：P1）

作为 Quality Center 运维人员，我希望通过稳定 HTTP endpoint 查询多个 agent/version 的 external intake portfolio，以便 Console 或外部运维工具无需直接调用 Python API。

**独立测试**：先写入 accepted external intake receipt，再调用 HTTP portfolio route，断言返回 200、route/method、portfolio receiving state、latest receipts 和 no-auto-action summary，且未新增 scorer execution。

### 用户故事 2 - 多 scope 和 required scope 必须可解释（优先级：P1）

作为治理负责人，我希望 route 能明确标记 required scope 缺 receipt 的组合缺口，但只生成人工建议，不自动补跑 scorer 或通知。

**独立测试**：请求包含一个有 receipt scope、一个 `required_scope` 且无 receipt scope，断言 portfolio 返回 `required_missing_scope_count=1`、`portfolio_state=incomplete` 或 `needs_review`，所有 automatic action flags 为 false。

### 用户故事 3 - HTTP 边界拒绝不安全或越权查询（优先级：P1）

作为安全负责人，我希望 route 拒绝缺少 scope、非法 scope、非法 limit 和生产模式缺读权限的请求，并写入不含 query payload/raw marker 的最小 audit。

**独立测试**：缺 scope 返回 `QUALITY_CENTER_INTAKE_PORTFOLIO_SCOPE_REQUIRED`；非法 scope/limit 返回对应 400；生产模式缺 `quality.scorer.intake.read` 返回 403；URI-style identity 可 hash lookup 但 response 只回显 `[redacted]` 和 hash identity。

## 边界情况

- `scope` 至少一个，最多 25 个；超出时截断到 25 个并在 `window_limit` 中返回实际限制。
- `scope` 与 `required_scope` 必须使用 `agent_id@version` 格式；缺任一边拒绝。
- URI-style agent_id 可参与 hash lookup；response 不回显原始 URL、secret marker 或 raw 字段。
- Route 不读取 request body，不记录 query 原文，不创建 execution evidence，不调用 external scorer，不写 Store，不发送通知。

## 需求

### 功能需求

- **FR-001**：系统必须登记 `quality_center_external_intake_portfolio_http.v1` contract，声明 route、method、required query、状态码/error code 和 AO52 contract tests。
- **FR-002**：`create_app()` 必须声明 `quality_center_external_intake_portfolio` route。
- **FR-003**：HTTP route 必须要求至少一个 `scope=agent_id@version`，可接受多个 scope 和多个 required_scope。
- **FR-004**：生产模式必须要求 `quality.scorer.intake.read` scope，并对 accepted/rejected/denied 写最小 audit record。
- **FR-005**：HTTP response 必须是 summary-only envelope，不返回 raw payload/prompt/diff/terminal/URL/secret 或 query 原文。
- **FR-006**：HTTP route 必须只读，不创建 scorer execution、rollout/template switch、Store write 或 notification。

### 关键实体

- **QualityCenterExternalIntakePortfolioHttpRequest**：只读 query envelope，包含 scope、required_scope 和可选 limit。
- **QualityCenterExternalIntakePortfolioHttpResponse**：HTTP envelope，包含 route、method、window_limit、portfolio、summary 和 audit_id。
- **QualityCenterExternalIntakePortfolio**：051 已定义的嵌套 portfolio projection。

## 成功标准

- **SC-001**：AO52 contract tests 覆盖 registry/app route、successful HTTP portfolio、required missing scopes、query-required、invalid scope/limit、production scope denial、URI identity no-raw echo。
- **SC-002**：AO50/AO51/AO52 定向回归通过，证明 HTTP route 不破坏 backend portfolio。
- **SC-003**：`uv run ruff check`、`uv run ruff format --check`、`uv run pytest` 定向套件、AI-SDLC constraints/truth/close-check 通过。
