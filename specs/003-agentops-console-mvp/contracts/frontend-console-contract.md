# AgentOps Console MVP 前端契约

**工作项**：`003-agentops-console-mvp`  
**状态**：对抗评审前草案  
**技术栈**：Vue 2.x  
**组件库**：SDLC 企业 Vue2 组件库，本地来源 `/Users/sinclairpan/project/前端组件库1`，包名 `@sxf/er-components`

## 1. Provider 约束

AgentOps Console 必须遵守 SDLC `016-frontend-enterprise-vue2-provider-baseline`：

- 企业 Vue2 组件库是 Provider 能力来源，不是 UI Kernel，也不是业务项目默认入口。
- 默认入口只能注册白名单包装后的组件能力。
- 禁止默认全量 `Vue.use(@sxf/er-components)` 或 `Vue.use(ErComponents)`。
- 危险能力默认关闭，包括全局弹窗劫持、全局通知滥用、任意 HTML 注入、无权限原文导出。
- 企业组件库不可用时，Console 可以使用项目内 shim 保持 MVP 可运行，但 contract 中必须保留 Provider 边界。
- 允许按需引入 `@sxf/er-components/<component>` 与对应组件样式；默认禁止 `_global/mask`、`_global/notify`、`window` 等全局插件注册。
- 允许 `@sxf/er-config` 的 `setLocale`、`updateGlobalConfig` 只用于 i18n 与 VueConstructor 初始化；不得借此开启全量组件注册或覆盖安全默认值。
- 允许核心样式按需引入，禁止把组件库 reset/global side effect 作为业务页面默认依赖，除非 Provider contract 明确记录影响面。

### 1.1 MVP 白名单

| Ui capability | 企业组件来源建议 | MVP fallback | 说明 |
|---|---|---|---|
| `UiButton` | button | native button wrapper | 仅命令按钮 |
| `UiCard` | card | section/article wrapper | 仅用于 repeated item 或工具区域 |
| `UiTag` | tag | status badge | 表达状态，不承载复杂交互 |
| `UiTabs` | tabs | segmented nav | 页面内状态切换 |
| `UiDrawer` | drawer | side panel | 详情查看，不展示 raw payload |
| `UiMenu` | nav-menu/menu | sidebar nav | 主导航 |
| `UiToolbar` | toolbar | div toolbar | 筛选和主动作 |
| `UiPagination` | pagination | simple pager | 列表分页 |
| `UiGrid` | grid/grid-form | responsive grid | 摘要指标与表格 |

## 2. 页面契约

| page_id | 页面 | P0 字段/状态 | 主交互 |
|---|---|---|---|
| `overview` | Overview | run_count、l5_gate、policy_slo、approval_backlog、evidence_health、connector_health | 跳转风险、审批、证据 |
| `runs` | Runs | run_id、agent_id、skill_id、risk_level、l5_state、policy_state、evidence_state | 筛选、查看详情 |
| `evidence` | Evidence Explorer | evidence_id、redacted_summary、payload_hash、raw_access_state、audit_id、denied_scope | 状态筛选、申请权限入口 |
| `approvals` | Approval Center | approval_id、requester、reason、affected_actions、sla_due_at、status、grant_id | 状态筛选、查看 Grant |
| `policies` | Policy Center | decision、fallback_action、policy_version、grant_ttl、audit_id、degrade_action | 决策筛选、查看策略来源 |
| `quality` | Quality Center | signal_id、category、status、score、evidence_ref、owner_hint、primary_action | 质量筛选、查看 gate 证据 |
| `risks` | Risk Triage | risk_id、source、severity、owner_hint、primary_action、deep_link | 风险筛选、跳转处理 |
| `connectors` | Connector Status | connector_id、status、last_seen_at、degrade_action、request_id | 查看影响范围 |
| `sdlc-runs` | Ai_AutoSDLC Runs | adapter_status、dry_run_status、proof_source、captured_at、verified_loaded | 区分预演与治理激活 |

## 3. 状态契约

### 3.1 通用状态

- `healthy`
- `unknown`
- `degraded`
- `empty`
- `loading`
- `error`
- `permission_denied`

规则：

- `unknown` 不得显示为 `healthy`。
- `degraded` 不得显示为 `allow`。
- `permission_denied` 必须包含 `denied_scope` 以及 `audit_id` 或 `request_id`。

### 3.2 Evidence 状态

- `summary_only`
- `pending_approval`
- `approved_limited`
- `expired`
- `redaction_failed`
- `permission_denied`

规则：

- UI 数据与 DOM 中不得出现 `raw_payload`。
- `redaction_failed` 不得展示不可信 `redacted_summary` 正文。
- `approved_limited` 只能显示限时授权状态，不在摘要卡片展示原文。

### 3.3 Policy 状态

- `block`
- `approval_required`
- `warn`
- `conditional_allow`
- `allow`
- `degraded`
- `unknown`
- `permission_denied`

