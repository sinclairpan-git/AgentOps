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
        { key: "decision", label: "裁决", type: "status" },
        { key: "action", label: "动作" },
        { key: "fallback_action", label: "降级动作" },
        { key: "policy_version", label: "版本" },
        { key: "grant_ttl", label: "Grant TTL" },
        { key: "audit_id", label: "审计" }
      ]
    };
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">运行策略</p><h3>策略中心</h3></div>
        <p class="heading-copy">拒绝/阻断优先级高于已生效 Grant（deny/block）；高风险未知状态不会显示为允许。</p>
      </section>
      <data-table :columns="columns" :rows="data.policies" />
    </div>
  `
};
