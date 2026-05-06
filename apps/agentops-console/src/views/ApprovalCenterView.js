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
        { key: "approval_id", label: "Approval" },
        { key: "requester", label: "Requester" },
        { key: "affected_actions", label: "Actions" },
        { key: "sla_due_at", label: "SLA" },
        { key: "status", label: "Status", type: "status" },
        { key: "grant_status", label: "Grant", type: "status" },
        { key: "audit_id", label: "Audit" }
      ]
    };
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">Human control</p><h3>Approval Center</h3></div>
        <p class="heading-copy">Approval state, SLA and grant status stay tied to the original policy request.</p>
      </section>
      <data-table :columns="columns" :rows="data.approvals" />
    </div>
  `
};
