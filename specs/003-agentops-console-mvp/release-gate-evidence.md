# AgentOps Console MVP Release Gate Evidence

**功能编号**：`003-agentops-console-mvp`  
**采集时间**：2026-05-06T04:50:00Z  
**允许裁决值**：PASS/WARN/BLOCK

```json
{
  "release_gate_evidence": {
    "overall_verdict": "PASS",
    "checks": [
      {
        "name": "recoverability",
        "verdict": "PASS",
        "evidence_source": "specs/003-agentops-console-mvp/development-summary.md",
        "reason": "Console MVP 使用 mock data adapter 和企业 Vue2 Provider shim，可在不依赖真实后端或企业 registry 的情况下恢复本地运行；dry-run 不被声明为 verified_loaded。"
      },
      {
        "name": "portability",
        "verdict": "PASS",
        "evidence_source": "GitHub Actions AgentOps Cross Platform / Compatibility Gate Result",
        "reason": "PR #1 的 Windows、Linux、macOS 后端和前端矩阵已通过，后续主线由 main-compatibility-gate 继续要求 Compatibility Gate Result。"
      },
      {
        "name": "multi_ide",
        "verdict": "PASS",
        "evidence_source": "docs/engineering/github-branch-governance.md",
        "reason": "仓库主线治理不依赖单一 IDE，本地 Codex、Windows Codex 与 GitHub PR 检查均通过同一 main ruleset 和云端门禁衔接。"
      },
      {
        "name": "stability",
        "verdict": "PASS",
        "evidence_source": "specs/003-agentops-console-mvp/evidence/browser-gate/browser-gate-result.json",
        "reason": "npm test、npm run build、uv run pytest tests -q、uv run ruff check src tests 与桌面/移动浏览器 gate 均通过，Vue runtime-only 渲染阻断已修复。"
      }
    ]
  }
}
```
