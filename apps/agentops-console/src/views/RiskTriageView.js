import { StatusBadge } from "../components/StatusBadge.js";

export const RiskTriageView = {
  name: "RiskTriageView",
  components: {
    StatusBadge
  },
  props: {
    data: { type: Object, required: true }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">运营队列</p><h3>风险处置</h3></div>
        <p class="heading-copy">风险项明确来源、责任人和下一步动作，也覆盖质量下降问题。</p>
      </section>
      <section class="list-stack">
        <ent-card v-for="risk in data.risks" :key="risk.id">
          <div class="risk-card">
            <div>
              <p class="eyebrow">{{ risk.severity }}</p>
              <h4>{{ risk.source }}</h4>
              <p class="muted">{{ risk.owner_hint }}</p>
            </div>
            <status-badge :status="risk.state" />
            <ent-button tone="secondary" @click="$emit('open-action-detail', 'action_risk_' + risk.id)">查看处置详情</ent-button>
          </div>
        </ent-card>
      </section>
    </div>
  `
};
