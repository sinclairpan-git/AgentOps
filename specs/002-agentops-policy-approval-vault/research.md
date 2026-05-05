# 研究记录：AgentOps 阶段 2 Policy / Approval / Grant / Evidence Vault

**工作项**：`002-agentops-policy-approval-vault`  
**日期**：2026-05-05  
**来源**：AgentOps PRD 阶段 2、顶层 PRD v1.4.2、001 close summary

## 1. Policy Check 强治理

| 决策点 | 选项 | 决策 | 理由 | 风险控制 |
|---|---|---|---|---|
| Policy Check 形态 | 同步 API / 异步队列 / 仅离线摘要 | 同步 API 语义 + 可执行内核 | 阶段 2 明确 P95 <= 500ms，执行前必须得到裁决 | service unavailable 高风险 require_online/block |
| 裁决优先级 | 各源平级合并 / deny 优先 | deny/block 最高优先 | PRD 冻结统一鉴权/安全 IAM 高于 AgentOps Policy | contract test 覆盖 IAM deny 覆盖 allow |
| 高风险未知状态 | allow + warning / require_online / block | require_online/block | 阶段 1 已明确未知不得显示安全，阶段 2 纳入强 SLO | policy_state_known=false 不得 allow |
| Grant 消费 | 可选 / 高风险必需 | 高风险 conditional_allow 必须绑定 active Grant | 保证审批到执行可追踪 | Grant scope/status/expiry 必验 |

## 2. Approval 与 Grant

| 决策点 | 决策 | 理由 | 风险控制 |
|---|---|---|---|
| Grant 来源 | 只允许 approved Approval 签发 | 防止绕过审批 | pending/rejected/expired/revoked 均测试拒绝 |
| 自审批 | 默认拒绝 | 避免 requester 单人批准高风险动作 | break_glass 留给真实 IAM 后续扩展 |
| 状态终态 | rejected/expired/revoked 为终态 | 审计事实不可反复改写 | 新申请使用新的 approval_id |
| Grant TTL | policy 配置，默认短期 | 运行时授权应限时 | 过期后不可 conditional_allow |

## 3. Evidence Vault

| 决策点 | 决策 | 理由 | 风险控制 |
|---|---|---|---|
| 摘要接口是否返回原文 | 永不返回 | PRD 红线：默认脱敏摘要，原文进 Vault 审批 | contract test 断言无 raw_payload |
| Raw access 返回形态 | 限时 access_state + audit，不返回 raw_payload | 当前阶段没有真实 Vault 后端 | 生产后端另行接入 |
| 脱敏失败 | 只保留 hash/摘要和告警 | 脱敏失败时不能以调试为由泄露原文 | `EVIDENCE_REDACTION_FAILED` 状态 |

## 4. Store/CLI 可解释摘要

阶段 2 的治理摘要必须帮助用户理解“谁要求、为什么、影响哪些动作、能否忽略、下一步是什么”。因此 `PolicyRequirement Summary` 必填：

- `required_by`
- `source`
- `issuer`
- `policy_owner`
- `policy_version`
- `can_ignore`
- `affected_actions`
- `deep_links`
- `plain_language`
- `primary_action`
- `secondary_action`

## 5. SLO 与降级

| 链路 | 阶段 2 阈值 | 告警 | 降级 |
|---|---|---|---|
| Policy Check | P95 <= 500ms，月可用性 >= 99.9% | P95 > 800ms 或错误率 > 1% | 高风险 require_online/block |
| Approval Service | 高风险审批通知 1 分钟内送达 | 超 SLA 未处理 | 自动提醒、升级审批人 |
| Evidence Query | P95 <= 2s | P95 > 3s | 原文查询失败回退脱敏摘要 |

缺失 SLO 数据时不得展示 healthy，必须展示 unknown/degraded 和 request_id。

## 6. 继承与非继承

- 继承 001 的 EventEnvelope、Evidence Summary、L5 Gate 和阶段 1 `evaluate_policy_decision` 兼容函数。
- 不继承 001 的阶段 1 “只降级不强治理”口径；阶段 2 对高风险 Policy Check 进入强 SLO。
- 不引入真实 IAM/HTTP/Postgres，避免在外部契约未稳定前扩大范围。
