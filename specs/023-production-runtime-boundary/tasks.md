# 任务：023 Production Runtime Boundary

| Task | 状态 | 内容 |
| --- | --- | --- |
| T23-01 | 完成 | 建立 023 规格、计划、任务和执行日志，冻结生产运行边界契约。 |
| T23-02 | 完成 | 新增上游身份/角色/scope 解析和 production auth policy。 |
| T23-03 | 完成 | 将 HTTP server 写接口与敏感读接口接入 production auth gate。 |
| T23-04 | 完成 | 补 frontend generation `recipe.yaml` / `exceptions.yaml` 并恢复 `ai-sdlc program status`。 |
| T23-05 | 完成 | 新增 AO23 契约测试并回归 AO4/AO18/AO22。 |
| T23-06 | 完成 | 执行全量验证、AI-SDLC close-check、提交、PR 和 Codex review 轮询。 |

## 验收

- AO23-CT-001 到 AO23-CT-008 全部通过。
- 本地默认模式保持兼容，生产模式显式启用鉴权。
- `program status` 不再因 frontend generation artifacts 缺失崩溃。
