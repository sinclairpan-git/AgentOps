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
        { key: "signal_id", label: "信号" },
        { key: "category", label: "类别" },
        { key: "status", label: "状态", type: "status" },
        { key: "score", label: "分数" },
        { key: "evidence_ref", label: "证据" },
        { key: "owner_hint", label: "负责人" },
        { key: "primary_action", label: "动作" }
      ]
    };
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">质量治理</p><h3>质量中心</h3></div>
        <p class="heading-copy">质量信号让契约覆盖、Browser Gate 准备度和证据完整性可运营。</p>
      </section>
      <data-table :columns="columns" :rows="data.quality" />
    </div>
  `
};
