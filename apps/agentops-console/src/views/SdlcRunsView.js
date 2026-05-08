import { DataTable } from "../components/DataTable.js";
import { StatusBadge } from "../components/StatusBadge.js";
import { TermGlossary } from "../components/TermGlossary.js";

export const SdlcRunsView = {
  name: "SdlcRunsView",
  components: {
    DataTable,
    StatusBadge,
    TermGlossary
  },
  props: {
    data: { type: Object, required: true }
  },
  data() {
    return {
      columns: [
        { key: "command", label: "命令" },
        { key: "adapter_status", label: "Adapter", type: "status" },
        { key: "dry_run_status", label: "dry-run", type: "status" },
        { key: "verified_loaded", label: "治理证明", type: "status" },
        { key: "proof_source", label: "证明来源" },
        { key: "captured_at", label: "采集时间" }
      ],
      reporterColumns: [
        { key: "command", label: "命令" },
        { key: "reporter_status", label: "上报器", type: "status" },
        { key: "credential_status", label: "凭证", type: "status" },
        { key: "source_signed", label: "签名", type: "status" },
        { key: "governance_state", label: "治理状态", type: "status" },
        { key: "primary_action", label: "下一步" }
      ],
      outboxColumns: [
        { key: "run_id", label: "运行" },
        { key: "outbox_status", label: "事件投递箱", type: "status" },
        { key: "sequence_state", label: "序列", type: "status" },
        { key: "pending_events", label: "待投递" },
        { key: "oldest_pending_age", label: "最旧待办" },
        { key: "audit_id", label: "审计引用" }
      ],
      eligibilityColumns: [
        { key: "run_id", label: "运行" },
        { key: "evidence_level", label: "证据等级" },
        { key: "l5_result", label: "L5 结果", type: "status" },
        { key: "governance_loaded", label: "治理加载", type: "status" },
        { key: "outbox_delivered", label: "事件投递", type: "status" },
        { key: "next_action", label: "下一步" }
      ],
      glossaryTerms: [
        { label: "已验证加载", copy: "后端拿到机器可验证证据，才算治理真的生效。" },
        { label: "已生成配置/未验证", copy: "只说明配置或预演存在，还不能当作生效证明。" },
        { label: "上报器", copy: "把运行事实送回治理系统的只读通道。" },
        { label: "事件投递箱", copy: "等待后端投递或重放的事件队列，本页不执行重放。" }
      ]
    };
  },
  computed: {
    workbench() {
      return this.data.sdlcRunWorkbench || {
        summary: {
          adapter_status: "materialized",
          proof_state: "unverified",
          dry_run_state: "empty",
          reporter_ready: 0,
          pending_proofs: 0,
          primary_action: "等待后端快照",
          safety_note: "尚未取得 Ai_AutoSDLC 运行工作台。"
        },
        reporter: [],
        outbox: [],
        eligibility: [],
        guardrails: []
      };
    },
    blockedConditions() {
      return this.workbench.eligibility
        .filter((item) => item.failed_conditions && item.failed_conditions !== "无")
        .length;
    }
  },
  methods: {
    readableText(value) {
      return String(value || "")
        .replaceAll("verified_loaded", "已验证加载")
        .replaceAll("materialized/unverified", "已生成配置/未验证")
        .replaceAll("materialized", "已生成配置")
        .replaceAll("unverified", "未验证")
        .replaceAll("Outbox Replay", "事件重放")
        .replaceAll("Outbox delivered", "事件已投递")
        .replaceAll("Outbox", "事件投递箱")
        .replaceAll("Reporter", "上报器");
    },
    readableConditions(value) {
      const labels = {
        governance_loaded: "治理加载证明",
        source_signed: "来源签名",
        outbox_delivered: "事件投递证明"
      };
      return String(value || "无")
        .split(",")
        .map((item) => labels[item.trim()] || item.trim())
        .filter(Boolean)
        .join("、") || "无";
    }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">Ai_AutoSDLC 证明</p><h3>Ai_AutoSDLC 运行</h3></div>
        <p class="heading-copy">CLI 预演通过不代表治理已经激活；只有拿到机器可验证的加载证据，页面才会显示“已验证加载”。</p>
      </section>
      <term-glossary :terms="glossaryTerms" />
      <section class="summary-band evidence-vault-band">
        <div>
          <p class="eyebrow">运行证明工作台</p>
          <h4>上报器、事件投递与 L5 条件</h4>
          <p class="muted">{{ readableText(workbench.summary.safety_note) }}</p>
        </div>
        <dl class="evidence-vault-metrics connector-metrics">
          <div><dt>Adapter</dt><dd><status-badge :status="workbench.summary.adapter_status" /></dd></div>
          <div><dt>证明</dt><dd><status-badge :status="workbench.summary.proof_state" /></dd></div>
          <div><dt>上报器就绪</dt><dd>{{ workbench.summary.reporter_ready }}</dd></div>
          <div><dt>待补证明</dt><dd>{{ workbench.summary.pending_proofs }}</dd></div>
        </dl>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>处置红线</h4>
          <span class="muted">只读运行摘要</span>
        </div>
        <ul class="guardrail-list">
          <li v-for="item in workbench.guardrails" :key="item">{{ readableText(item) }}</li>
        </ul>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>证明来源</h4>
          <span class="muted">dry-run 与治理激活分开展示</span>
        </div>
        <data-table
          :columns="columns"
          :rows="data.sdlcRuns"
          empty-title="暂无 Ai_AutoSDLC 运行证明"
          empty-detail="当前快照没有运行证明记录；完成 dry-run 和机器可验证加载证明后会在这里显示。"
        />
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>上报器与凭证</h4>
          <span class="muted">“可用”必须有机器证明</span>
        </div>
        <data-table
          :columns="reporterColumns"
          :rows="workbench.reporter"
          empty-title="暂无上报器记录"
          empty-detail="上报器显示可用时必须有机器证明；没有记录时不能推导“已验证加载”。"
        />
        <div class="boundary-list">
          <h5 class="boundary-title">上报器边界</h5>
          <div v-for="item in workbench.reporter" :key="item.id + '_boundary'" class="boundary-row connector-boundary-row">
            <strong>{{ item.command }}</strong>
            <span>{{ item.primary_action }}</span>
            <small>{{ readableText(item.integration_mode) }} · {{ readableText(item.proof_source) }} · {{ readableText(item.safety_note) }}</small>
          </div>
        </div>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>事件投递</h4>
          <span class="muted">本页只展示，不执行重放</span>
        </div>
        <data-table
          :columns="outboxColumns"
          :rows="workbench.outbox"
          empty-title="暂无事件投递记录"
          empty-detail="事件已投递只表示投递状态；没有记录时不会提升 L5 证据等级。"
        />
        <div class="boundary-list">
          <h5 class="boundary-title">回放边界</h5>
          <div v-for="item in workbench.outbox" :key="item.id + '_boundary'" class="boundary-row connector-boundary-row">
            <strong>{{ item.run_id }}</strong>
            <span>{{ readableText(item.evidence_impact) }}</span>
            <small>{{ readableText(item.replay_boundary) }} · {{ readableText(item.safety_note) }}</small>
          </div>
        </div>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>L5 条件</h4>
          <span class="muted">{{ blockedConditions }} 条仍需补齐</span>
        </div>
        <data-table
          :columns="eligibilityColumns"
          :rows="workbench.eligibility"
          empty-title="暂无 L5 条件记录"
          empty-detail="当前没有可复核的 L5 条件；出现缺口后会展示缺失条件和下一步。"
        />
        <div class="boundary-list">
          <h5 class="boundary-title">缺失条件</h5>
          <div v-for="item in workbench.eligibility" :key="item.id + '_conditions'" class="boundary-row connector-boundary-row">
            <strong>{{ item.run_id }}</strong>
            <span>{{ readableConditions(item.failed_conditions) }}</span>
            <small>{{ readableText(item.safety_note) }}</small>
          </div>
        </div>
      </section>
    </div>
  `
};
