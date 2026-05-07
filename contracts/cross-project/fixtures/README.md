# Cross-Project Contract Fixtures

These fixtures mirror Agent Store 008 at source commit `b6c3aef08102eb6352e9904001adffd23b95a7ba` and freeze the shared field names for Agent Store, AgentOps, and Ai_AutoSDLC contract tests.

- `signed_installation_assertion.v1.json` is produced by Agent Store.
- `agentops_credential_handoff.v1.json` is consumed by AgentOps and assembled from Agent Store assertion data plus Ai_AutoSDLC device proof data.
- `device_proof.v1.json` is stored here only for cross-project contract tests. Ai_AutoSDLC is the producer; AgentOps consumes and validates it.
- `credential_issue_response.v1.json` is produced by AgentOps and consumed by Agent Store.
- `unsupported_schema.v2.json` is a negative fixture for unknown major versions.

## Source Checksums

- `agentops_credential_handoff.v1.json`: `d26a2240a2a24d89d20cf9253f59e621cad411c922a659b9a04aca465f869fa0`
- `credential_issue_response.v1.json`: `63004beb528db22f1863b035999ef4892c517bd7e5a13b229d59039f8cbad464`
- `device_proof.v1.json`: `ed740715d1afd316671b341e265826679e2a9d0f39d4eb6a6b5ff5b6fca41425`
- `signed_installation_assertion.v1.json`: `aabd5734cbea3e24887e67737c7dc6dcedb6facd4e8024520e34b9ebacc0db9f`
- `unsupported_schema.v2.json`: `3527a26fe64a76d449ac9d00b472200247e2207771b30eb8a68f61ca394778b4`
