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
        { key: "run_id", label: "运行" },
        { key: "agent", label: "Agent" },
        { key: "skill", label: "Skill" },
        { key: "risk_level", label: "风险" },
        { key: "l5_state", label: "L5 Gate", type: "status" },
        { key: "policy_state", label: "策略", type: "status" },
        { key: "evidence_state", label: "证据", type: "status" }
      ]
    };
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">运行事实</p><h3>运行记录</h3></div>
        <p class="heading-copy">每条运行都展示 L5 Gate、策略和证据状态；未知状态不会被折叠成健康。</p>
      </section>
      <data-table
        :columns="columns"
        :rows="data.runs"
        empty-title="暂无运行记录"
        empty-detail="当前事件仓库没有运行事实；接入运行事件后会显示 Agent、Skill、风险、L5 Gate、策略和证据状态。"
      />
    </div>
  `
};
