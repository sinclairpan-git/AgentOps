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
          <p class="eyebrow">可信运行</p>
          <h3>AgentOps 控制台</h3>
        </div>
        <p class="heading-copy">统一查看运行、证据、策略、审批、质量，以及 AI-SDLC 框架下的 Ai_AutoSDLC adapter 证明。</p>
      </section>

      <section class="metric-grid" aria-label="AgentOps 总览指标">
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
            <h4>优先风险</h4>
            <ent-button tone="ghost" @click="$emit('navigate', 'risks')">打开队列</ent-button>
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
            <h4>治理证明</h4>
            <ent-button tone="ghost" @click="$emit('navigate', 'sdlc-runs')">查看</ent-button>
          </div>
          <div class="proof-panel">
            <status-badge :status="data.summary.adapter.status" />
            <p>{{ data.summary.adapter.copy }}</p>
            <dl>
              <div><dt>证明来源</dt><dd>{{ data.summary.adapter.proof_source }}</dd></div>
              <div><dt>采集时间</dt><dd>{{ data.summary.adapter.captured_at }}</dd></div>
            </dl>
          </div>
        </ent-card>
      </section>
    </div>
  `
};
