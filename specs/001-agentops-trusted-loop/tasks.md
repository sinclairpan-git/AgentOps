---
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_AgentOps_AiSDLC_应用底座顶层规划_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
---
# 任务分解：AgentOps 可信最小闭环

**编号**：`001-agentops-trusted-loop`  
**日期**：2026-05-05  
**来源**：`spec.md` + `plan.md` + `research.md` + `data-model.md` + `contracts/*`

## 分批策略

```text
Batch 1: contract baseline and project scaffold
Batch 2: ingestion, evidence, and L5 evaluator
Batch 3: bootstrap credentials and Store summary
Batch 4: policy degradation, admin view models, and close verification
```

## 完成状态

| 任务 | 状态 | 验证 |
|---|---|---|
| T11 | 已完成 | `ai-sdlc gate refine`、`ai-sdlc gate design`、对抗评审通过 |
| T12 | 已完成 | `uv run pytest tests -q` |
| T21 | 已完成 | `uv run pytest tests/contract/test_ao_ct_001_event_envelope.py tests/contract/test_ao_ct_006_integration_mode.py -q` |
| T22 | 已完成 | `uv run pytest tests/unit/test_l5_gate.py tests/contract/test_ao_ct_003_evidence_summary.py -q` |
| T31 | 已完成 | `uv run pytest tests/contract/test_ao_ct_002_credential_issue.py -q` |
| T32 | 已完成 | `uv run pytest tests/contract/test_ao_ct_005_store_summary.py -q` |
| T41 | 已完成 | `uv run pytest tests/contract/test_ao_ct_004_policy_decision.py -q` |
| T42 | 已完成 | `uv run pytest tests/unit/test_admin_view_models.py -q` |
| T43 | 已完成 | `uv run pytest tests -q`、`ai-sdlc verify constraints` |

## Batch 1：contract baseline and project scaffold

### Task 1.1 冻结规格与契约基线

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：
  - `/Users/sinclairpan/project/AgentOps/specs/001-agentops-trusted-loop/spec.md`
  - `/Users/sinclairpan/project/AgentOps/specs/001-agentops-trusted-loop/research.md`
  - `/Users/sinclairpan/project/AgentOps/specs/001-agentops-trusted-loop/data-model.md`
  - `/Users/sinclairpan/project/AgentOps/specs/001-agentops-trusted-loop/contracts/event-envelope-v1.schema.yaml`
  - `/Users/sinclairpan/project/AgentOps/specs/001-agentops-trusted-loop/contracts/agentops-api.openapi.yaml`
  - `/Users/sinclairpan/project/AgentOps/specs/001-agentops-trusted-loop/contracts/contract-tests.md`
- **可并行**：否
- **验收标准**：
  1. `ai-sdlc gate refine` 通过。
  2. `ai-sdlc gate design` 通过。
  3. 两个对抗评审 agent 无 P0/P1 阻断。
- **验证**：`ai-sdlc gate refine && ai-sdlc gate design`

### Task 1.2 建立 Python 3.11 服务与测试骨架

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：
  - `/Users/sinclairpan/project/AgentOps/pyproject.toml`
  - `/Users/sinclairpan/project/AgentOps/src/agentops/__init__.py`
  - `/Users/sinclairpan/project/AgentOps/src/agentops/api/app.py`
  - `/Users/sinclairpan/project/AgentOps/tests/contract/conftest.py`
  - `/Users/sinclairpan/project/AgentOps/tests/unit/conftest.py`
- **可并行**：否
- **验收标准**：
  1. 项目可安装并运行 pytest。
  2. Contract test 目录存在且能加载 fixtures。
- **验证**：`python -m pytest tests -q`

## Batch 2：ingestion, evidence, and L5 evaluator

### Task 2.1 实现 EventEnvelope schema 与 Ingestion 幂等

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T12
- **文件**：
  - `/Users/sinclairpan/project/AgentOps/src/agentops/core/envelope.py`
  - `/Users/sinclairpan/project/AgentOps/src/agentops/core/idempotency.py`
  - `/Users/sinclairpan/project/AgentOps/src/agentops/core/signature.py`
  - `/Users/sinclairpan/project/AgentOps/src/agentops/api/ingestion.py`
  - `/Users/sinclairpan/project/AgentOps/tests/contract/test_ao_ct_001_event_envelope.py`
  - `/Users/sinclairpan/project/AgentOps/tests/contract/test_ao_ct_006_integration_mode.py`
- **可并行**：否
- **验收标准**：
  1. enterprise_managed 缺 signature 返回 `EVENT_SIGNATURE_REQUIRED`。
  2. 重复 idempotency_key 不重复写核心事实。
  3. standalone/custom_sink/unknown 按契约降级或拒绝。
- **验证**：`python -m pytest tests/contract/test_ao_ct_001_event_envelope.py tests/contract/test_ao_ct_006_integration_mode.py -q`

