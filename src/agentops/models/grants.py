"""Capability Grant constants."""

GRANT_STATUSES = {"active", "expired", "revoked"}

GRANT_BINDING_FIELDS = (
    "policy_check_id",
    "action",
    "requester",
    "agent_id",
    "skill_id",
    "resource_scope",
    "policy_version",
)

GRANT_CONTEXT_FIELDS = (
    "version",
    "artifact_hash",
    "installation_id",
    "device_id",
    "user_id",
    "session_id",
    "run_id",
)
