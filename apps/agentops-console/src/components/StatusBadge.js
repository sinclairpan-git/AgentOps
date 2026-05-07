const labels = {
  healthy: "健康",
  allow: "允许",
  conditional_allow: "条件允许",
  warn: "警告",
  approval_required: "需审批",
  block: "阻断",
  degraded: "降级",
  unknown: "未知",
  empty: "暂无数据",
  pending: "待处理",
  needs_more_info: "需补充",
  approved: "已批准",
  rejected: "已拒绝",
  expired: "已过期",
  revoked: "已撤销",
  escalated: "已升级",
  active: "生效中",
  consumed: "已消费",
  summary_only: "仅摘要",
  pending_approval: "审批中",
  approved_limited: "限时批准",
  redaction_failed: "脱敏失败",
  permission_denied: "无权限",
  materialized: "已生成配置",
  verified_loaded: "已验证加载",
  unsupported: "不支持",
  dry_run_passed: "预演通过",
  unverified: "未验证",
  suspected: "疑似异常",
  governed: "已治理",
  registered: "已注册",
  unregistered: "未注册",
  normal: "正常",
  warning: "需关注",
  authenticated: "已认证",
  credential_issued: "凭证已签发",
  signature_verified: "签名已验证",
  not_asserted: "未声明"
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
      if (["healthy", "allow", "approved", "verified_loaded", "governed", "registered", "normal"].includes(this.status)) return "good";
      if (["block", "rejected", "revoked", "redaction_failed", "permission_denied"].includes(this.status)) return "bad";
      if (["degraded", "unknown", "expired", "unsupported", "unverified", "suspected", "unregistered", "warning", "not_asserted"].includes(this.status)) return "warn";
      return "info";
    }
  },
  template: `<span class="status-badge" :class="'status-badge--' + tone">{{ label }}</span>`
};
