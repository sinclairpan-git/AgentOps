const labels = {
  healthy: "健康",
  allow: "允许",
  conditional_allow: "条件允许",
  warn: "警告",
  approval_required: "需审批",
  block: "阻断",
  blocked: "已阻断",
  created: "已创建",
  succeeded: "成功",
  failed: "失败",
  cancelled: "已取消",
  timeout: "超时",
  approval_paused: "审批暂停",
  trace_pending: "轨迹待补齐",
  running: "运行中",
  ok: "成功",
  error: "错误",
  unset: "未设置",
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
  ready: "就绪",
  insufficient_data: "数据不足",
  watching: "观察中",
  needs_review: "需复核",
  critical: "严重",
  insufficient_evidence: "证据不足",
  review_required: "需复核",
  disable_review_recommended: "建议禁用复核",
  ready_for_manual_approval: "待人工审批",
  needs_human_review: "需人工复核",
  candidate: "候选",
  draft: "草稿",
  retired: "已退役",
  neutral: "中性",
  improved: "改善",
  negative: "负向",
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
      if (["healthy", "allow", "approved", "verified_loaded", "governed", "registered", "normal", "succeeded", "ok", "ready", "improved"].includes(this.status)) return "good";
      if (["block", "blocked", "failed", "timeout", "error", "rejected", "revoked", "redaction_failed", "permission_denied", "critical", "negative"].includes(this.status)) return "bad";
      if (["degraded", "unknown", "expired", "unsupported", "unverified", "suspected", "unregistered", "warning", "not_asserted", "cancelled", "needs_review", "needs_human_review", "disable_review_recommended"].includes(this.status)) return "warn";
      return "info";
    }
  },
  template: `<span class="status-badge" :class="'status-badge--' + tone">{{ label }}</span>`
};
