# 数据模型：AgentOps 可信最小闭环

**工作项**：`001-agentops-trusted-loop`  
**日期**：2026-05-05  
**状态**：对抗评审前草案

## 1. 模型边界

AgentOps 写以下事实：Session、Run、Step、Event、Evidence、L5Evaluation、BootstrapSession、ReporterCredential、IngestionToken、DeviceKey、PolicyDecision、Approval、QualitySummary、IntegrationSource。

AgentOps 消费但不写以下事实：Agent、AgentVersion、Skill、Package、Installation 基础注册事实来自 Agent Store；User、Role、Attribute 来自统一认证/IAM。

## 2. 表定义

### sessions

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| session_id | string | 是 | 用户意图、工单、PR 或任务上下文 |
| user_id | string | 是 | 统一身份 ID |
| organization | string | 是 | 组织 |
| project | string | 是 | 项目 |
| repo | string | 否 | 代码仓 |
| workitem | string | 否 | 工单/需求/任务 ID |
| source_type | enum | 是 | reporter、sdk、wrapper、connector、imported |
| status | enum | 是 | running、finished、failed、cancelled |
| created_at | datetime | 是 | 创建时间 |
| finished_at | datetime | 否 | 完成时间 |

**索引**：`session_id` unique；`user_id, created_at`；`project, repo, created_at`。

### runs

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| run_id | string | 是 | Agent 执行尝试 |
| session_id | string | 是 | 关联 sessions |
| agent_id | string | 是 | 来自 Agent Store 或 imported evidence |
| agent_version | string | 否 | Agent 版本 |
| installation_id | string | 否 | 安装记录 |
| device_id | string | 否 | 设备 |
| integration_mode | enum | 是 | standalone、enterprise_managed、custom_sink、unknown |
| enterprise_state | enum | 是 | inactive、activating、active、degraded、disabled |
| status | enum | 是 | running、succeeded、failed、cancelled、pending |
| evidence_level | enum | 是 | L1、L2、L3、L4、L5、pending、unknown |
| enforcement_mode | enum | 否 | observe、warn、enforce、degraded |
| policy_state_known | boolean | 是 | 高风险策略是否可追溯 |
| created_at | datetime | 是 | 创建时间 |
| finished_at | datetime | 否 | 完成时间 |

**索引**：`run_id` unique；`session_id`；`agent_id, agent_version, created_at`；`installation_id, device_id`。

### steps

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| step_id | string | 是 | Run 内动作 |
| run_id | string | 是 | 关联 runs |
| parent_step_id | string | 否 | 父动作 |
| step_type | enum | 是 | plan、read、edit、verify、model_call、skill_call、artifact、approval、violation |
| status | enum | 是 | pending、running、succeeded、failed、skipped |
| started_at | datetime | 否 | 开始时间 |
| finished_at | datetime | 否 | 完成时间 |

**索引**：`step_id` unique；`run_id, started_at`；`parent_step_id`。

### events

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| event_id | string | 是 | 事件 ID |
| schema_version | string | 是 | `event-envelope.v1` |
| event_type | string | 是 | Event Catalog 名称 |
| event_type_version | string | 是 | 事件 payload 版本 |
| layer | enum | 是 | raw、domain、derived |
| integration_mode | enum | 是 | standalone、enterprise_managed、custom_sink、unknown |
| enterprise_state | enum | 是 | active、degraded、disabled 等 |
| session_id | string | 否 | 关联 Session |
| run_id | string | 否 | 关联 Run |
| step_id | string | 否 | 关联 Step |
| trace_id | string | 是 | 调用链 |
| span_id | string | 是 | span |
| parent_span_id | string | 否 | 父 span |
| sequence_no | integer | 是 | run 内顺序 |
| idempotency_key | string | 是 | 幂等键 |
| source_trust_level | enum | 是 | verified、declared、ai_suggested、imported、suspected |
| signature_status | enum | 是 | valid、missing、invalid、not_required |
| local_subject | string | 否 | standalone 本地主体 |
| local_workspace_hash | string | 否 | standalone 工作区 hash |
| local_report_uri | string | 否 | standalone 本地报告 URI |
| sink_id | string | 否 | custom_sink 标识 |
| sink_capability_id | string | 否 | custom_sink 能力声明 |
| external_subject | string | 否 | custom_sink 外部主体 |
| data_classification | enum | 是 | public、internal、confidential、restricted |
| redaction_policy | string | 是 | 脱敏策略 |
| payload_hash | string | 是 | payload hash |
| payload_redacted | json | 是 | 脱敏 payload |
| received_at | datetime | 是 | 接收时间 |

