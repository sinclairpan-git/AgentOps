import { DataTable } from "../components/DataTable.js";
import { TermGlossary } from "../components/TermGlossary.js";

export const ApprovalCenterView = {
  name: "ApprovalCenterView",
  components: {
    DataTable,
    TermGlossary
  },
  props: {
    data: { type: Object, required: true }
  },
  data() {
    return {
      queueColumns: [
        { key: "approval_id", label: "审批" },
        { key: "requester", label: "申请方" },
        { key: "reason", label: "审批原因" },
        { key: "status", label: "状态", type: "status" },
        { key: "sla_state", label: "SLA" },
        { key: "primary_action", label: "建议处置" },
        { key: "secondary_action", label: "下一步摘要" },
        { key: "audit_id", label: "审计引用" }
      ],
      grantColumns: [
        { key: "approval_id", label: "审批" },
        { key: "grant_status", label: "授权票", type: "status" },
        { key: "policy_version", label: "策略版本" },
        { key: "resource_scope", label: "授权范围" },
        { key: "ttl_summary", label: "有效期" },
        { key: "expires_at", label: "到期" },
        { key: "audit_id", label: "审计引用" }
      ],
      auditColumns: [
        { key: "approval_id", label: "审批" },
        { key: "stage", label: "阶段" },
        { key: "occurred_at", label: "发生时间" },
        { key: "summary", label: "审计摘要" },
        { key: "owner", label: "负责人" },
        { key: "status", label: "状态", type: "status" },
        { key: "audit_id", label: "审计引用" }
      ],
      glossaryTerms: [
        { label: "授权票", copy: "临时允许某个高风险动作的票据，有范围和到期时间。" },
        { label: "有效期", copy: "授权票能被使用的时间窗口，过期后不能继续放行。" },
        { label: "SLA", copy: "约定的处理时限，用来判断审批是否需要升级。" }
      ]
    };
  },
  computed: {
    approvalWorkbench() {
      return this.data.approvalWorkbench || {
        queues: [],
        grants: [],
        auditTrail: [],
        guardrails: []
      };
    }
  },
  methods: {
    readableText(value) {
      return String(value || "")
        .replaceAll("Grant", "授权票")
        .replaceAll("TTL", "有效期");
    },
    openApproval(row) {
      this.$emit("open-action-detail", `action_approval_${row.approval_id}`);
    }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">人工控制</p><h3>审批中心</h3></div>
        <p class="heading-copy">审批状态、SLA、补充材料和授权票状态始终绑定原始策略请求；本页只展示人工处置摘要，不执行生产写操作。</p>
      </section>
      <term-glossary :terms="glossaryTerms" />
      <section class="summary-band evidence-vault-band">
        <div>
          <p class="eyebrow">人工审批与授权票工作台</p>
          <h4>审批队列</h4>
          <p class="muted">把高风险动作审批、补充材料、限时授权票和审计回显放在同一个只读工作台。</p>
        </div>
        <dl class="evidence-vault-metrics">
          <div><dt>待处理</dt><dd>{{ approvalWorkbench.queues.filter((item) => item.status === 'pending').length }}</dd></div>
          <div><dt>已升级</dt><dd>{{ approvalWorkbench.queues.filter((item) => item.status === 'escalated').length }}</dd></div>
          <div><dt>有效授权票</dt><dd>{{ approvalWorkbench.grants.filter((item) => item.grant_status === 'active').length }}</dd></div>
        </dl>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>处置红线</h4>
          <span class="muted">只读审批摘要</span>
        </div>
        <ul class="guardrail-list">
          <li v-for="item in approvalWorkbench.guardrails" :key="item">{{ readableText(item) }}</li>
        </ul>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>审批队列</h4>
          <span class="muted">审批原因、SLA、补充材料与审计引用</span>
        </div>
        <data-table
          :columns="queueColumns"
          :rows="approvalWorkbench.queues"
          row-action-label="查看处置记录"
          empty-title="暂无审批待办"
          empty-detail="当前没有需要人工处理的高风险动作。出现审批请求后会显示申请方、原因、SLA 和下一步。"
          @row-action="openApproval"
        />
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>授权票影响</h4>
          <span class="muted">绑定策略版本、资源范围和授权时限</span>
        </div>
        <data-table
          :columns="grantColumns"
          :rows="approvalWorkbench.grants"
          empty-title="暂无授权票影响"
          empty-detail="没有生效授权时，不会扩大任何资源范围；授权产生后会展示策略版本、有效期和审计引用。"
        />
        <div class="boundary-list" aria-label="授权票消费边界">
          <h5 class="boundary-title">消费边界与撤销状态</h5>
          <div v-for="item in approvalWorkbench.grants" :key="item.id + '_boundary'" class="boundary-row">
            <strong>{{ item.approval_id }}</strong>
            <span>{{ readableText(item.consumption_policy) }}</span>
            <small>{{ item.revocation_state }} · {{ item.audit_id }}</small>
          </div>
        </div>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>审批审计轨迹</h4>
          <span class="muted">申请、升级、批准、撤销可追溯</span>
        </div>
        <data-table
          :columns="auditColumns"
          :rows="approvalWorkbench.auditTrail"
          empty-title="暂无审批审计轨迹"
          empty-detail="申请、升级、批准、撤销发生后会记录到这里，便于复核。"
        />
      </section>
    </div>
  `
};
