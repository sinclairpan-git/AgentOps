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
      taskGuardColumns: [
        { key: "run_id", label: "运行" },
        { key: "workitem", label: "工作项" },
        { key: "executable_task_id", label: "任务" },
        { key: "task_guard_state", label: "任务守卫", type: "status" },
        { key: "guard_result", label: "变更守卫", type: "status" },
        { key: "next_action", label: "下一步" }
      ],
      receiptColumns: [
        { key: "outbox_id", label: "Outbox" },
        { key: "producer", label: "生产者" },
        { key: "outbox_state", label: "状态", type: "status" },
        { key: "accepted_count", label: "接收" },
        { key: "rejected_count", label: "拒绝" },
        { key: "dlq_count", label: "DLQ" }
      ],
      readinessColumns: [
        { key: "run_id", label: "运行" },
        { key: "executable_task_id", label: "任务" },
        { key: "freshness_state", label: "新鲜度", type: "status" },
        { key: "policy_state", label: "策略", type: "status" },
        { key: "raw_payload_state", label: "原文" },
        { key: "l5_path", label: "L5 路径", type: "status" }
      ],
      adapterDiagnosticColumns: [
        { key: "run_id", label: "运行" },
        { key: "adapter_diagnostic_state", label: "Adapter 诊断", type: "status" },
        { key: "verified_loaded_semantics", label: "verified_loaded" },
        { key: "hard_gate", label: "硬门槛" },
        { key: "next_action", label: "下一步" }
      ],
      glossaryTerms: [
        { label: "可执行任务", copy: "Ai_AutoSDLC 输出的明确任务、工作项和允许变更范围。" },
        { label: "任务守卫", copy: "代码变更是否仍在可执行任务范围内的后端判定。" },
        { label: "verified_loaded", copy: "只作为 adapter 诊断展示，不再作为主路径硬门槛。" },
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
        taskGuard: [],
        outboxReceipts: [],
        evidenceReadiness: [],
        adapterDiagnostics: [],
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
        .replaceAll("diagnostic_only", "仅诊断")
        .replaceAll("hard_gate", "硬门槛")
        .replaceAll("false", "否")
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
        executable_task_linked: "可执行任务",
        task_guard_allowed: "任务守卫通过",
        governance_loaded: "治理加载诊断",
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
        <p class="heading-copy">接入主路径以可执行任务、任务守卫、签名事实、回执与证据就绪状态为准；verified_loaded 只作为 adapter 诊断展示。</p>
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
          <div><dt>任务守卫通过</dt><dd>{{ workbench.summary.task_guard_allowed || 0 }}</dd></div>
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
          <h4>可执行任务与任务守卫</h4>
          <span class="muted">L5 主路径</span>
        </div>
        <data-table
          :columns="taskGuardColumns"
          :rows="workbench.taskGuard"
          empty-title="暂无任务守卫记录"
          empty-detail="等待 Ai_AutoSDLC 发送 executable_task 与 code_guard 运行事实。"
        />
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>事件回执</h4>
          <span class="muted">只读接收回执</span>
        </div>
        <data-table
          :columns="receiptColumns"
          :rows="workbench.outboxReceipts"
          empty-title="暂无回执"
          empty-detail="收到 Ai_AutoSDLC outbox 后会展示接收、拒绝与 DLQ 摘要。"
        />
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>证据就绪状态</h4>
          <span class="muted">摘要、策略与新鲜度</span>
        </div>
        <data-table
          :columns="readinessColumns"
          :rows="workbench.evidenceReadiness"
          empty-title="暂无证据就绪状态"
          empty-detail="任务守卫通过后会展示可进入 L5 复核的证据状态。"
        />
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>Adapter 诊断</h4>
          <span class="muted">不作为硬门槛</span>
        </div>
        <data-table
          :columns="adapterDiagnosticColumns"
          :rows="workbench.adapterDiagnostics"
          empty-title="暂无 adapter 诊断"
          empty-detail="verified_loaded 只作为诊断字段，不替代任务与回执证据。"
        />
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
          <h4>Reporter 与凭证</h4>
          <span class="muted">Reporter 即上报器；“可用”必须有机器证明</span>
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
          <h4>Outbox 投递</h4>
          <span class="muted">Outbox 即事件投递箱；本页只展示，不执行 Outbox Replay</span>
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
