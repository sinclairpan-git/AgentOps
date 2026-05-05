# 技术调研与方案决策：AgentOps 可信最小闭环

**工作项**：`001-agentops-trusted-loop`  
**日期**：2026-05-05  
**状态**：对抗评审前草案

## 1. 设计原则

1. **契约先行**：先冻结 EventEnvelope、API、错误码、状态枚举和 contract tests，再实现服务。
2. **事实源边界清晰**：AgentOps 写运行事实、证据、策略、审批、风险；Agent Store 写 Agent/Skill/Installation 注册事实。
3. **L5 是 run 级判定**：Ai_AutoSDLC 官方应用只能是 L5-capable，单次 run 是否 L5 必须由 AgentOps evaluator 判定。
4. **低证据不伪装高证据**：缺签名、缺 fresh verification、governance degraded、outbox pending 必须降级或 pending。
5. **默认脱敏**：Evidence Summary 默认摘要/hash，原文必须走 Evidence Vault 审批。

## 2. 关键决策

| 决策 | 选项 | 选择 | 理由 | 影响 |
|---|---|---|---|---|
| API 设计 | REST / gRPC / message queue first | REST + OpenAPI first | 阶段 1 需要 Agent Store、Reporter、测试框架都能快速消费 | 后续可在 Ingestion 内部扩展 queue |
| Schema 技术 | Pydantic / JSON Schema only / ad hoc dict | Pydantic + JSON Schema/OpenAPI | Python 3.11+ 下易实现可执行校验和契约导出 | 需要保持 schema_version 兼容 |
| Event 存储 | 单表日志 / raw-domain-derived 分层 | raw event + domain event + derived fact | 符合顶层事件分层，便于审计和重放 | 写入路径略复杂 |
| 幂等策略 | event_id only / idempotency_key only / 双键 | event_id + idempotency_key 双键 | outbox 重放和 producer bug 都能防重 | 需要唯一索引和冲突处理 |
| 签名验证 | 直接实现加密细节 / 抽象 verifier | 抽象 verifier + contract mock | 阶段 1 可验证语义，避免被具体 IAM/密钥方案阻塞 | Phase 2/3 可替换真实 verifier |
| L5 Gate | DB 查询耦合 / 纯函数 evaluator | 纯函数 evaluator | 易测试、可解释、可复用到批处理 | 调用层需组装完整输入 |
| 原文证据 | 阶段 1 存原文 / 默认不存原文 | 默认摘要/hash，保留 raw_access_state | 降低敏感信息风险，符合 PRD | 语义质量分析推迟 |
| Policy Check | 阶段 1 完整实现 / 阶段 1 降级口径 | 阶段 1 降级口径 | PRD 明确强 SLO 从阶段 2 起 | 需清晰展示 unknown 不等于 allow |
| 管理员 UI | 先做完整前端 / 先做 view model | 先做 view model | 当前阶段重在可解释状态和契约 | 前端实现可稍后接入 |

## 3. EventEnvelope v1 冻结点

EventEnvelope v1 必须是 AgentOps 所有 producer 的唯一入口语义，字段不能被不同项目重写。enterprise_managed 事件的最小必填字段包括：

- identity：user_id、identity_confidence、organization、project、repo。
- agent binding：agent_id、agent_version、installation_id、device_id。
- trace：session_id、run_id、step_id、trace_id、span_id、parent_span_id。
- ordering：sequence_no、idempotency_key、timestamp。
- trust：integration_mode、enterprise_state、source_trust_level、signature。
- data governance：data_classification、redaction_policy、payload_hash。
- payload：按 event_type_version 校验的结构体。

条件必填规则：

- enterprise_managed 必须包含 agent_version、installation_id、device_id、signature、span_id；credential、device 和 installation 验证完成前不得展示 active。
- standalone 远端导入不得包含企业 credential 语义；即便有 session/run，也只能作为 imported evidence 或被解释性拒绝。
- custom_sink 必须带 capability descriptor，由外部系统自行声明证据能力，不得冒用 AgentOps L5。

## 3.1 Registry 冻结策略

| Registry | 平台 Owner | 域 Owner | 阶段 0 冻结内容 |
|---|---|---|---|
| Schema Registry | AgentOps | AgentOps / Ai_AutoSDLC / Agent Store | event envelope、payload schema、evidence schema、policy schema |
| API Contract Registry | AgentOps | 对应 API owner | Ingestion、Credential、Evidence、Policy、Store Summary |
| 状态枚举 Registry | AgentOps + 统一体验 Owner | 三项目 Owner | 机器值、展示名、严重度、动作、流转 |
| 错误码 Registry | AgentOps | 三项目 Owner | 错误码、HTTP 映射、retryable、human_action_required |
| Contract Test Registry | AgentOps | producer/consumer 双方 | AO-CT-001 到 AO-CT-006 正反例、幂等、兼容 |

## 4. Bootstrap 签名与凭证决策

