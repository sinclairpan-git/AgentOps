const labels = {
  healthy: "Healthy",
  allow: "Allow",
  conditional_allow: "Conditional",
  warn: "Warn",
  approval_required: "Approval",
  block: "Block",
  degraded: "Degraded",
  unknown: "Unknown",
  pending: "Pending",
  needs_more_info: "More Info",
  approved: "Approved",
  rejected: "Rejected",
  expired: "Expired",
  revoked: "Revoked",
  escalated: "Escalated",
  summary_only: "Summary",
  pending_approval: "Pending",
  approved_limited: "Limited",
  redaction_failed: "Redaction Failed",
  permission_denied: "Denied",
  materialized: "Materialized",
  verified_loaded: "Verified Loaded",
  unsupported: "Unsupported",
  dry_run_passed: "Dry Run Passed",
  unverified: "Unverified"
};

export const StatusBadge = {
  name: "StatusBadge",
  props: {
    status: { type: String, required: true }
  },
  computed: {
    label() {
      return labels[this.status] || this.status;
    },
    tone() {
      if (["healthy", "allow", "approved", "verified_loaded"].includes(this.status)) return "good";
      if (["block", "rejected", "revoked", "redaction_failed", "permission_denied"].includes(this.status)) return "bad";
      if (["degraded", "unknown", "expired", "unsupported", "unverified"].includes(this.status)) return "warn";
      return "info";
    }
  },
  template: `<span class="status-badge" :class="'status-badge--' + tone">{{ label }}</span>`
};