**索引**：`event_id` unique；`idempotency_key` unique；`run_id, sequence_no`；`trace_id, span_id`；`event_type, received_at`。

### evidence

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| evidence_id | string | 是 | 证据 ID |
| run_id | string | 是 | 关联 Run |
| source | string | 是 | reporter、ci、git、test、imported |
| level | enum | 是 | L1-L5、pending、unknown |
| trust | enum | 是 | verified、declared、imported、suspected |
| confidence | decimal | 是 | 0-1 |
| completeness | decimal | 是 | 事件链完整度 |
| freshness | enum | 是 | fresh、stale、unknown |
| data_classification | enum | 是 | 数据分级 |
| redaction_policy | string | 是 | 脱敏策略 |
| access_policy | string | 是 | 访问策略 |
| retention_policy | string | 是 | 保留策略 |
| raw_access_state | enum | 是 | not_available、summary_only、requestable、approved、denied、expired |
| missing_evidence | json | 是 | 缺失证据列表 |
| linked_event_ids | json | 是 | 来源事件 |
| calculated_at | datetime | 是 | 计算时间 |

**索引**：`evidence_id` unique；`run_id`；`level, confidence`；`raw_access_state`。

### l5_evaluations

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| evaluation_id | string | 是 | L5 判定 ID |
| run_id | string | 是 | 关联 Run |
| result | enum | 是 | L5、L4、L3、pending、not_eligible |
| conditions | json | 是 | 条件逐项结果 |
| failed_conditions | json | 是 | 失败条件 |
| missing_evidence | json | 是 | 缺失证据 |
| downgrade_reason | string | 否 | 降级原因 |
| evaluated_at | datetime | 是 | 判定时间 |

**索引**：`evaluation_id` unique；`run_id` unique；`result, evaluated_at`。

### bootstrap_sessions

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| bootstrap_id | string | 是 | 激活会话 |
| installation_id | string | 是 | Agent Store 安装记录 |
| device_id | string | 是 | 设备 |
| user_id | string | 是 | 用户 |
| artifact_hash | string | 是 | 安装包 hash |
| assertion_key_id | string | 是 | Agent Store 签名 key |
| assertion_algorithm | string | 是 | 签名算法 |
| assertion_nonce | string | 是 | 防重放 nonce |
| assertion_issued_at | datetime | 是 | assertion 签发时间 |
| status | enum | 是 | created、authenticated、credential_issued、verified、expired、failed |
| trace_id | string | 是 | 跨系统追踪 |
| expires_at | datetime | 是 | 过期时间 |
| created_at | datetime | 是 | 创建时间 |

**索引**：`bootstrap_id` unique；`installation_id, device_id`；`assertion_nonce` unique；`trace_id`。

### reporter_credentials

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| credential_id | string | 是 | 凭证 |
| installation_id | string | 是 | 安装记录 |
| device_id | string | 是 | 设备 |
| issuer | string | 是 | 签发方 |
| scope | json | 是 | 上报范围 |
| status | enum | 是 | active、rotating、expired、revoked |
| issued_at | datetime | 是 | 签发时间 |
| expires_at | datetime | 是 | 过期时间 |
| revoked_at | datetime | 否 | 吊销时间 |

**索引**：`credential_id` unique；`installation_id, device_id, status`。

### ingestion_tokens

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| token_id | string | 是 | token |
| credential_id | string | 是 | 关联 credential |
| ttl_seconds | integer | 是 | TTL |
| status | enum | 是 | active、expired、revoked |
| last_used_at | datetime | 否 | 最近使用 |
| expires_at | datetime | 是 | 过期 |

**索引**：`token_id` unique；`credential_id, status`；`last_used_at`。

### device_keys

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| device_key_id | string | 是 | 设备 key |
| device_id | string | 是 | 设备 |
| public_key_hash | string | 是 | 公钥 hash |
| status | enum | 是 | active、rotating、lost、revoked |
| rotated_at | datetime | 否 | 轮换时间 |
| revoked_at | datetime | 否 | 吊销时间 |

**索引**：`device_key_id` unique；`device_id, status`。

### registries

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| registry_id | string | 是 | registry 条目 |
| registry_type | enum | 是 | schema、api_contract、status_enum、error_code、contract_test |
| name | string | 是 | 名称 |
| version | string | 是 | 版本 |
| platform_owner | string | 是 | 平台 Owner |
| domain_owner | string | 是 | 域 Owner |
| compatibility | enum | 是 | backward_compatible、breaking、deprecated |
| status | enum | 是 | draft、frozen、deprecated |
| contract_test_id | string | 否 | 关联 AO-CT |
| updated_at | datetime | 是 | 更新时间 |

