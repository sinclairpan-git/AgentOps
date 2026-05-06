# 功能规格：AgentOps Console API 快照与联调闭环

**功能编号**：`004-agentops-console-api-snapshot`  
**创建日期**：2026-05-06  
**状态**：实现中  
**工作项分类**：`new_requirement`  
**继承 baseline_id**：`agent-platform-baseline-2026-05-v1.4.2`  
**上游依赖**：`001-agentops-trusted-loop`、`002-agentops-policy-approval-vault`、`003-agentops-console-mvp`

## 1. 目标与边界

### 1.1 项目目标

本工作项把 003 阶段的静态 Console MVP 推进为“前后端可联调的最小运行闭环”。Console 不应只能消费前端 mock；它必须优先从 AgentOps 后端读取治理快照，并在后端不可用时用明确的中文降级状态安全回退。

阶段 4 完成后，平台必须能够证明：

1. Python 后端提供无重型框架依赖的最小 HTTP API：`/v1/health` 与 `/v1/console/snapshot`。
2. `/v1/console/snapshot` 返回 Console 已冻结的信息架构：总览、运行记录、证据、审批、策略、质量、风险、连接器与 Ai_AutoSDLC 运行。
3. API 快照不包含 `raw_payload`，不得把 `materialized/unverified` 表达为 `verified_loaded`。
4. Vue2 Console 优先拉取 API 快照；请求失败、超时或 schema 不合格时，必须显示中文降级提示并安全回退本地 mock。
5. 本阶段保持跨平台优先，不引入 FastAPI/Flask/Node 服务端等新运行时依赖。

### 1.2 本期范围

- 新增 AgentOps Console Snapshot view model builder。
- 新增 Python 标准库 HTTP server，可通过 `python -m agentops.api.server` 启动。
- 新增 Console API 契约文档与 Python/前端 contract tests。
- Vue2 Console 新增 runtime data adapter，支持 API 优先、mock 回退和中文加载/错误/降级提示。
- Vite 开发环境支持通过 `VITE_AGENTOPS_API_BASE` 指定后端地址，默认 `http://127.0.0.1:8765`。

### 1.3 本期不做

- 不做生产身份登录、IAM 鉴权、多租户和 ABAC/RBAC 后端。
- 不做生产数据库、真实 Evidence Vault 原文存储或异步事件队列。
- 不替换 001/002 已完成的核心契约，只把其页面模型聚合成 Console snapshot。
- 不声明 `ai-sdlc run --dry-run` 等于 `verified_loaded`。
- 不把 fallback mock 当作真实后端健康证明。

## 2. 用户故事与验收

### 用户故事 1 - 管理员打开真实 API 驱动的控制台（P0）

作为 AgentOps 管理员，我希望控制台从后端读取治理快照，以便看到同一份后端事实在页面上的呈现，而不是只能看静态 mock。

**验收场景**：

1. **Given** 后端 API 可用，**When** Console 加载，**Then** 页面展示 API snapshot，并显示“后端快照已连接”。
2. **Given** 后端 API 不可用，**When** Console 加载，**Then** 页面展示中文降级提示，并回退到本地安全样例。
3. **Given** API 返回 `materialized/unverified`，**When** Ai_AutoSDLC 运行页展示，**Then** 不显示为 `verified_loaded`。

### 用户故事 2 - 开发者跨平台启动最小联调（P0）

作为开发者，我希望在 macOS、Windows、Linux 上用 Python 标准库启动后端，用 Vite 启动前端，以便无需额外服务框架即可完成最小联调。

**验收场景**：

1. **Given** 已安装 Python 3.11+，**When** 执行 `python -m agentops.api.server --port 8765`，**Then** `/v1/health` 返回健康状态。
2. **Given** 前端设置 `VITE_AGENTOPS_API_BASE`，**When** Console 加载，**Then** 请求该地址的 `/v1/console/snapshot`。
3. **Given** API 不返回合法 JSON，**When** Console 解析失败，**Then** 使用 mock 并标注“后端快照不可用”。

## 3. 功能需求

- **FR-001**：系统必须提供 `build_console_snapshot()`，返回 Console 页面所需完整快照。
- **FR-002**：系统必须提供 `/v1/health`，返回 `service`、`status`、`version`。
- **FR-003**：系统必须提供 `/v1/console/snapshot`，返回 `schema_version`、`generated_at`、`source`、`routes`、`consoleData`。
- **FR-004**：API 必须设置 CORS allowlist，默认允许 `127.0.0.1` 与 `localhost` 的本地开发端口，不默认返回 `Access-Control-Allow-Origin: *`。
- **FR-005**：API 对未知路径返回 404 JSON，不返回 HTML 错误页。
- **FR-006**：前端必须优先拉取 API snapshot，失败时回退 `mockAgentOpsData`。
- **FR-007**：前端必须显示中文数据来源状态，不得用英文错误文本面向用户。
- **FR-008**：snapshot 和前端 adapter 均不得包含或展示 `raw_payload`。
- **FR-009**：`verified_loaded` 只有在存在非待采集机器证明时才允许展示为已验证加载。

## 4. 契约测试矩阵

| test_id | 契约 | 正例 | 反例/错误码 |
|---|---|---|---|
| AO4-CT-001 | Console Snapshot Schema | 返回完整九类数据 | 缺 routes/consoleData 失败 |
| AO4-CT-002 | HTTP API | `/v1/health` 与 `/v1/console/snapshot` 返回 JSON | 未知路径返回 404 JSON |
| AO4-CT-003 | CORS | 本地前端可跨域读取 | 通配 `*` 或外部 Origin 放行失败 |
| AO4-CT-004 | Evidence Safety | snapshot 不含 `raw_payload` | 任意层级出现 `raw_payload` 失败 |
| AO4-CT-005 | Adapter Truth | materialized/unverified 不显示为 verified_loaded | dry-run 伪装 verified_loaded 失败 |
| AO4-CT-006 | Frontend Fallback | fetch 失败、超时、schema 异常、非法状态回退 mock 并中文提示 | 空白页或英文错误提示失败 |

## 5. 成功标准

- **SC-001**：`python -m agentops.api.server --port 8765` 可启动最小后端。
- **SC-002**：Vue2 Console 可从 API snapshot 渲染，后端不可用时安全回退。
- **SC-003**：Python 与前端 contract tests 覆盖 AO4-CT-001 到 AO4-CT-006。
- **SC-004**：`npm test`、`npm run build`、`uv run pytest tests -q`、`uv run ruff check src tests` 通过。
- **SC-005**：两个常驻对抗 agent 对文档、实现和验证无 P0/P1 阻断意见。
