import { MetricTile } from "../components/MetricTile.js";
import { StatusBadge } from "../components/StatusBadge.js";

export const OverviewView = {
  name: "OverviewView",
  components: {
    MetricTile,
    StatusBadge
  },
  props: {
    data: { type: Object, required: true }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div>
          <p class="eyebrow">Trusted Operations</p>
          <h3>AgentOps Console</h3>
        </div>
        <p class="heading-copy">Live governance surface for runs, evidence, policy, approvals, quality and AI-SDLC adapter proof.</p>
      </section>

      <section class="metric-grid" aria-label="AgentOps summary metrics">
        <metric-tile
          v-for="metric in data.summary.metrics"
          :key="metric.label"
          :label="metric.label"
          :value="metric.value"
          :status="metric.status"
          :detail="metric.detail"
        />
      </section>

      <section class="split-grid">
        <ent-card>
          <div class="section-title">
            <h4>Priority Risks</h4>
            <ent-button tone="ghost" @click="$emit('navigate', 'risks')">Open queue</ent-button>
          </div>
          <div class="list-stack">
            <button
              v-for="risk in data.risks.slice(0, 4)"
              :key="risk.id"
              class="risk-row"
              type="button"
              @click="$emit('navigate', risk.deep_link)"
            >
              <span>
                <strong>{{ risk.source }}</strong>
                <small>{{ risk.owner_hint }} · {{ risk.primary_action }}</small>
              </span>
              <status-badge :status="risk.state" />
            </button>
          </div>
        </ent-card>

        <ent-card>
          <div class="section-title">
            <h4>Governance Proof</h4>
            <ent-button tone="ghost" @click="$emit('navigate', 'sdlc-runs')">Inspect</ent-button>
          </div>
          <div class="proof-panel">
            <status-badge :status="data.summary.adapter.status" />
            <p>{{ data.summary.adapter.copy }}</p>
            <dl>
              <div><dt>Proof source</dt><dd>{{ data.summary.adapter.proof_source }}</dd></div>
              <div><dt>Captured</dt><dd>{{ data.summary.adapter.captured_at }}</dd></div>
            </dl>
          </div>
        </ent-card>
      </section>
    </div>
  `
};
