import { DataTable } from "../components/DataTable.js";

export const QualityCenterView = {
  name: "QualityCenterView",
  components: {
    DataTable
  },
  props: {
    data: { type: Object, required: true }
  },
  data() {
    return {
      columns: [
        { key: "signal_id", label: "Signal" },
        { key: "category", label: "Category" },
        { key: "status", label: "Status", type: "status" },
        { key: "score", label: "Score" },
        { key: "evidence_ref", label: "Evidence" },
        { key: "owner_hint", label: "Owner" },
        { key: "primary_action", label: "Action" }
      ]
    };
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">Quality governance</p><h3>Quality Center</h3></div>
        <p class="heading-copy">Quality signals make contract coverage, browser gate readiness and evidence completeness operational.</p>
      </section>
      <data-table :columns="columns" :rows="data.quality" />
    </div>
  `
};
