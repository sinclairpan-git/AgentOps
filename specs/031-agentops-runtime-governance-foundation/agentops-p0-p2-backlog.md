# AgentOps P0-P2 需求归档

**归档所属工作项**：`031-agentops-runtime-governance-foundation`  
**归档日期**：2026-05-09  
**状态**：已归档，后续拆分需求时以本文为 AgentOps backlog 入口  
**来源 PRD**：

- `/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md`
- `/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Runtime_项目_PRD.md`
- `/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_AgentOps_AiSDLC_应用底座顶层规划_PRD.md`

## 1. 归档目的

本文统一归档 AgentOps 在新四项目边界下的 P0 / P1 / P2 需求池，避免后续阶段重新从 PRD 和讨论记录里归纳。后续创建新工作项时，优先从本文选取需求包并保留原编号。

边界再次确认：

```text
AgentOps 管治理、观测、证据、策略、审批、健康、评测、审计和回写；
AgentOps 不执行 Agent、不加载包、不调度 Tool/Model、不作为统一门户入口。
```

## 2. P0：最小受管治理闭环

P0 目标是打通一条可验证链路：

```text
Runtime / Ai_AutoSDLC 上报事实
  -> AgentOps 校验、接收、去重、降级
  -> 管理员查看 Run Detail / Trace Timeline
  -> 生成 EvidenceSummary / HealthSummary
  -> Policy / Grant / Approval 最小治理
  -> 回写 Agent Store 摘要
```

| 编号 | 需求包 | 目标 | 建议承接工作项 |
|---|---|---|---|
| AO-P0-01 | Contract / Schema Registry 最小治理 | 冻结 AgentOps 负责的 `PolicyDecision`、`CapabilityGrant`、`Approval`、`EvidenceSummary`、`HealthSummary`、`EvalCase` schema、Owner、错误码、状态枚举和 contract tests | 031 |
| AO-P0-02 | Runtime Ingestion API v1 | 接收 `RuntimeRun`、`TraceSpan`、`EventEnvelope`、Guardrail result、Artifact refs；校验 schema、签名、idempotency_key、sequence_no、source_trust、payload_hash | 031 |
| AO-P0-03 | Runtime Run Detail | 支持按 `session_id / run_id / step/span` 查看运行详情，展示状态、失败原因、policy 决策、guardrail、artifact 摘要 | 031 |
| AO-P0-04 | Trace Timeline | 展示 `agent / workflow / model / tool / retrieval / handoff / approval / guardrail / artifact / system` span 链路；缺失、待上报、降级有明确状态 | 031 |
| AO-P0-05 | EvidenceSummary 合成 | 输出 evidence_level、source_event_ids、freshness、valid_until、confidence、missing_dimensions、redaction_state、raw_access_state、degraded_reason | 后续 032 建议 |
| AO-P0-06 | HealthSummary 生成与 Store 回写 | 按窗口输出 success_rate、failure_rate、evidence_completeness、policy_block_count、recommended_action、valid_until，并回写 Store | 后续 032 建议 |
| AO-P0-07 | PolicyDecision API 最小版 | 支持 `allow / warn / approval_required / block / policy_unavailable`，返回 reason_code、policy_set_version、ttl、fallback_action、obligations | 后续 033 建议 |
| AO-P0-08 | CapabilityGrant 最小签发与审计 | Grant 绑定 agent/version/artifact/installation/device/user/session/run/skill/resource_scope，支持 TTL、remaining_uses、revoked/expired 审计 | 后续 033 建议 |
| AO-P0-09 | Guardrail 结果接入 | P0 只接收 Runtime / Ai_AutoSDLC 上报的 guardrail 结果与审计，不做复杂规则配置中心 | 可并入 031 或 033 |
| AO-P0-10 | Outbox / DLQ 接收语义 | 支持 Runtime / Reporter 重放，重复事件幂等忽略，乱序、签名失败、schema 拒绝进入可解释状态 | 031 + 后续 034 |
| AO-P0-11 | Agent Store 回显接口 | 向 Store 提供 EvidenceSummary、HealthSummary、recommended_action、ops_detail_url，摘要过期后必须返回 expired | 后续 032 建议 |
| AO-P0-12 | 权限与脱敏基线 | Run、Trace、Evidence 原文默认脱敏或引用 Evidence Vault；403 返回 reason_category、request_access_url、audit_id | 031 + 既有 023/012 |
| AO-P0-13 | P0 端到端验收 | 打通 Runtime 上报 -> Ops Run Detail/Timeline -> Evidence/Health Summary -> Store 回显 | 后续 P0 集成验收 |
| AO-P0-14 | Ai_AutoSDLC Trace 映射接入 | enterprise_managed 模式下，stage/gate/verification/artifact/violation 事件可映射为 Runtime TraceSpan / Evidence 输入 | 后续 034 建议 |

### 2.1 P0 不做

- 不做云端 Runtime、serverless hosting、容器弹性伸缩。
- 不做完整质量评分、ROI、采纳分析月报。
- 不做完整 replay、simulation、prompt optimizer。
- 不做完整 MCP/A2A Gateway。
- 不做 Agent Store 排行、评论、商业 marketplace。
- 不让 AgentOps 接管 Runtime 执行或 Store 包管理。

## 3. P1：稳定治理闭环

P1 目标是让 P0 闭环从“可证明”走向“可运营、可恢复、可评测”。

