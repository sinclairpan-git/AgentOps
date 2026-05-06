import { DataTable } from "../components/DataTable.js";

export const ApprovalCenterView = {
  name: "ApprovalCenterView",
  components: {
    DataTable
  },
  props: {
    data: { type: Object, required: true }
  },
  data() {
    return {
      columns: [
        { key: "approval_id", label: "审批" },
        { key: "requester", label: "申请方" },
        { key: "affected_actions", label: "影响动作" },
        { key: "sla_due_at", label: "SLA" },
        { key: "status", label: "状态", type: "status" },
        { key: "grant_status", label: "Grant", type: "status" },
        { key: "audit_id", label: "审计" }
      ]
    };
  },
  methods: {
    openApproval(row) {
      this.$emit("open-action-detail", `action_approval_${row.approval_id}`);
    }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">人工控制</p><h3>审批中心</h3></div>
        <p class="heading-copy">审批状态、SLA 和 Grant 状态始终绑定原始策略请求。</p>
      </section>
      <data-table :columns="columns" :rows="data.approvals" row-action-label="查看处置" @row-action="openApproval" />
    </div>
  `
};
