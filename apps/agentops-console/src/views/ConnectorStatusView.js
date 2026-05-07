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
      healthColumns: [
        { key: "name", label: "连接器" },
        { key: "status", label: "状态", type: "status" },
        { key: "last_seen_at", label: "最后心跳" },
        { key: "freshness", label: "新鲜度" },
        { key: "rate_limit_state", label: "限流", type: "status" },
        { key: "rate_limit_detail", label: "限流说明" },
        { key: "owner", label: "负责人" }
      ],
      dlqColumns: [
        { key: "connector_id", label: "连接器" },
        { key: "dlq_depth", label: "DLQ 积压" },
        { key: "oldest_event_age", label: "最旧事件" },
        { key: "replay_state", label: "回放状态", type: "status" },
        { key: "retry_window", label: "回放窗口" },
        { key: "audit_id", label: "审计引用" }
      ],
      trailColumns: [
        { key: "connector_id", label: "连接器" },
        { key: "stage", label: "阶段" },
        { key: "occurred_at", label: "发生时间" },
        { key: "summary", label: "同步摘要" },
        { key: "owner", label: "负责人" },
        { key: "status", label: "状态", type: "status" }
      ]
    };
  },
  computed: {
    connectorWorkbench() {
      return this.data.connectorWorkbench || {
        health: [],
        dlq: [],
        syncTrail: [],
        guardrails: []
      };
    },
    degradedCount() {
      return this.connectorWorkbench.health.filter((item) => item.status !== "healthy").length;
    },
    dlqRiskCount() {
      return this.connectorWorkbench.dlq.filter((item) => item.replay_state === "pending").length;
    },
    unverifiedCount() {
      return this.connectorWorkbench.health.filter((item) =>
        item.status === "materialized" || /verified_loaded/.test(item.evidence_impact || "")
      ).length;
    }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">集成治理</p><h3>连接器状态</h3></div>
        <p class="heading-copy">统一查看 Git、PR、CI、测试、IAM、证据和策略连接器的新鲜度、限流、DLQ、回放边界与降级影响。</p>
      </section>
      <section class="summary-band evidence-vault-band">
        <div>
          <p class="eyebrow">连接器健康工作台</p>
          <h4>新鲜度、限流与证据影响</h4>
          <p class="muted">materialized/unverified 只能证明配置或预演存在，不构成 verified_loaded 治理激活证明。</p>
        </div>
        <dl class="evidence-vault-metrics connector-metrics">
          <div><dt>连接器</dt><dd>{{ connectorWorkbench.health.length }}</dd></div>
          <div><dt>需复核</dt><dd>{{ degradedCount }}</dd></div>
          <div><dt>DLQ 风险</dt><dd>{{ dlqRiskCount }}</dd></div>
          <div><dt>未验证</dt><dd>{{ unverifiedCount }}</dd></div>
        </dl>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>处置红线</h4>
          <span class="muted">只读连接器摘要</span>
        </div>
        <ul class="guardrail-list">
          <li v-for="item in connectorWorkbench.guardrails" :key="item">{{ item }}</li>
        </ul>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>健康与限流</h4>
          <span class="muted">15 分钟 SLO，超过 20 分钟告警</span>
        </div>
        <data-table :columns="healthColumns" :rows="connectorWorkbench.health" />
        <div class="boundary-list" aria-label="连接器证据影响">
          <h5 class="boundary-title">证据等级与处置建议</h5>
          <div v-for="item in connectorWorkbench.health" :key="item.id + '_impact'" class="boundary-row connector-boundary-row">
            <strong>{{ item.name }}</strong>
            <span>{{ item.evidence_impact }}</span>
            <small>限流：{{ item.rate_limit_detail }} · {{ item.primary_action }} · {{ item.secondary_action }} · {{ item.request_id }}</small>
          </div>
        </div>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>DLQ 与 Outbox Replay</h4>
          <span class="muted">只读展示，不在本页执行回放</span>
        </div>
        <data-table :columns="dlqColumns" :rows="connectorWorkbench.dlq" />
        <div class="boundary-list" aria-label="DLQ 回放边界">
          <h5 class="boundary-title">降级策略</h5>
          <div v-for="item in connectorWorkbench.dlq" :key="item.id + '_policy'" class="boundary-row connector-boundary-row">
            <strong>{{ item.connector_id }}</strong>
            <span>{{ item.degrade_policy }}</span>
            <small>{{ item.safety_note }}</small>
          </div>
        </div>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>同步轨迹</h4>
          <span class="muted">心跳、降级与待证明状态可追溯</span>
        </div>
        <data-table :columns="trailColumns" :rows="connectorWorkbench.syncTrail" />
      </section>
    </div>
  `
};
