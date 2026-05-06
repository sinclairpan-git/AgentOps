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
        <div><p class="eyebrow">Operator queue</p><h3>Risk Triage</h3></div>
        <p class="heading-copy">Risk items keep source ownership and next action explicit, including quality drops.</p>
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
            <ent-button tone="secondary" @click="$emit('navigate', risk.deep_link)">{{ risk.primary_action }}</ent-button>
          </div>
        </ent-card>
      </section>
    </div>
  `
};
