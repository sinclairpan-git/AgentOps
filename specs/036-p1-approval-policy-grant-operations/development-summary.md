# 开发总结：P1 Approval Policy Grant Operations

**工作项**：`036-p1-approval-policy-grant-operations`  
**日期**：2026-05-10  
**状态**：formal baseline 已创建

## 变更摘要

- 新增 AO36 canonical work item，承接 P1-A：Approval Center 完整版、Policy 管理台、Grant 生命周期管理。
- 冻结 `spec.md`、`plan.md`、`tasks.md`，明确 P1 操作面只管理治理事实、版本、状态、审计和摘要。
- `program-manifest.yaml` 已由 `ai-sdlc workitem init` 物化 036 映射，并完成 program truth sync。

## 边界确认

- AgentOps 不执行 Runtime、不调度 Agent、不发送真实通知。
- Policy operations 只登记和解释 policy set 版本，不替代外部 IAM/Policy 引擎。
- Grant lifecycle 不绕过 approval binding，不扩大 resource_scope。
- 所有 P1 projection 不暴露 raw payload、prompt、token secret、credential secret、device key 或 Evidence Vault 原文。

## 下一步

- T12：已登记 P1 governance operations contracts，并新增 AO36 registry contract tests。
- T21：已实现 Approval operations 状态机基础，包括补材料、升级、撤回和 break-glass 审计。
- T31：已实现 Policy set version operations projection，覆盖 canary、active、rollback 和 deny priority 解释。
- T41：已实现 Grant lifecycle query/revoke/impact summary，覆盖 consumption、binding、revocation metadata 和离线授权影响提示。
- T51：运行 AO36 + AO2/AO13/AO33/AO35 回归、ruff、AI-SDLC constraints，并进入 PR 收口。
