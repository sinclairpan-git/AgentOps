"""Approval lifecycle constants."""

APPROVAL_STATUSES = {
    "pending",
    "approved",
    "rejected",
    "needs_input",
    "needs_more_info",
    "expired",
    "escalated",
    "revoked",
    "withdrawn",
}

APPROVAL_TERMINAL_STATUSES = {
    "approved",
    "rejected",
    "expired",
    "revoked",
    "withdrawn",
}

APPROVAL_ACTION_TO_STATUS = {
    "approve": "approved",
    "reject": "rejected",
    "request_input": "needs_input",
    "request_more_info": "needs_more_info",
    "expire": "expired",
    "escalate": "escalated",
    "revoke": "revoked",
    "withdraw": "withdrawn",
}
