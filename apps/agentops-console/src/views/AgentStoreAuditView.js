import { DataTable } from "../components/DataTable.js";
import { StatusBadge } from "../components/StatusBadge.js";

export const AgentStoreAuditView = {
  name: "AgentStoreAuditView",
  components: {
    DataTable,
    StatusBadge
  },
  props: {
    data: { type: Object, required: true }
  },
  data() {
    return {
      gapColumns: [
        { key: "gap_id", label: "发现编号" },
        { key: "gap_type", label: "类型" },
        { key: "agent_id", label: "Agent" },
        { key: "version", label: "版本" },
        { key: "state", label: "状态", type: "status" },
        { key: "severity", label: "级别" },
        { key: "owner_hint", label: "负责人" },
        { key: "affected_runs_label", label: "影响运行" },
        { key: "primary_action", label: "下一步" }
      ],
      registryColumns: [
        { key: "agent_id", label: "Agent" },
        { key: "version", label: "版本" },
        { key: "metadata_state", label: "元数据状态", type: "status" },
        { key: "fact_owner", label: "事实来源" },
        { key: "skill_count", label: "Skill 数" },
        { key: "synced_at", label: "同步时间" }
      ]
    };
  },
  computed: {
    agentStore() {
      const source = this.data.agentStore || {};
      return {
        discoveryGaps: Array.isArray(source.discoveryGaps) ? source.discoveryGaps : [],
        runAudits: Array.isArray(source.runAudits) ? source.runAudits : [],
        storeSummaries: Array.isArray(source.storeSummaries) ? source.storeSummaries : [],
        registryMap: Array.isArray(source.registryMap) ? source.registryMap : []
      };
    },
    activeSummary() {
      return this.agentStore.storeSummaries[0] || null;
    },
    gapRows() {
      return this.agentStore.discoveryGaps.map((gap) => ({
        ...gap,
        affected_runs_label: this.joinValues(gap.affected_runs)
      }));
    },
    activePolicyRequirement() {
      return this.activeSummary?.policy_requirement || {
        policy_owner: "待确认",
        affected_actions: []
      };
    }
  },
  methods: {
    joinValues(values) {
      return (values || []).join("、") || "无";
    },
    auditDeepLinks(audit) {
      return audit.deep_links || {
        session_id: "待确认",
        trace_id: "待确认",
        installation_id: "待确认",
        return_url: "待确认"
      };
    }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">Agent Store 治理</p><h3>Agent Store 审计</h3></div>
        <p class="heading-copy">集中查看未注册发现、运行审计和回显摘要；AgentOps 只消费 Agent Store 元数据，不写注册事实。</p>
      </section>

      <section class="panel-grid three">
        <ent-card>
          <p class="eyebrow">发现队列</p>
          <h4>{{ agentStore.discoveryGaps.length }}</h4>
          <p class="muted">未注册 Agent 或 Skill 会进入疑似异常队列。</p>
        </ent-card>
        <ent-card>
          <p class="eyebrow">运行审计</p>
          <h4>{{ agentStore.runAudits.length }}</h4>
          <p class="muted">审计只展示摘要和深链，不暴露原文。</p>
        </ent-card>
        <ent-card>
          <p class="eyebrow">注册映射</p>
          <h4>{{ agentStore.registryMap.length }}</h4>
          <p class="muted">事实来源保持为 Agent Store。</p>
        </ent-card>
      </section>

      <section class="view-stack">
        <div class="section-title">
          <h4>发现队列</h4>
          <span>负责人和下一步动作</span>
        </div>
        <data-table v-if="gapRows.length" :columns="gapColumns" :rows="gapRows" />
        <ent-card v-else><p class="empty-state">暂无未注册发现。</p></ent-card>
      </section>

      <section class="list-stack">
        <div class="section-title">
          <h4>运行审计</h4>
          <span>注册状态、事件数和深链</span>
        </div>
        <ent-card v-for="audit in agentStore.runAudits" :key="audit.audit_id">
          <div class="audit-card">
            <div>
              <p class="eyebrow">{{ audit.audit_id }}</p>
              <h4>{{ audit.run_id }}</h4>
              <p class="muted">{{ audit.agent_id }} / {{ audit.version }} · {{ audit.event_count }} 条事件</p>
              <p class="muted">关联版本：{{ joinValues(audit.related_agent_versions) }}</p>
              <p class="muted">发现编号：{{ joinValues(audit.discovery_gap_ids) }}</p>
            </div>
            <status-badge :status="audit.registration_state" />
            <ent-button tone="secondary" @click="$emit('navigate', 'runs')">查看运行</ent-button>
          </div>
          <div class="deep-link-grid">
            <span>session_id：{{ auditDeepLinks(audit).session_id }}</span>
            <span>trace_id：{{ auditDeepLinks(audit).trace_id }}</span>
            <span>installation_id：{{ auditDeepLinks(audit).installation_id }}</span>
            <span>return_url：{{ auditDeepLinks(audit).return_url }}</span>
          </div>
        </ent-card>
      </section>

      <section v-if="activeSummary" class="summary-band">
        <div>
          <p class="eyebrow">回显摘要</p>
          <h4>{{ activeSummary.agent_id }} / {{ activeSummary.agent_version }}</h4>
          <p class="muted">证据等级 {{ activeSummary.evidence_level }}，置信度 {{ activeSummary.confidence }}，有效期至 {{ activeSummary.valid_until }}</p>
          <p class="muted">策略要求：{{ activePolicyRequirement.policy_owner }} 负责，影响 {{ joinValues(activePolicyRequirement.affected_actions) }}</p>
        </div>
        <status-badge :status="activeSummary.risk_state" />
      </section>

      <section class="view-stack">
        <div class="section-title">
          <h4>注册映射</h4>
          <span>只读消费 Agent Store 元数据</span>
        </div>
        <data-table :columns="registryColumns" :rows="agentStore.registryMap" />
      </section>
    </div>
  `
};
