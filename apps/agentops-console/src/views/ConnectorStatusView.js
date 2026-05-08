import { DataTable } from "../components/DataTable.js";
import { TermGlossary } from "../components/TermGlossary.js";

export const ConnectorStatusView = {
  name: "ConnectorStatusView",
  components: {
    DataTable,
    TermGlossary
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
        { key: "dlq_depth", label: "异常队列积压" },
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
      ],
      glossaryTerms: [
        { label: "异常队列", copy: "处理失败或待复核的事件集合，避免问题被静默丢失。" },
        { label: "事件重放", copy: "按审批后的安全流程重新投递事件，本页只展示状态。" },
        { label: "已验证加载", copy: "机器证明确认治理规则已被真实加载。" },
        { label: "限流", copy: "连接器主动降速，防止外部系统或证据链被压垮。" }
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
  methods: {
    readableText(value) {
      return String(value || "")
        .replaceAll("verified_loaded", "已验证加载")
        .replaceAll("materialized", "已生成配置")
        .replaceAll("unverified", "未验证")
        .replaceAll("DLQ", "异常队列")
        .replaceAll("Outbox Replay", "事件重放")
        .replaceAll("Outbox", "事件投递箱")
        .replaceAll("require_online", "在线校验");
    }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">集成治理</p><h3>连接器状态</h3></div>
        <p class="heading-copy">统一查看 Git、PR、CI、测试、IAM、证据和策略连接器的新鲜度、限流、异常队列、回放边界与降级影响。</p>
      </section>
      <term-glossary :terms="glossaryTerms" />
      <section class="summary-band evidence-vault-band">
        <div>
          <p class="eyebrow">连接器健康工作台</p>
          <h4>新鲜度、限流与证据影响</h4>
          <p class="muted">“已生成配置/未验证”只能证明配置或预演存在，不构成“已验证加载”的治理激活证明。</p>
        </div>
        <dl class="evidence-vault-metrics connector-metrics">
          <div><dt>连接器</dt><dd>{{ connectorWorkbench.health.length }}</dd></div>
          <div><dt>需复核</dt><dd>{{ degradedCount }}</dd></div>
          <div><dt>异常队列风险</dt><dd>{{ dlqRiskCount }}</dd></div>
          <div><dt>未验证</dt><dd>{{ unverifiedCount }}</dd></div>
        </dl>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>处置红线</h4>
          <span class="muted">只读连接器摘要</span>
        </div>
        <ul class="guardrail-list">
          <li v-for="item in connectorWorkbench.guardrails" :key="item">{{ readableText(item) }}</li>
        </ul>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>健康与限流</h4>
          <span class="muted">15 分钟 SLO，超过 20 分钟告警</span>
        </div>
        <data-table
          :columns="healthColumns"
          :rows="connectorWorkbench.health"
          empty-title="暂无连接器心跳"
          empty-detail="当前快照没有连接器健康记录；接入 Git、PR、CI、IAM 等连接器后会显示新鲜度、限流和负责人。"
        />
        <div class="boundary-list" aria-label="连接器证据影响">
          <h5 class="boundary-title">证据等级与处置建议</h5>
          <div v-for="item in connectorWorkbench.health" :key="item.id + '_impact'" class="boundary-row connector-boundary-row">
            <strong>{{ item.name }}</strong>
            <span>{{ readableText(item.evidence_impact) }}</span>
            <small>限流：{{ readableText(item.rate_limit_detail) }} · {{ readableText(item.primary_action) }} · {{ readableText(item.secondary_action) }} · {{ item.request_id }}</small>
          </div>
        </div>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>异常队列与事件重放</h4>
          <span class="muted">只读展示，不在本页执行回放</span>
        </div>
        <data-table
          :columns="dlqColumns"
          :rows="connectorWorkbench.dlq"
          empty-title="暂无异常队列风险"
          empty-detail="当前没有死信或回放风险；出现积压后会显示最旧事件、回放窗口和审计引用。"
        />
        <div class="boundary-list" aria-label="异常队列回放边界">
          <h5 class="boundary-title">降级策略</h5>
          <div v-for="item in connectorWorkbench.dlq" :key="item.id + '_policy'" class="boundary-row connector-boundary-row">
            <strong>{{ item.connector_id }}</strong>
            <span>{{ readableText(item.degrade_policy) }}</span>
            <small>{{ readableText(item.safety_note) }}</small>
          </div>
        </div>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>同步轨迹</h4>
          <span class="muted">心跳、降级与待证明状态可追溯</span>
        </div>
        <data-table
          :columns="trailColumns"
          :rows="connectorWorkbench.syncTrail"
          empty-title="暂无同步轨迹"
          empty-detail="心跳、降级、限流和待证明状态发生后会记录在这里。"
        />
      </section>
    </div>
  `
};
