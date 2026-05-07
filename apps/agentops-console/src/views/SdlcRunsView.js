import { DataTable } from "../components/DataTable.js";

export const SdlcRunsView = {
  name: "SdlcRunsView",
  components: {
    DataTable
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
        { key: "reporter_status", label: "Reporter", type: "status" },
        { key: "credential_status", label: "凭证", type: "status" },
        { key: "source_signed", label: "签名", type: "status" },
        { key: "governance_state", label: "治理状态", type: "status" },
        { key: "primary_action", label: "下一步" }
      ],
      outboxColumns: [
        { key: "run_id", label: "运行" },
        { key: "outbox_status", label: "Outbox", type: "status" },
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
        { key: "outbox_delivered", label: "Outbox 投递", type: "status" },
        { key: "next_action", label: "下一步" }
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
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">Ai_AutoSDLC 证明</p><h3>Ai_AutoSDLC 运行</h3></div>
        <p class="heading-copy">CLI dry-run 通过不代表 adapter 已完成治理激活；只有机器可验证证据才能进入 verified_loaded。</p>
      </section>
      <section class="summary-band evidence-vault-band">
        <div>
          <p class="eyebrow">运行证明工作台</p>
          <h4>Reporter、Outbox 与 L5 条件</h4>
          <p class="muted">{{ workbench.summary.safety_note }}</p>
        </div>
        <dl class="evidence-vault-metrics connector-metrics">
          <div><dt>Adapter</dt><dd>{{ workbench.summary.adapter_status }}</dd></div>
          <div><dt>证明</dt><dd>{{ workbench.summary.proof_state }}</dd></div>
          <div><dt>Reporter 就绪</dt><dd>{{ workbench.summary.reporter_ready }}</dd></div>
          <div><dt>待补证明</dt><dd>{{ workbench.summary.pending_proofs }}</dd></div>
        </dl>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>处置红线</h4>
          <span class="muted">只读运行摘要</span>
        </div>
        <ul class="guardrail-list">
          <li v-for="item in workbench.guardrails" :key="item">{{ item }}</li>
        </ul>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>证明来源</h4>
          <span class="muted">dry-run 与治理激活分开展示</span>
        </div>
        <data-table :columns="columns" :rows="data.sdlcRuns" />
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>Reporter 与凭证</h4>
          <span class="muted">active 必须有机器证明</span>
        </div>
        <data-table :columns="reporterColumns" :rows="workbench.reporter" />
        <div class="boundary-list">
          <h5 class="boundary-title">Reporter 边界</h5>
          <div v-for="item in workbench.reporter" :key="item.id + '_boundary'" class="boundary-row connector-boundary-row">
            <strong>{{ item.command }}</strong>
            <span>{{ item.primary_action }}</span>
            <small>{{ item.integration_mode }} · {{ item.proof_source }} · {{ item.safety_note }}</small>
          </div>
        </div>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>Outbox 投递</h4>
          <span class="muted">本页不执行 Outbox Replay</span>
        </div>
        <data-table :columns="outboxColumns" :rows="workbench.outbox" />
        <div class="boundary-list">
          <h5 class="boundary-title">回放边界</h5>
          <div v-for="item in workbench.outbox" :key="item.id + '_boundary'" class="boundary-row connector-boundary-row">
            <strong>{{ item.run_id }}</strong>
            <span>{{ item.evidence_impact }}</span>
            <small>{{ item.replay_boundary }} · {{ item.safety_note }}</small>
          </div>
        </div>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>L5 条件</h4>
          <span class="muted">{{ blockedConditions }} 条仍需补齐</span>
        </div>
        <data-table :columns="eligibilityColumns" :rows="workbench.eligibility" />
        <div class="boundary-list">
          <h5 class="boundary-title">缺失条件</h5>
          <div v-for="item in workbench.eligibility" :key="item.id + '_conditions'" class="boundary-row connector-boundary-row">
            <strong>{{ item.run_id }}</strong>
            <span>{{ item.failed_conditions }}</span>
            <small>{{ item.safety_note }}</small>
          </div>
        </div>
      </section>
    </div>
  `
};
