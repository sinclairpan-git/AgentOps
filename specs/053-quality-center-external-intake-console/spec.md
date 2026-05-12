# 功能规格：Quality Center External Intake Console

**功能编号**：`053-quality-center-external-intake-console`  
**创建日期**：2026-05-12  
**状态**：已冻结  
**输入**：承接 `050-quality-center-external-intake-health`、`051-quality-center-external-intake-portfolio` 和 `052-quality-center-external-intake-portfolio-http`，把 external intake 健康态展示到既有 Quality Center Console。继续保持 summary-only、只读、no-auto-action 边界；不执行 scorer、不 replay payload、不读取 raw evidence/prompt/diff/terminal、不自动 rollout、不写 Store、不发送通知。

**范围**：扩展 Console snapshot、前端 API client 校验和 Quality Center 页面。页面展示 per-agent external intake health、顶层 external intake panel、portfolio state、required missing scopes 和 latest receipt 摘要。保留旧快照 fallback；旧后端未提供 external intake 字段时 UI 使用安全 empty/no_receipts 默认值。

## 用户场景与测试

### 用户故事 1 - 质量负责人查看 external intake 覆盖（优先级：P1）

作为 Quality Center 负责人，我希望在 Console 质量中心看到 external intake receiving/no_receipts/needs_review 分布和 portfolio state，以便判断外部 scorer 接入是否健康。

**独立测试**：Console snapshot 输出 `external_intake_panel` 和 `external_intake_portfolio`，前端页面渲染“外部评分输入”“组合覆盖”“缺失必需接入”等中文文案。

### 用户故事 2 - Agent 摘要展示 intake 状态但不泄露（优先级：P1）

作为 Agent Owner，我希望每个 agent summary 能看到 external intake health、receipt_count 和 recommendation，但不显示 URL、secret 或 raw 字段。

**独立测试**：前端 rows 包含 external intake columns；非法 raw URL 或自动动作 flag 导致 API validation 失败；URI/redacted value 不泄露。

### 用户故事 3 - 缺失必需接入进入人工队列（优先级：P1）

作为治理负责人，我希望 `required_missing_scopes` 和 `external_intake` review item 明确展示为人工处理，而不是在 UI 中提供补跑、发布、写回或通知按钮。

**独立测试**：Review queue 可显示 `external_intake` 类型；所有 automatic action flags 为 false；UI 文案只给“连接外部评分器/人工复核”。

## 边界情况

- 旧快照没有 external intake 字段时，fallback 返回 no_receipts/empty，不崩溃、不伪造 receiving。
- `external_intake_required=false` 且无 receipt 时不默认生成人工队列。
- UI 不展示 raw payload、prompt、diff、terminal、download/raw URL、secret marker。
- UI 不提供自动 scorer invocation、rollout、template switch、Store write、notification 控件。

## 需求

### 功能需求

- **FR-001**：Console snapshot `qualityCenterWorkbench` 必须包含 `external_intake_panel`、`external_intake_portfolio` 和每个 agent summary 的 `external_intake_health`。
- **FR-002**：前端 API client 必须校验 external intake no-auto-action flags 和 legacy fallback。
- **FR-003**：Quality Center 页面必须展示 external intake metrics、portfolio summary、latest receipts、required missing scopes 和 per-agent intake health。
- **FR-004**：UI 文案必须保持中文且只读，不出现自动 rollout、自动 scorer、Store write 或 notification action。
- **FR-005**：053 必须回归 AO4/AO42/AO50/AO51/AO52 和 Console npm contract。

## 成功标准

- **SC-001**：AO4 contract tests 覆盖 Console snapshot external intake fields 和 no-auto-action guardrails。
- **SC-002**：Console npm contract 覆盖 API validation、legacy fallback、unsafe external intake rejection 和页面中文文案。
- **SC-003**：Browser smoke 证明 Quality Center 页面渲染 external intake 内容且无明显布局破损。
- **SC-004**：`uv run pytest` 定向套件、`npm test`、ruff、AI-SDLC constraints/truth/close-check 通过。