| 编号 | 需求包 | 目标 |
|---|---|---|
| AO-P1-01 | Approval Center 完整版 | 支持 pending、补充材料、approve、reject、expire、withdraw、SLA、通知、resume_token / pause_token |
| AO-P1-02 | Policy 管理台 | policy set 版本、灰度、回滚、risk template、fallback_action、deny 优先级解释 |
| AO-P1-03 | Grant 生命周期管理 | Grant 查询、吊销、过期、消耗、离线授权策略、影响范围分析 |
| AO-P1-04 | Evidence Vault 原文申请 | 原文访问申请、审批、审计、脱敏预览、raw_access_state |
| AO-P1-05 | EvalCase 基础闭环 | 失败 run 标记为待沉淀样本，生成 EvalCase，支持基础 scorer 和版本对比 |
| AO-P1-06 | 成本 / token / latency 预算 | 从 TraceSpan 汇总 token_usage、cost_estimate、latency，形成 budget 和 SLO 视图 |
| AO-P1-07 | DLQ 运维台 | 查看积压、失败原因、重放、丢弃、schema 兼容拒绝说明 |
| AO-P1-08 | OTLP / OpenInference Exporter | 对接外部观测系统，但不改变内部事实源模型 |
| AO-P1-09 | Runtime SLO 运营 | Runtime trace 延迟、ingestion backlog、policy latency、approval SLA、evidence freshness 统一监控 |
| AO-P1-10 | Store 回显治理升级 | 支持摘要申诉、替代版本建议、Owner 通知、禁用建议状态闭环 |
| AO-P1-11 | 失败样本沉淀 | 从 blocked/failed/degraded run 中选择样本，标注 privacy_class、owner_team、expected_behavior |
| AO-P1-12 | 基础 scorer 管理 | 支持 deterministic scorer、人工复核、版本对比，不进入自动优化 |

## 4. P2：生态与优化

P2 目标是进入更完整的 AgentOps 优化平台，但必须以 P0/P1 治理可信为前提。

| 编号 | 需求包 | 目标 |
|---|---|---|
| AO-P2-01 | Safe Replay / Simulation | 对历史 Trace 做安全回放、沙箱模拟和回归验证 |
| AO-P2-02 | Prompt / Model / Tool Experiment | 支持实验分组、对照、优化建议 |
| AO-P2-03 | MCP / A2A 治理 | 外部工具和多 Agent 通信必须经 Runtime Gateway / Policy Check 后进入受管证据 |
| AO-P2-04 | 完整质量评分引擎 | 从 HealthSummary 升级到多维质量评分、置信度、模板、月报 |
| AO-P2-05 | Adoption / ROI 分析 | 采纳率、返工率、人工节省、团队趋势 |
| AO-P2-06 | 多 exporter 生态 | OTLP、OpenInference、第三方 APM、数据湖导出 |
| AO-P2-07 | Optimizer | 基于 EvalCase / Replay / Experiment 的 prompt、model、tool 策略优化建议 |
| AO-P2-08 | 多 Agent handoff 评测 | 跨 Agent handoff 链路质量、责任归因、失败回放 |
| AO-P2-09 | 复杂风险画像 | 跨团队、跨 Agent、跨数据域的长期风险趋势和异常检测 |
| AO-P2-10 | 治理策略仿真 | 在发布前模拟 policy / grant / approval 变更影响范围 |

## 5. 推荐后续工作项拆分

| 建议工作项 | 覆盖需求 | 说明 |
|---|---|---|
| 031 Runtime Governance Foundation | AO-P0-01、AO-P0-02、AO-P0-03、AO-P0-04，部分 AO-P0-09/10/12 | 当前工作项，先打地基 |
| 032 Evidence and Health Summary Loop | AO-P0-05、AO-P0-06、AO-P0-11、AO-P0-13 | 让 Ops 结论能回写 Store |
| 033 Policy Grant Approval Minimum Control | AO-P0-07、AO-P0-08、AO-P0-09 | 最小策略、授权、审批控制 |
| 034 Runtime Outbox and SDLC Trace Bridge | AO-P0-10、AO-P0-14 | Runtime / Ai_AutoSDLC 上报可靠性与映射 |
| 035 P0 End-to-End Acceptance Gate | AO-P0-13 | 串起 P0 完整验收，不新增大功能 |
| P1-A Approval / Policy / Grant Operations | AO-P1-01 到 AO-P1-03 | 稳定治理操作面 |
| P1-B Evidence / Eval / Cost Operations | AO-P1-04 到 AO-P1-12 | 证据、评测、成本与 SLO |
| P2-A Replay / Simulation / Optimizer | AO-P2-01、AO-P2-02、AO-P2-07、AO-P2-10 | 优化与仿真 |
| P2-B Ecosystem Governance | AO-P2-03、AO-P2-06、AO-P2-08、AO-P2-09 | MCP/A2A、多 exporter、多 Agent 风险 |

## 6. 归档使用规则

1. 后续新建 AgentOps 工作项时，必须先从本文选择需求包编号，不重新发明编号。
2. 若新增需求不在本文，先追加到本文并标注来源，再进入 spec。
3. 若需求阶段发生变化，更新本文的 P0/P1/P2 分层，并在对应工作项 `task-execution-log.md` 记录原因。
4. 任何 P2 能力不得绕过 P0/P1 的证据、权限、脱敏和 contract test 基线。
5. 若与 PRD 冲突，以顶层 PRD 第 14 章和 AgentOps PRD 第 16 章为准，并同步修订本文。
