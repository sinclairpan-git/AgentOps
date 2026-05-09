import { DataTable } from "../components/DataTable.js";
import { StatusBadge } from "../components/StatusBadge.js";

export const RunsView = {
  name: "RunsView",
  components: {
    DataTable,
    StatusBadge
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
        { key: "runtime_status", label: "运行时", type: "status" },
        { key: "trace_state", label: "轨迹", type: "status" },
        { key: "l5_state", label: "L5 Gate", type: "status" },
        { key: "policy_state", label: "策略", type: "status" },
        { key: "evidence_state", label: "证据", type: "status" }
      ]
    };
  },
  computed: {
    runtimeRuns() {
      return Array.isArray(this.data.runs) ? this.data.runs : [];
    }
  },
  methods: {
    traceTimeline(run) {
      return Array.isArray(run.trace_timeline) ? run.trace_timeline : [];
    },
    traceEmptyTitle(run) {
      return run.trace_state === "trace_pending" ? "轨迹待补齐" : "暂无轨迹摘要";
    },
    traceEmptyDetail(run) {
      if (run.trace_state === "trace_pending") {
        return "运行时记录已接收，但轨迹片段尚未到齐；页面不会把它显示为健康。";
      }
      return "当前仅保留运行摘要、状态和审计引用，不展示原始输入输出。";
    }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">运行事实</p><h3>运行记录</h3></div>
        <p class="heading-copy">每条运行都展示运行时、轨迹、L5 Gate、策略和证据状态；未知、阻断、待补齐状态不会被折叠成健康。</p>
      </section>
      <data-table
        :columns="columns"
        :rows="runtimeRuns"
        empty-title="暂无运行记录"
        empty-detail="当前事件仓库没有运行事实；接入运行事件后会显示 Agent、Skill、风险、L5 Gate、策略和证据状态。"
      />

      <section class="runtime-run-grid" aria-label="运行时运行详情">
        <ent-card
          v-for="run in runtimeRuns"
          :key="run.run_id + '-runtime-detail'"
          class="runtime-run-card"
        >
          <div class="runtime-run-head">
            <div>
              <p class="eyebrow">{{ run.run_id }}</p>
              <h4>{{ run.agent }} / {{ run.skill }}</h4>
            </div>
            <status-badge :status="run.runtime_status || run.l5_state || 'unknown'" />
          </div>
          <p class="summary-copy">{{ run.detail_summary || '仅展示脱敏运行摘要。' }}</p>
          <dl class="detail-list runtime-detail-list">
            <div><dt>轨迹状态</dt><dd><status-badge :status="run.trace_state || 'unknown'" /></dd></div>
            <div><dt>Outbox</dt><dd><status-badge :status="run.outbox_state || 'unknown'" /></dd></div>
            <div><dt>下一动作</dt><dd>{{ run.runtime_action || '保持观测' }}</dd></div>
          </dl>

          <div class="runtime-trace-panel">
            <div class="section-title">
              <h4>轨迹摘要</h4>
              <small>仅展示哈希引用和审计摘要</small>
            </div>
            <ul v-if="traceTimeline(run).length" class="timeline-list">
              <li
                v-for="span in traceTimeline(run)"
                :key="span.span_id"
                class="timeline-node runtime-span-node"
              >
                <span class="timeline-marker" aria-hidden="true"></span>
                <span>
                  <span class="timeline-head">
                    <strong>{{ span.title || span.span_id }}</strong>
                    <status-badge :status="span.status_code || 'unset'" />
                  </span>
                  <small>{{ span.span_kind }} · {{ span.duration_ms }}ms · 入参 {{ span.input_ref }} · 出参 {{ span.output_ref }}</small>
                </span>
              </li>
            </ul>
            <div v-else class="empty-workbench">
              <strong>{{ traceEmptyTitle(run) }}</strong>
              <p>{{ traceEmptyDetail(run) }}</p>
            </div>
          </div>
        </ent-card>
      </section>
    </div>
  `
};
