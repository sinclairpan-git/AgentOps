import { StatusBadge } from "../components/StatusBadge.js";

export const RiskTriageView = {
  name: "RiskTriageView",
  components: {
    StatusBadge
  },
  props: {
    data: { type: Object, required: true }
  },
  methods: {
    actionId(risk) {
      return risk.source === "Agent Store" && String(risk.id).startsWith("gap_")
        ? `action_gap_${risk.id}`
        : `action_risk_${risk.id}`;
    }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">运营队列</p><h3>风险处置</h3></div>
        <p class="heading-copy">风险项明确来源、责任人和下一步动作，也覆盖质量下降问题。</p>
      </section>
      <section class="summary-band">
        <div>
          <p class="eyebrow">当前结论</p>
          <h4>{{ data.risks.length ? data.risks.length + ' 项风险需要复核' : '当前没有待处置风险' }}</h4>
          <p class="muted">{{ data.risks.length ? '按严重度、负责人和下一步动作逐项处理；本页只打开处置详情，不执行生产写操作。' : '后端事实快照没有返回风险队列。出现新风险后会在这里显示来源、负责人和建议动作。' }}</p>
        </div>
        <status-badge :status="data.risks.length ? 'warning' : 'healthy'" />
      </section>
      <section class="list-stack">
        <ent-card v-for="risk in data.risks" :key="risk.id">
          <div class="risk-card">
            <div>
              <p class="eyebrow">{{ risk.severity }}</p>
              <h4>{{ risk.source }}</h4>
              <p class="muted">负责人：{{ risk.owner_hint }}</p>
              <p class="muted">下一步：{{ risk.primary_action }}</p>
            </div>
            <status-badge :status="risk.state" />
            <ent-button tone="secondary" @click="$emit('open-action-detail', actionId(risk))">查看处置详情</ent-button>
          </div>
        </ent-card>
        <ent-card v-if="!data.risks.length">
          <div class="empty-workbench">
            <strong>风险队列为空</strong>
            <p>这是安全空态，不代表风险能力缺失。后续出现策略阻断、证据脱敏失败、连接器降级或治理证明缺口时，会在这里形成可追踪队列。</p>
            <span>建议下一步：继续观察总览指标或检查连接器状态。</span>
          </div>
        </ent-card>
      </section>
    </div>
  `
};
