import { DataTable } from "../components/DataTable.js";

export const ApprovalCenterView = {
  name: "ApprovalCenterView",
  components: {
    DataTable
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
        { key: "grant_status", label: "Grant", type: "status" },
        { key: "policy_version", label: "策略版本" },
        { key: "resource_scope", label: "授权范围" },
        { key: "ttl_summary", label: "TTL" },
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
    openApproval(row) {
      this.$emit("open-action-detail", `action_approval_${row.approval_id}`);
    }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">人工控制</p><h3>审批中心</h3></div>
        <p class="heading-copy">审批状态、SLA、补充材料和 Grant 状态始终绑定原始策略请求；本页只展示人工处置摘要，不执行生产写操作。</p>
      </section>
      <section class="summary-band evidence-vault-band">
        <div>
          <p class="eyebrow">人工审批与 Grant 工作台</p>
          <h4>审批队列</h4>
          <p class="muted">把高风险动作审批、补充材料、限时 Grant 和审计回显放在同一个只读工作台。</p>
        </div>
        <dl class="evidence-vault-metrics">
          <div><dt>待处理</dt><dd>{{ approvalWorkbench.queues.filter((item) => item.status === 'pending').length }}</dd></div>
          <div><dt>已升级</dt><dd>{{ approvalWorkbench.queues.filter((item) => item.status === 'escalated').length }}</dd></div>
          <div><dt>有效 Grant</dt><dd>{{ approvalWorkbench.grants.filter((item) => item.grant_status === 'active').length }}</dd></div>
        </dl>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>处置红线</h4>
          <span class="muted">只读审批摘要</span>
        </div>
        <ul class="guardrail-list">
          <li v-for="item in approvalWorkbench.guardrails" :key="item">{{ item }}</li>
        </ul>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>审批队列</h4>
          <span class="muted">审批原因、SLA、补充材料与审计引用</span>
        </div>
        <data-table :columns="queueColumns" :rows="approvalWorkbench.queues" row-action-label="查看处置记录" @row-action="openApproval" />
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>Grant 影响</h4>
          <span class="muted">绑定策略版本、资源范围和授权时限</span>
        </div>
        <data-table :columns="grantColumns" :rows="approvalWorkbench.grants" />
        <div class="boundary-list" aria-label="Grant 消费边界">
          <h5 class="boundary-title">消费边界与撤销状态</h5>
          <div v-for="item in approvalWorkbench.grants" :key="item.id + '_boundary'" class="boundary-row">
            <strong>{{ item.approval_id }}</strong>
            <span>{{ item.consumption_policy }}</span>
            <small>{{ item.revocation_state }} · {{ item.audit_id }}</small>
          </div>
        </div>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>审批审计轨迹</h4>
          <span class="muted">申请、升级、批准、撤销可追溯</span>
        </div>
        <data-table :columns="auditColumns" :rows="approvalWorkbench.auditTrail" />
      </section>
    </div>
  `
};