**索引**：`registry_type, name, version` unique；`platform_owner`；`status`。

### policy_decisions

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| decision_id | string | 是 | 裁决 |
| run_id | string | 否 | 关联 Run |
| skill_id | string | 否 | Skill |
| action | enum | 是 | read、write、execute、network、deploy、config_change |
| resource_scope | json | 否 | 资源范围 |
| decision | enum | 是 | block、approval_required、warn、conditional_allow、allow |
| fallback_action | enum | 是 | allow、warn、block、require_online |
| policy_version | string | 是 | 策略版本 |
| decision_reason | string | 是 | 原因 |
| audit_id | string | 是 | 审计 ID |
| decided_at | datetime | 是 | 时间 |

**索引**：`decision_id` unique；`run_id`；`skill_id, action`；`audit_id`。

### agent_store_summaries

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| summary_id | string | 是 | 回显摘要 |
| agent_id | string | 是 | Agent |
| agent_version | string | 否 | 版本 |
| evidence_level | enum | 是 | L1-L5/pending/unknown |
| confidence | decimal | 是 | 置信度 |
| missing_evidence | json | 是 | 缺失证据 |
| risk_state | enum | 是 | normal、warning、blocked、unknown |
| approval_state | enum | 是 | none、pending、approved、rejected、expired |
| score_template_id | string | 是 | 评分模板 |
| calculated_at | datetime | 是 | 计算时间 |
| valid_until | datetime | 是 | 有效期 |
| deep_links | json | 是 | run/evidence/risk 链接 |

**索引**：`summary_id` unique；`agent_id, agent_version`；`valid_until`。

## 3. 状态枚举

| 枚举 | 值 |
|---|---|
| integration_mode | standalone、enterprise_managed、custom_sink、unknown |
| enterprise_state | not_detected、inactive、activating、active、degraded、disabled |
| source_trust_level | verified、declared、ai_suggested、imported、suspected |
| evidence_level | L1、L2、L3、L4、L5、pending、unknown |
| raw_access_state | not_available、summary_only、requestable、approved、denied、expired |
| decision | block、approval_required、warn、conditional_allow、allow |
| fallback_action | allow、warn、block、require_online |

### status_registry

状态注册表不是只保存机器枚举值，还必须保存面向用户和审计的语义字段，避免页面直接暴露 machine value。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| status_id | string | 是 | 状态条目 ID |
| enum_group | string | 是 | integration_mode、enterprise_state、evidence_state、approval_state 等 |
| machine_value | string | 是 | 机器值 |
| display_name | string | 是 | 展示名 |
| plain_language | string | 是 | 白话解释 |
| severity | enum | 是 | normal、info、warning、critical |
| primary_action | string | 是 | 主动作 |
| secondary_action | string | 否 | 次动作 |
| visible_roles | list[string] | 是 | 可见角色 |
| notification_rule | string | 是 | 通知规则 |
| audit_required | boolean | 是 | 是否必须审计 |
| owner | string | 是 | 状态 Owner |
| allowed_transitions | list[string] | 是 | 允许流转目标 |
| store_echo_policy | string | 是 | Agent Store 回显策略 |

**索引**：`enum_group, machine_value` unique；`owner`；`severity`。

## 4. 关系约束

- `runs.session_id` 必须引用 `sessions.session_id`。
- `steps.run_id` 必须引用 `runs.run_id`。
- `events.run_id` 可为空，但 enterprise_managed L5 核心事件进入 L5 Gate 前必须可映射到 run。
- `evidence.run_id` 必须引用 `runs.run_id`。
- `l5_evaluations.run_id` 与 `runs.run_id` 一对一保留最新判定，历史可进入 audit log。
- `reporter_credentials.installation_id` 来自 Agent Store installation，不由 AgentOps 创建注册事实。
- `agent_store_summaries` 是 AgentOps 生成的回显投影，不是 Agent 注册事实。

## 5. 保留与脱敏

- Raw payload 默认不进入阶段 1 核心存储；只保存 hash 与 redacted payload。
- Evidence Summary 保留周期按 data_classification 与 retention_policy 决定。
- raw_access_state 为 approved 前，任何 API 不得返回未脱敏原文。
- 脱敏失败时 evidence 仍可保存 hash，但必须标记 `raw_access_state=not_available` 并产生告警。
