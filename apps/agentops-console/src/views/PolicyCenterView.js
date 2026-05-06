import { DataTable } from "../components/DataTable.js";

export const PolicyCenterView = {
  name: "PolicyCenterView",
  components: {
    DataTable
  },
  props: {
    data: { type: Object, required: true }
  },
  data() {
    return {
      columns: [
        { key: "decision", label: "Decision", type: "status" },
        { key: "action", label: "Action" },
        { key: "fallback_action", label: "Fallback" },
        { key: "policy_version", label: "Version" },
        { key: "grant_ttl", label: "Grant TTL" },
        { key: "audit_id", label: "Audit" }
      ]
    };
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">Runtime policy</p><h3>Policy Center</h3></div>
        <p class="heading-copy">Deny and block states stay higher priority than active grants. Unknown high-risk policy does not render as allow.</p>
      </section>
      <data-table :columns="columns" :rows="data.policies" />
    </div>
  `
};
