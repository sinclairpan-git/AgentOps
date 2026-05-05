"""Policy decision models."""

HIGH_RISK_ACTIONS = {"write", "execute", "network", "deploy", "config_change"}

POLICY_PRIORITY_DENIES = [
    "global_deny",
    "iam_or_security_deny",
    "project_scope_deny",
    "agent_or_version_disabled",
    "policy_block",
]

POLICY_DECISIONS = {"block", "approval_required", "warn", "conditional_allow", "allow"}
FALLBACK_ACTIONS = {"allow", "warn", "require_online", "block"}
