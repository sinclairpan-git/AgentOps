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
        { key: "command", label: "命令" },
        { key: "adapter_status", label: "Adapter", type: "status" },
        { key: "dry_run_status", label: "dry-run", type: "status" },
        { key: "verified_loaded", label: "治理证明", type: "status" },
        { key: "proof_source", label: "证明来源" },
        { key: "captured_at", label: "采集时间" }
      ]
    };
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">Ai_AutoSDLC 证明</p><h3>Ai_AutoSDLC 运行</h3></div>
        <p class="heading-copy">CLI dry-run 通过不代表 adapter 已完成治理激活；只有机器可验证证据才能进入 verified_loaded。</p>
      </section>
      <data-table :columns="columns" :rows="data.sdlcRuns" />
    </div>
  `
};
