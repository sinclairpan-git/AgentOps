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
  computed: {
    runtimeSummary() {
      const runs = Array.isArray(this.data.runs) ? this.data.runs : [];
      const counts = runs.reduce((acc, run) => {
        const status = run.runtime_status || "unknown";
        acc[status] = (acc[status] || 0) + 1;
        return acc;
      }, {});
      return [
        { status: "succeeded", label: "成功", value: counts.succeeded || 0, detail: "完整轨迹摘要" },
        { status: "blocked", label: "阻断", value: counts.blocked || 0, detail: "策略或安全边界阻断" },
        { status: "approval_paused", label: "审批暂停", value: counts.approval_paused || 0, detail: "等待人工 Grant" },
        { status: "trace_pending", label: "轨迹待补齐", value: counts.trace_pending || 0, detail: "运行事实早于轨迹片段到达" },
        { status: "degraded", label: "降级", value: counts.degraded || 0, detail: "仅展示安全摘要" }
      ];
    }
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
            <ent-button tone="ghost" @click="$emit('navigate', 'risks')">查看风险处置队列</ent-button>
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
            <div v-if="!data.risks.length" class="empty-workbench">
              <strong>暂无优先风险</strong>
              <p>当前没有策略阻断、证据脱敏失败或治理证明缺口。新风险出现后会同步到风险处置队列。</p>
            </div>
          </div>
        </ent-card>

        <ent-card>
          <div class="section-title">
            <h4>治理证明</h4>
            <ent-button tone="ghost" @click="$emit('navigate', 'sdlc-runs')">查看 AI-SDLC 证明</ent-button>
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

        <ent-card>
          <div class="section-title">
            <h4>运行时运行态</h4>
            <ent-button tone="ghost" @click="$emit('navigate', 'runs')">查看运行记录</ent-button>
          </div>
          <div class="runtime-status-grid">
            <button
              v-for="item in runtimeSummary"
              :key="item.status"
              class="runtime-status-card"
              type="button"
              @click="$emit('navigate', 'runs')"
            >
              <span>
                <strong>{{ item.value }}</strong>
                <small>{{ item.label }}</small>
              </span>
              <status-badge :status="item.status" />
              <em>{{ item.detail }}</em>
            </button>
          </div>
        </ent-card>
      </section>
    </div>
  `
};
