# Cross-Project Contract Fixtures

These fixtures mirror Agent Store 008 and freeze the shared field names for Agent Store, AgentOps, and Ai_AutoSDLC contract tests.

- `signed_installation_assertion.v1.json` is produced by Agent Store.
- `agentops_credential_handoff.v1.json` is consumed by AgentOps and assembled from Agent Store assertion data plus Ai_AutoSDLC device proof data.
- `device_proof.v1.json` is stored here only for cross-project contract tests. Ai_AutoSDLC is the producer; AgentOps consumes and validates it.
- `credential_issue_response.v1.json` is produced by AgentOps and consumed by Agent Store.
- `unsupported_schema.v2.json` is a negative fixture for unknown major versions.