Bootstrap 必须是可重放防护的短期签名交换，不接受“页面已登录所以可信”的弱证明。

| 字段/机制 | 阶段 1 约束 |
|---|---|
| canonicalization | JSON canonical form，字段排序稳定，签名前不包含 signature 本身 |
| algorithm | 由 registry 声明，默认 `ed25519` 或企业 IAM 支持的等价非对称签名 |
| key_id | assertion 与 device proof 均必须带 key_id，用于查找 issuer public key |
| timestamp skew | 默认允许 5 分钟时钟偏差，超出返回 `BOOTSTRAP_TIMESTAMP_SKEW` |
| nonce/replay window | bootstrap_id + nonce 在 TTL 内唯一，重复使用返回同状态或 `BOOTSTRAP_REPLAY_DETECTED` |
| assertion TTL | 默认 10 分钟，过期返回 `BOOTSTRAP_EXPIRED` |
| device proof TTL | 默认 5 分钟，绑定 device_id 与 public_key_hash |
| rotation | ReporterCredential、IngestionToken、DeviceKey 都必须支持 rotating 状态 |
| revocation propagation | revoked credential/token/device key 必须使后续 enterprise_managed 事件失去 L5 资格 |

## 5. L5 Gate 决策

L5 evaluator 输入必须是结构化事实，而不是日志文本。每个条件输出 `pass/fail/pending/not_applicable`，并带 reason code。

| 条件 | 失败后最高等级 | 说明 |
|---|---|---|
| reporter_enabled | L3 | 除非有其他可信 Agent 事件源 |
| governance_loaded | L4 | degraded/unsupported 不得完整 L5 |
| schema_valid | L3 | 核心事件 schema 失败不能高置信 |
| source_signed | L3 | 无签名事件不得进入 L5 |
| identity_confidence | L4 | ambiguous/missing 不得完整 L5 |
| session_mapping | L4 | 无法映射 session/run/step |
| stage_events_complete | L4 | 缺 gate_result 或 violation_scan_completed 不完整 |
| verification_fresh | L4 | 缺 fresh verification 不得 L5 |
| artifact_linked | L4 | 产物或 snapshot 无法追踪 |
| outbox_delivered | pending | 可显示 pending L5 verification |
| policy_state_known | L4 | 高风险动作策略未知不得 L5 |

## 6. 管理员体验决策

阶段 1 不交付完整前端，但必须冻结页面模型：

- **Overview**：今日风险、Ingestion 健康、DLQ、pending L5、证据失败。
- **Runs**：session/run/step 调用链、事件状态、L5 Gate 明细。
- **Evidence Explorer**：脱敏摘要、raw_access_state、申请原文、缺失证据。
- **Risk Triage**：critical/security_revoked、policy_block、approval_overdue、evidence_failed、quality_drop 排序。
- **Approval Center**：审批原因、审批人、SLA、补充材料、撤回、拒绝原因、过期/撤销影响、Store/通知/审计回显。
- **Policy Center**：裁决优先级、fallback_action、enforcement_mode、policy_version、resource_scope、Grant TTL、策略降级。
- **Quality Center**：score_template_id、证据等级、置信度、缺失证据、解释链、申诉入口、低置信人工复核。
- **Connector Status**：freshness、rate_limit、replay watermark、degraded reason。

所有状态都必须有 `primary_action`、`secondary_action`、`owner_hint`、`audit_id/request_id`。

阶段 0 还必须冻结跨系统体验层：

- 统一 Shell：一级入口、角色默认首页、面包屑、return_url。
- 通知中心：审批变化、DLQ、证据降级、credential revoked、Store 回显失败。
- 待办中心：我的审批、我的风险、我的 DLQ、我的补证据。
- 全局搜索：按权限搜索 Agent 摘要、run、evidence、risk、approval。
- 状态文案：机器值到用户可理解文案的映射，不把 `pending_l5_verification` 原样扔给用户。
- 可访问性：WCAG 2.2 AA、键盘可达、焦点可见、权限失败不泄露敏感事实。

## 7. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 过早实现完整质量评分导致范围膨胀 | 阶段 1 只做 summary-ready 字段和 missing_evidence |
| 未签名或 custom_sink 事件被误判为 L5 | integration_mode + signature + credential 三重门禁 |
| Agent Store/AgentOps 注册事实源混淆 | AgentOps 只消费 Store metadata，不写注册事实 |
| 敏感 prompt/diff 泄露 | 默认 hash/摘要，Evidence Vault 原文审批 |
| Policy Service 未完成却显示安全 | 高风险 unknown 默认 require_online/block |
| Outbox 重放造成重复事件 | event_id + idempotency_key 唯一约束 |

## 8. 未解决项

当前无阻塞阶段 0/1 的未解决技术问题。IAM、Agent Store Registry、生产存储选型作为联调前开放项记录在 `spec.md` 与 `plan.md`。
