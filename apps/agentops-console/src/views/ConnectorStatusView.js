import { DataTable } from "../components/DataTable.js";

export const ConnectorStatusView = {
  name: "ConnectorStatusView",
  components: {
    DataTable
  },
  props: {
    data: { type: Object, required: true }
  },
  data() {
    return {
      columns: [
        { key: "name", label: "Connector" },
        { key: "status", label: "Status", type: "status" },
        { key: "last_seen_at", label: "Last Seen" },
        { key: "degrade_action", label: "Degrade Action" },
        { key: "request_id", label: "Request" }
      ]
    };
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">Integrations</p><h3>Connector Status</h3></div>
        <p class="heading-copy">Connector health explains impact and fallback behavior before operators touch a run.</p>
      </section>
      <data-table :columns="columns" :rows="data.connectors" />
    </div>
  `
};
