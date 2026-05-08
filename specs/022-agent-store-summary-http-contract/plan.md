# 计划：022 Agent Store Summary HTTP Contract

1. 建立 `022-agent-store-summary-http-contract` 规格、计划、任务、执行日志和开发摘要。
2. 扩展 Agent Store summary 核心模型，补 `agentops_fact_owner`、display-only boundary、allowed/forbidden actions 和 redaction metadata。
3. 新增 HTTP route `GET /v1/store-summary/{agent_id}`，从 repository run events 计算 evidence summary，并复用现有 echo summary builder。
4. 更新 OpenAPI path/query/schema，明确 `version`、`run_id`、`schema_version` 和 error response。
5. 补 AO22 契约测试，覆盖成功、缺参、unsupported schema、run mismatch、缺失 L5 evidence 和敏感字段隔离。
6. 执行统一验证、AI-SDLC constraints、program validate、truth sync 和 close-check。
