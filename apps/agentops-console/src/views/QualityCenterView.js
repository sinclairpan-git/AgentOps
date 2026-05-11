import { DataTable } from "../components/DataTable.js";
import { StatusBadge } from "../components/StatusBadge.js";

export const QualityCenterView = {
  name: "QualityCenterView",
  components: {
    DataTable,
    StatusBadge
  },
  props: {
    data: { type: Object, required: true }
  },
  data() {
    return {
      agentColumns: [
        { key: "agent_id", label: "Agent" },
        { key: "version", label: "版本" },
        { key: "quality_state", label: "质量状态", type: "status" },
        { key: "score_label", label: "评分" },
        { key: "confidence_label", label: "置信度" },
        { key: "evidence_level", label: "证据等级" },
        { key: "scorer_state", label: "评分器状态" },
        { key: "lifecycle_action", label: "生命周期建议" }
      ],
      reviewColumns: [
        { key: "review_type", label: "复核类型" },
        { key: "agent_id", label: "Agent" },
        { key: "reason", label: "原因" },
        { key: "recommended_action", label: "建议动作" },
        { key: "owner_team", label: "负责人" }
      ],
      signalColumns: [
        { key: "signal_id", label: "信号" },
        { key: "category", label: "类别" },
        { key: "status", label: "状态", type: "status" },
        { key: "score", label: "分数" },
        { key: "evidence_ref", label: "证据" },
        { key: "owner_hint", label: "负责人" },
        { key: "primary_action", label: "动作" }
      ]
    };
  },
  computed: {
    qualityCenterWorkbench() {
      return this.data.qualityCenterWorkbench || {
        workbench_state: "empty",
        agent_summaries: [],
        scorer_rollout_panel: {
          candidate_count: 0,
          ready_for_manual_approval_count: 0,
          needs_human_review_count: 0,
          insufficient_evidence_count: 0,
          manual_approval_queue_size: 0,
          automatic_rollout_enabled: false
        },
        review_queue: [],
        trend_summary: {},
        summary: {}
      };
    },
    rolloutPanel() {
      return this.qualityCenterWorkbench.scorer_rollout_panel || {};
    },
    trendSummary() {
      return this.qualityCenterWorkbench.trend_summary || {};
    },
    guardrailSummary() {
      return this.qualityCenterWorkbench.summary || {};
    },
    metricTiles() {
      return [
        {
          label: "Agent 摘要",
          value: this.qualityCenterWorkbench.agent_summaries.length,
          detail: this.qualityCenterWorkbench.workbench_state || "empty"
        },
        {
          label: "候选评分器",
          value: this.rolloutPanel.candidate_count || 0,
          detail: `人工审批 ${this.rolloutPanel.manual_approval_queue_size || 0}`
        },
        {
          label: "复核队列",
          value: this.qualityCenterWorkbench.review_queue.length,
          detail: `趋势复核 ${this.trendSummary.review_queue_size || 0}`
        },
        {
          label: "保留率",
          value: this.trendSummary.retention_rate || "0%",
          detail: `返工 ${this.trendSummary.rework_rounds || 0}`
        }
      ];
    },
    agentSummaryRows() {
      return this.qualityCenterWorkbench.agent_summaries.map((item) => ({
        ...item,
        id: `${item.agent_id}_${item.version}`,
        score_label: `${Math.round(Number(item.score || 0))}`,
        confidence_label: `${Math.round(Number(item.confidence || 0) * 100)}%`,
        scorer_state: item.scorer_comparison?.comparison_state || "insufficient_evidence",
        missing_evidence_text: (item.missing_evidence || []).join("、") || "无"
      }));
    },
    qualitySignals() {
      return this.data.quality || [];
    },
    boundaryRows() {
      return [
        { label: "原始证据", value: this.guardrailSummary.payload_access || "forbidden" },
        { label: "提示词 / 变更", value: `${this.guardrailSummary.prompt_access || "forbidden"} / ${this.guardrailSummary.change_access || "forbidden"}` },
        { label: "发布执行", value: this.guardrailSummary.automatic_rollout_enabled ? "enabled" : "disabled" },
        { label: "Store 写回", value: this.guardrailSummary.store_write_performed ? "performed" : "not_performed" },
        { label: "发布/通知", value: this.guardrailSummary.automatic_publish_performed || this.guardrailSummary.notification_sent ? "performed" : "not_performed" }
      ];
    }
  },
  methods: {
    readableText(value) {
      return String(value ?? "")
        .replaceAll("ready_for_manual_approval", "待人工审批")
        .replaceAll("needs_human_review", "需人工复核")
        .replaceAll("insufficient_evidence", "证据不足")
        .replaceAll("collect_more_evidence", "补充证据")
        .replaceAll("collect_more_samples", "补充样本")
        .replaceAll("submit_for_manual_rollout_approval", "提交人工发布审批")
        .replaceAll("open_ops_review", "打开人工复核")
        .replaceAll("open_disable_review", "打开禁用复核")
        .replaceAll("forbidden", "禁止")
        .replaceAll("disabled", "关闭")
        .replaceAll("not_performed", "未执行")
        .replaceAll("candidate", "候选");
    }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">质量治理</p><h3>质量中心</h3></div>
        <p class="heading-copy">质量分、评分器发布、复核队列和趋势摘要统一展示；低置信只进入人工复核。</p>
      </section>
      <section class="metric-grid">
        <article v-for="item in metricTiles" :key="item.label" class="ent-card metric-tile">
          <div>
            <p class="metric-label">{{ item.label }}</p>
            <strong>{{ item.value }}</strong>
            <small>{{ readableText(item.detail) }}</small>
          </div>
        </article>
      </section>
      <section class="summary-band quality-center-band">
        <div>
          <p class="eyebrow">质量中心工作台</p>
          <h4>评分器发布与生命周期边界</h4>
          <p class="muted">候选评分器、缺证据和生命周期建议只进入人工队列；本页不执行发布、Store 写回或通知发送。</p>
        </div>
        <dl class="evidence-vault-metrics quality-center-metrics">
          <div><dt>待审批</dt><dd>{{ rolloutPanel.ready_for_manual_approval_count || 0 }}</dd></div>
          <div><dt>需复核</dt><dd>{{ rolloutPanel.needs_human_review_count || 0 }}</dd></div>
          <div><dt>证据不足</dt><dd>{{ rolloutPanel.insufficient_evidence_count || 0 }}</dd></div>
          <div><dt>发布执行</dt><dd>{{ rolloutPanel.automatic_rollout_enabled ? '开启' : '关闭' }}</dd></div>
        </dl>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>Agent 质量摘要</h4>
          <span class="muted">AO42 仅摘要</span>
        </div>
        <data-table
          :columns="agentColumns"
          :rows="agentSummaryRows"
          empty-title="暂无质量工作台摘要"
          empty-detail="当前快照没有 Agent 质量摘要；接入 AO42 快照后会显示评分、置信度和评分器状态。"
        />
        <div class="boundary-list" aria-label="缺失证据摘要">
          <h5 class="boundary-title">质量解释链</h5>
          <div v-for="item in agentSummaryRows" :key="item.id + '_evidence'" class="boundary-row quality-center-row">
            <strong>{{ item.agent_id }}</strong>
            <span>{{ readableText(item.missing_evidence_text) }}</span>
            <small>{{ readableText(item.explanation) }}</small>
          </div>
        </div>
      </section>
      <section class="panel-grid two">
        <article class="ent-card quality-insight-card">
          <div class="section-title">
            <h4>采纳概览</h4>
            <status-badge :status="trendSummary.report_state || 'insufficient_data'" />
          </div>
          <dl class="detail-list">
            <div><dt>保留率</dt><dd>{{ trendSummary.retention_rate || '0%' }}</dd></div>
            <div><dt>复核队列</dt><dd>{{ trendSummary.review_queue_size || 0 }}</dd></div>
            <div><dt>返工轮次</dt><dd>{{ trendSummary.rework_rounds || 0 }}</dd></div>
            <div><dt>PR 问题</dt><dd>{{ trendSummary.pr_review_findings || 0 }}</dd></div>
          </dl>
          <p class="summary-copy">{{ readableText(trendSummary.recommendation || '等待质量趋势摘要。') }}</p>
        </article>
        <article class="ent-card quality-insight-card">
          <div class="section-title">
            <h4>处置红线</h4>
            <span class="muted">只读工作台</span>
          </div>
          <dl class="detail-list">
            <div v-for="item in boundaryRows" :key="item.label"><dt>{{ item.label }}</dt><dd>{{ readableText(item.value) }}</dd></div>
          </dl>
        </article>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>复核队列</h4>
          <span>人工处理</span>
        </div>
        <data-table
          :columns="reviewColumns"
          :rows="qualityCenterWorkbench.review_queue"
          empty-title="暂无人工复核事项"
          empty-detail="当前没有缺证据、低置信或评分器发布项需要人工处理。"
        />
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>原质量信号</h4>
          <span class="muted">兼容旧版快照</span>
        </div>
        <data-table
          :columns="signalColumns"
          :rows="qualitySignals"
          empty-title="暂无质量信号"
          empty-detail="当前快照没有质量异常信号；采纳、CI、复核或 Agent Store 回显产生后会在这里展示。"
        />
      </section>
    </div>
  `
};
