import { DataTable } from "../components/DataTable.js";

export const SdlcRunsView = {
  name: "SdlcRunsView",
  components: {
    DataTable
  },
  props: {
    data: { type: Object, required: true }
  },
  data() {
    return {
      columns: [
        { key: "command", label: "Command" },
        { key: "adapter_status", label: "Adapter", type: "status" },
        { key: "dry_run_status", label: "Dry Run", type: "status" },
        { key: "verified_loaded", label: "Governance Proof", type: "status" },
        { key: "proof_source", label: "Proof Source" },
        { key: "captured_at", label: "Captured" }
      ]
    };
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">AI-SDLC proof</p><h3>Ai_AutoSDLC Runs</h3></div>
        <p class="heading-copy">CLI dry-run can pass while adapter governance is still materialized or unverified. Only machine-verifiable evidence becomes verified_loaded.</p>
      </section>
      <data-table :columns="columns" :rows="data.sdlcRuns" />
    </div>
  `
};