规则：

- 高风险 `unknown` 必须显示阻断或 require_online 说明。
- active Grant 不得覆盖更高优先级 deny/block。
- `allow` 必须有 `policy_version` 与 `audit_id`。

### 3.4 Approval/Grant 状态

- Approval：`pending`、`needs_more_info`、`approved`、`rejected`、`expired`、`revoked`、`escalated`
- Grant：`active`、`consumed`、`expired`、`revoked`、`scope_mismatch`

规则：

- expired/revoked grant 不得显示为 active。
- pending/escalated 必须展示 SLA 或升级动作。
- requester 自批不得成为默认 UI 主动作。

### 3.5 SDLC Adapter 状态

- `materialized`
- `verified_loaded`
- `degraded`
- `unsupported`
- `dry_run_passed`
- `unverified`

规则：

- `dry_run_passed` 不得等同 `verified_loaded`。
- `materialized/unverified` 必须显示为未完成治理激活证明。
- `verified_loaded` 必须展示 machine-verifiable evidence、proof_source、captured_at。

## 4. 契约测试

### AO3-CT-001 Console Shell

- Given Console 启动
- When 浏览器打开首页
- Then 主导航、顶部状态、Overview 主内容可见
- And 切换至少三个页面后内容随路由更新

### AO3-CT-002 Enterprise Vue2 Provider

- Given 前端代码加载 Provider
- When 搜索默认入口
- Then 不存在 `Vue.use(ErComponents)` 或全量 `Vue.use(@sxf/er-components)` 路径
- And Provider 暴露白名单能力与 fallback 说明

### AO3-CT-003 Evidence UI Safety

- Given mock data 包含 `redaction_failed` 与 `permission_denied`
- When Evidence Explorer 渲染
- Then DOM 中不得出现 `raw_payload`
- And `redaction_failed` 只展示 hash、告警与补救动作

### AO3-CT-004 Policy/Risk UI

- Given mock data 包含 `unknown`、`degraded`、`approval_required`、`block`
- When Policy Center 与 Risk Triage 渲染
- Then unknown/degraded 不显示为 healthy/allow
- And 高风险状态展示 fallback_action 或 degrade_action

### AO3-CT-005 Approval UI

- Given mock data 包含 pending、approved、expired、revoked、escalated
- When Approval Center 渲染
- Then 每类状态有明确文案、主动作和审计字段
- And expired/revoked Grant 不显示 active

### AO3-CT-006 Quality UI

- Given mock data 包含 `quality_drop`、contract gap、browser gate degraded
- When Quality Center 渲染
- Then 每个质量信号有 score、status、owner_hint、evidence_ref 和 primary_action
- And 质量数据缺失不得显示 healthy

### AO3-CT-007 SDLC Adapter UI

- Given adapter 状态为 materialized/unverified 且 dry-run 通过
- When Ai_AutoSDLC Runs 渲染
- Then 页面说明 dry-run 可运行但不构成 verified_loaded 证明
- And verified_loaded 只在存在 proof_source/captured_at/evidence 时显示

## 5. 浏览器验收

最低视口矩阵：

| matrix_id | viewport | 验收 |
|---|---|---|
| `desktop-1440` | 1440x1000 | 首页无空白、导航可切换、九页可达，包含 Quality Center |
| `mobile-390` | 390x844 | 导航可操作、关键按钮不遮挡、状态 badge 不溢出 |

验收口径：

- 首屏必须是 AgentOps Console 产品界面，不是营销页。
- 文字不得互相遮挡。
- 页面主内容不得空白。
- Quality Center 必须纳入桌面/移动导航与截图验收，且 `quality_drop`、browser gate、contract gap 状态可见。
- Evidence、Policy、Approval、Adapter 四类安全红线必须可见。
- 键盘 Tab 能到达主导航、筛选按钮和主要动作按钮。
- 焦点态必须可见，文字与状态 badge 保持基础对比度。
- 截图产物命名建议：`ao3-console-<matrix_id>-<page_id>.png`。

## 6. 跨平台工程验收

AgentOps Console 的三端兼容声明必须依赖目标平台 CI 证据：

- GitHub Actions 必须覆盖 Windows、Linux、macOS。
- 前端必须在三端执行 `npm ci --audit=false`、`npm test`、`npm run build`。
- 后端必须在三端执行 `uv sync --locked`、`uv run ruff check src tests`、`uv run pytest tests -q`。
- 后端必须在三端分别执行 `uv build --sdist --wheel --out-dir dist/python` 并上传独立 artifact。
- 前端必须在三端分别上传 `apps/agentops-console/dist/**` 独立 artifact。
- 本地 macOS 验证、Windows 验证或 Linux 验证都不能单独替代其他平台证据。
- 企业私有依赖不得因外部 `npm audit` 默认泄露到公共服务。
