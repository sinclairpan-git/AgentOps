"""Approval lifecycle constants."""

APPROVAL_STATUSES = {
    "pending",
    "approved",
    "rejected",
    "needs_more_info",
    "expired",
    "escalated",
    "revoked",
}

APPROVAL_TERMINAL_STATUSES = {"approved", "rejected", "expired", "revoked"}

APPROVAL_ACTION_TO_STATUS = {
    "approve": "approved",
    "reject": "rejected",
    "request_more_info": "needs_more_info",
    "expire": "expired",
    "escalate": "escalated",
    "revoke": "revoked",
}
