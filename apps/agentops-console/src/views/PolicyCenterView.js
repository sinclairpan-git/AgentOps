import { DataTable } from "../components/DataTable.js";
import { TermGlossary } from "../components/TermGlossary.js";

export const PolicyCenterView = {
  name: "PolicyCenterView",
  components: {
    DataTable,
    TermGlossary
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
        { key: "grant_ttl", label: "授权有效期" },
        { key: "audit_id", label: "审计" }
      ],
      glossaryTerms: [
        { label: "在线校验", copy: "执行前必须连到策略服务再次确认。" },
        { label: "阻断", copy: "动作不允许继续，需要人工或更高等级证据处理。" },
        { label: "授权有效期", copy: "临时授权可生效的时间窗口。" }
      ]
    };
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">运行策略</p><h3>策略中心</h3></div>
        <p class="heading-copy">拒绝/阻断优先级高于已生效授权票；高风险未知状态不会显示为允许。</p>
      </section>
      <term-glossary :terms="glossaryTerms" />
      <data-table :columns="columns" :rows="data.policies" />
    </div>
  `
};
