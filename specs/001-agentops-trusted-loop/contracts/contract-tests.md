# Contract Tests：AO-CT-001 到 AO-CT-006

**工作项**：`001-agentops-trusted-loop`  
**日期**：2026-05-05

## AO-CT-001 Reporter Event Envelope

- **正例**：enterprise_managed 事件包含有效 signature、token、installation_id、device_id、idempotency_key、sequence_no，写入 Raw Event 并映射 Domain Event。
- **L5 payload 正例**：`stage_started/stage_completed/gate_result/verification_result/violation_scan_completed/artifact_generated/generation_snapshot/l5_eligibility_input` 均按 `event-envelope-v1.schema.yaml` 的最小 payload 字段校验通过。
- **反例**：缺 signature 返回 `EVENT_SIGNATURE_REQUIRED`；schema_version 不支持返回 `EVENT_SCHEMA_UNSUPPORTED`；L5 核心 payload 缺必填字段返回 `EVENT_PAYLOAD_INVALID`。
- **幂等**：同 idempotency_key 重放返回 deduplicated，不重复写核心事实。
- **兼容**：event_type_version minor version 向后兼容。

## AO-CT-002 Credential Issue API

- **正例**：active bootstrap session + 有效 signed_installation_assertion 签发 ReporterCredential、IngestionToken、DeviceKey。
- **反例**：过期 bootstrap 返回 `BOOTSTRAP_EXPIRED`；artifact_hash 不一致返回 `BOOTSTRAP_ARTIFACT_MISMATCH`；installation_id 或 user_id 与 BootstrapSession 不一致返回 `BOOTSTRAP_IDENTITY_MISMATCH`。
- **幂等**：同 bootstrap_id 的有效重试返回同 credential 状态；缺 assertion、缺 device proof 或身份不匹配的重试不得绕过校验。
- **兼容**：Credential status 旧值可解释为 degraded，不静默 allow。
- **签名约束**：canonicalization、algorithm、key_id、issued_at、nonce、timestamp skew 和 replay window 必须参与校验。

## AO-CT-003 Evidence Summary

- **正例**：有权限用户获得脱敏摘要、raw_access_state、missing_evidence、linked_event_ids。
- **反例**：无权限访问原文返回 `RAW_ACCESS_DENIED`。
- **幂等**：同一 run 的相同输入重复计算返回同 evidence_id 或同 summary hash。
- **兼容**：旧 schema 摘要可降级展示，不返回未识别原文字段。

## AO-CT-004 PolicyDecision

- **正例**：高风险动作按策略只能返回 block 或 approval_required，并包含 fallback_action、policy_version、audit_id。
- **反例**：缺 resource_scope 返回 `POLICY_SCOPE_REQUIRED`。
- **幂等**：同 policy_version 的旧决策查询保持可解释。
- **兼容**：阶段 1 policy unknown 输出 require_online/block 降级说明。

## AO-CT-005 Agent Store Summary

- **正例**：Agent Store 消费质量/风险/审批摘要，字段包含 evidence_level、confidence、missing_evidence、calculated_at、valid_until、deep_links。
- **反例**：consumer schema 不兼容返回 `SUMMARY_SCHEMA_UNSUPPORTED`。
- **幂等**：同 agent/version 与同 calculated_at 返回稳定 summary。
- **兼容**：schema minor version 向后兼容；未知字段必须被 consumer 安全忽略。

## AO-CT-006 Integration Mode Ingestion

- **正例**：enterprise_managed 进入 L5 Gate；custom_sink 作为 imported evidence；standalone 远端事件不进入 L5。
- **反例**：unknown mode 返回 `INTEGRATION_MODE_UNSUPPORTED` 或降级为 imported evidence。
- **幂等**：integration_mode 不改变 idempotency_key 的防重语义。
- **兼容**：新增 mode 必须先进入 Schema Registry，不得直接进入 L5。
