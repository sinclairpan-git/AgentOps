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
      columns: [
        { key: "signal_id", label: "信号" },
        { key: "category", label: "类别" },
        { key: "status", label: "状态", type: "status" },
        { key: "score", label: "分数" },
        { key: "evidence_ref", label: "证据" },
        { key: "owner_hint", label: "负责人" },
        { key: "primary_action", label: "动作" }
      ],
      reviewColumns: [
        { key: "title", label: "复核事项" },
        { key: "status", label: "状态", type: "status" },
        { key: "owner", label: "负责人" },
        { key: "evidence_ref", label: "证据" },
        { key: "action", label: "动作" }
      ]
    };
  },
  computed: {
    adoption() {
      return this.data.adoption || {
        metrics: {},
        explanationChains: [],
        segments: [],
        reviewSignals: [],
        guardrails: []
      };
    },
    metricTiles() {
      const metrics = this.adoption.metrics || {};
      return [
        { label: "生成行数", value: metrics.generated_lines || 0, detail: "AI 生成摘要量" },
        { label: "最终保留", value: metrics.retained_lines || 0, detail: `保留率 ${metrics.retention_rate || "待采集"}` },
        { label: "人工修改", value: metrics.human_modified_lines || 0, detail: "人工调整摘要量" },
        { label: "返工轮次", value: metrics.rework_rounds || 0, detail: `PR 问题 ${metrics.pr_review_findings || 0}` }
      ];
    },
    ciFailureTypes() {
      return (this.adoption.metrics && this.adoption.metrics.ci_failure_types) || [];
    }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">质量治理</p><h3>质量中心</h3></div>
        <p class="heading-copy">质量信号、采纳摘要和复核队列共同解释 Agent 效果；低置信不自动下架。</p>
      </section>
      <section class="metric-grid">
        <article v-for="item in metricTiles" :key="item.label" class="ent-card metric-tile">
          <div>
            <p class="metric-label">{{ item.label }}</p>
            <strong>{{ item.value }}</strong>
            <small>{{ item.detail }}</small>
          </div>
        </article>
      </section>
      <section class="split-grid">
        <article class="ent-card quality-insight-card">
          <div class="section-title">
            <h4>采纳概览</h4>
            <span>聚合摘要</span>
          </div>
          <dl class="detail-list">
            <div><dt>删除行数</dt><dd>{{ adoption.metrics.deleted_lines || 0 }}</dd></div>
            <div><dt>CI 失败类型</dt><dd>{{ ciFailureTypes.join('、') }}</dd></div>
            <div><dt>安全边界</dt><dd>不展示代码片段、差异内容或 PR 原文</dd></div>
          </dl>
        </article>
        <article class="ent-card quality-insight-card">
          <div class="section-title">
            <h4>治理红线</h4>
            <span>生命周期边界</span>
          </div>
          <ul class="guardrail-list">
            <li v-for="item in adoption.guardrails" :key="item">{{ item }}</li>
          </ul>
        </article>
      </section>
      <section class="card-grid">
        <div class="section-title quality-chain-heading">
          <h4>质量解释链</h4>
          <span>评分依据</span>
        </div>
        <article v-for="chain in adoption.explanationChains" :key="chain.id" class="ent-card quality-chain">
          <div class="section-title">
            <h4>{{ chain.category }}</h4>
            <status-badge :status="chain.status" />
          </div>
          <dl class="detail-list">
            <div><dt>评分模板</dt><dd>{{ chain.score_template_id }}</dd></div>
            <div><dt>证据等级</dt><dd>{{ chain.evidence_level }}</dd></div>
            <div><dt>置信度</dt><dd>{{ Math.round(chain.confidence * 100) }}%</dd></div>
            <div><dt>缺失证据</dt><dd>{{ chain.missing_evidence.join('、') }}</dd></div>
            <div><dt>申诉路径</dt><dd>{{ chain.appeal_path }}</dd></div>
          </dl>
          <p class="summary-copy">{{ chain.explanation }}</p>
          <p class="safety-note">{{ chain.lifecycle_guardrail }}</p>
        </article>
      </section>
      <section class="panel-grid two">
        <article v-for="segment in adoption.segments" :key="segment.id" class="ent-card quality-segment">
          <div class="section-title">
            <h4>{{ segment.title }}</h4>
            <status-badge :status="segment.status" />
          </div>
          <dl class="detail-list">
            <div><dt>保留率</dt><dd>{{ segment.retention_rate }}</dd></div>
            <div><dt>影响 Agent</dt><dd>{{ segment.affected_agents }}</dd></div>
            <div><dt>负责人</dt><dd>{{ segment.owner }}</dd></div>
            <div><dt>下次复核</dt><dd>{{ segment.next_review }}</dd></div>
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
          :rows="adoption.reviewSignals"
          empty-title="暂无人工复核事项"
          empty-detail="当前没有低置信、返工或采纳异常需要人工处理。"
        />
      </section>
      <data-table
        :columns="columns"
        :rows="data.quality"
        empty-title="暂无质量信号"
        empty-detail="当前快照没有质量异常信号；采纳、CI、复核或 Agent Store 回显产生后会在这里展示。"
      />
    </div>
  `
};