### Task 2.2 实现 Evidence Summary 与 L5 Gate

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T21
- **文件**：
  - `/Users/sinclairpan/project/AgentOps/src/agentops/core/l5_gate.py`
  - `/Users/sinclairpan/project/AgentOps/src/agentops/core/evidence.py`
  - `/Users/sinclairpan/project/AgentOps/src/agentops/core/redaction.py`
  - `/Users/sinclairpan/project/AgentOps/src/agentops/api/evidence.py`
  - `/Users/sinclairpan/project/AgentOps/tests/unit/test_l5_gate.py`
  - `/Users/sinclairpan/project/AgentOps/tests/contract/test_ao_ct_003_evidence_summary.py`
- **可并行**：可与 T31 之后的 Store Summary view model 部分并行，但不得改同文件
- **验收标准**：
  1. 完整 run 可判定 L5。
  2. 缺 fresh verification 或 governance degraded 不得判 L5。
  3. Evidence Summary 默认只返回脱敏摘要和 raw_access_state。
- **验证**：`python -m pytest tests/unit/test_l5_gate.py tests/contract/test_ao_ct_003_evidence_summary.py -q`

## Batch 3：bootstrap credentials and Store summary

### Task 3.1 实现 Bootstrap Credential API

- **任务编号**：T31
- **优先级**：P0
- **依赖**：T12
- **文件**：
  - `/Users/sinclairpan/project/AgentOps/src/agentops/models/credentials.py`
  - `/Users/sinclairpan/project/AgentOps/src/agentops/api/credentials.py`
  - `/Users/sinclairpan/project/AgentOps/tests/contract/test_ao_ct_002_credential_issue.py`
- **可并行**：可与 T21 并行，写集不重叠
- **验收标准**：
  1. active bootstrap 签发 ReporterCredential、IngestionToken、DeviceKey。
  2. 过期 bootstrap 返回 `BOOTSTRAP_EXPIRED`。
  3. 同 bootstrap_id 重试返回同 credential 状态。
- **验证**：`python -m pytest tests/contract/test_ao_ct_002_credential_issue.py -q`

### Task 3.2 实现 Agent Store Summary API

- **任务编号**：T32
- **优先级**：P1
- **依赖**：T22
- **文件**：
  - `/Users/sinclairpan/project/AgentOps/src/agentops/api/store_summary.py`
  - `/Users/sinclairpan/project/AgentOps/src/agentops/models/evidence.py`
  - `/Users/sinclairpan/project/AgentOps/tests/contract/test_ao_ct_005_store_summary.py`
- **可并行**：否
- **验收标准**：
  1. 返回 score_template_id、evidence_level、confidence、missing_evidence、risk_state、approval_state、calculated_at、valid_until、deep_links。
  2. schema 不兼容返回 `SUMMARY_SCHEMA_UNSUPPORTED`。
  3. 不返回未脱敏原文。
- **验证**：`python -m pytest tests/contract/test_ao_ct_005_store_summary.py -q`

## Batch 4：policy degradation, admin view models, and close verification

### Task 4.1 实现 PolicyDecision 阶段 1 降级口径

- **任务编号**：T41
- **优先级**：P1
- **依赖**：T12
- **文件**：
  - `/Users/sinclairpan/project/AgentOps/src/agentops/models/policy.py`
  - `/Users/sinclairpan/project/AgentOps/src/agentops/api/policy.py`
  - `/Users/sinclairpan/project/AgentOps/tests/contract/test_ao_ct_004_policy_decision.py`
- **可并行**：可与 T32 并行，写集不重叠
- **验收标准**：
  1. 缺 resource_scope 返回 `POLICY_SCOPE_REQUIRED`。
  2. 高风险 policy_unknown 默认 require_online/block。
  3. decision 输出 audit_id、policy_version、fallback_action。
- **验证**：`python -m pytest tests/contract/test_ao_ct_004_policy_decision.py -q`

### Task 4.2 定义管理员页面 view model 与状态快照

- **任务编号**：T42
- **优先级**：P1
- **依赖**：T22
- **文件**：
  - `/Users/sinclairpan/project/AgentOps/src/agentops/api/view_models.py`
  - `/Users/sinclairpan/project/AgentOps/tests/unit/test_admin_view_models.py`
- **可并行**：否
- **验收标准**：
  1. Overview、Runs、Evidence Explorer、Risk Triage、Approval Center、Policy Center、Quality Center、Connector Status 均覆盖 pending/degraded/failed/empty/permission_denied。
  2. 每个状态包含 primary_action、secondary_action、owner_hint、audit_id/request_id。
  3. 权限失败状态不包含未脱敏原文。
- **验证**：`python -m pytest tests/unit/test_admin_view_models.py -q`

### Task 4.3 收尾验证与执行日志

- **任务编号**：T43
- **优先级**：P0
- **依赖**：T21、T22、T31、T32、T41、T42
- **文件**：
  - `/Users/sinclairpan/project/AgentOps/specs/001-agentops-trusted-loop/task-execution-log.md`
  - `/Users/sinclairpan/project/AgentOps/specs/001-agentops-trusted-loop/tasks.md`
- **可并行**：否
- **验收标准**：
  1. 所有 contract tests 通过。
  2. `ai-sdlc verify constraints` 无 BLOCKER。
  3. 执行日志记录命令、结果、证据路径和未解决风险。
- **验证**：`python -m pytest tests -q && ai-sdlc verify constraints`
