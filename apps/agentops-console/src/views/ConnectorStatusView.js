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
        { key: "name", label: "连接器" },
        { key: "status", label: "状态", type: "status" },
        { key: "last_seen_at", label: "最后心跳" },
        { key: "degrade_action", label: "降级动作" },
        { key: "request_id", label: "请求" }
      ]
    };
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">集成状态</p><h3>连接器状态</h3></div>
        <p class="heading-copy">连接器健康状态会在运营人员处理运行前说明影响范围和降级行为。</p>
      </section>
      <data-table :columns="columns" :rows="data.connectors" />
    </div>
  `
};
