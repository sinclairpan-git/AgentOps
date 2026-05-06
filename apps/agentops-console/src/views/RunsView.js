import { DataTable } from "../components/DataTable.js";

export const RunsView = {
  name: "RunsView",
  components: {
    DataTable
  },
  props: {
    data: { type: Object, required: true }
  },
  data() {
    return {
      columns: [
        { key: "run_id", label: "Run" },
        { key: "agent", label: "Agent" },
        { key: "skill", label: "Skill" },
        { key: "risk_level", label: "Risk" },
        { key: "l5_state", label: "L5 Gate", type: "status" },
        { key: "policy_state", label: "Policy", type: "status" },
        { key: "evidence_state", label: "Evidence", type: "status" }
      ]
    };
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">Runtime facts</p><h3>Runs</h3></div>
        <p class="heading-copy">Each run keeps L5, policy and evidence state visible. Unknown states never collapse into healthy.</p>
      </section>
      <data-table :columns="columns" :rows="data.runs" />
    </div>
  `
};
