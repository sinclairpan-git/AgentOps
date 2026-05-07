import { DataTable } from "../components/DataTable.js";
import { StatusBadge } from "../components/StatusBadge.js";

export const CredentialHandoffView = {
  name: "CredentialHandoffView",
  components: {
    DataTable,
    StatusBadge
  },
  props: {
    data: { type: Object, required: true }
  },
  data() {
    return {
      sessionColumns: [
        { key: "bootstrap_id", label: "启动会话" },
        { key: "bootstrap_status", label: "启动状态", type: "status" },
        { key: "credential_status", label: "凭证状态", type: "status" },
        { key: "installation_id", label: "安装标识" },
        { key: "device_id", label: "设备标识" },
        { key: "next_action_label", label: "下一步" },
        { key: "verified_loaded", label: "治理加载", type: "status" },
        { key: "l5_status", label: "L5", type: "status" }
      ]
    };
  },
  computed: {
    workbench() {
      const source = this.data.credentialHandoff || {};
      return {
        summary: source.summary || {},
        sessions: Array.isArray(source.sessions) ? source.sessions : [],
        guardrails: Array.isArray(source.guardrails) ? source.guardrails : []
      };
    },
    sessionRows() {
      return this.workbench.sessions.map((item) => ({
        ...item,
        next_action_label: this.actionLabel(item.next_action)
      }));
    }
  },
  methods: {
    actionLabel(action) {
      const labels = {
        issue_credential: "签发 AgentOps 凭证",
        send_signature_test_event: "发送签名测试事件",
        display_activation_result: "展示激活回显",
        reissue_credential: "重新签发凭证"
      };
      return labels[action] || action || "待确认";
    }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">跨项目联调</p><h3>凭证联调</h3></div>
        <p class="heading-copy">展示 Agent Store 交接到 AgentOps 后的只读状态回显；本页不签发、不激活、不得本地推导 active，也不推导 verified_loaded。</p>
      </section>

      <section class="panel-grid four">
        <ent-card>
          <p class="eyebrow">启动会话数量</p>
          <h4>{{ workbench.summary.bootstrap_count || 0 }}</h4>
          <p class="muted">来自 AgentOps 启动会话。</p>
        </ent-card>
        <ent-card>
          <p class="eyebrow">已签发</p>
          <h4>{{ workbench.summary.credential_issued || 0 }}</h4>
          <p class="muted">仅代表凭证对象已生成。</p>
        </ent-card>
        <ent-card>
          <p class="eyebrow">签名测试通过</p>
          <h4>{{ workbench.summary.signature_verified || 0 }}</h4>
          <p class="muted">不等同 verified_loaded 或 L5。</p>
        </ent-card>
        <ent-card>
          <p class="eyebrow">已撤销</p>
          <h4>{{ workbench.summary.revoked || 0 }}</h4>
          <p class="muted">撤销后只能展示重新签发建议。</p>
        </ent-card>
      </section>

      <section class="summary-band">
        <div>
          <p class="eyebrow">事实来源</p>
          <h4>{{ workbench.summary.agentops_fact_owner || "agentops" }}</h4>
          <p class="muted">{{ workbench.summary.safety_note }}</p>
        </div>
        <status-badge :status="workbench.summary.verified_loaded || 'not_asserted'" />
      </section>

      <section class="view-stack">
        <div class="section-title">
          <h4>凭证状态回显</h4>
          <span>Agent Store 只消费展示字段</span>
        </div>
        <data-table v-if="sessionRows.length" :columns="sessionColumns" :rows="sessionRows" />
        <ent-card v-else><p class="empty-state">暂无凭证联调记录。</p></ent-card>
      </section>

      <section class="panel-grid two">
        <ent-card v-for="item in workbench.sessions" :key="item.id">
          <div class="section-title">
            <h4>{{ item.bootstrap_id }}</h4>
            <status-badge :status="item.bootstrap_status" />
          </div>
          <div class="deep-link-grid">
            <span>credential_id：{{ item.credential_id }}</span>
            <span>token_id：{{ item.token_id }}</span>
            <span>device_key_id：{{ item.device_key_id }}</span>
            <span>signature_test_event_id：{{ item.signature_test_event_id }}</span>
            <span>revocation_id：{{ item.revocation_id }}</span>
            <span>撤销时间：{{ item.revoked_at }}</span>
            <span>撤销原因：{{ item.revocation_reason }}</span>
            <span>撤销范围：{{ item.revocation_scope }}</span>
            <span>允许动作：{{ item.allowed_actions }}</span>
            <span>禁止动作：{{ item.forbidden_actions }}</span>
          </div>
          <p class="muted">{{ item.display_scope }}</p>
        </ent-card>
      </section>

      <section class="guardrail-list">
        <div v-for="guardrail in workbench.guardrails" :key="guardrail" class="guardrail-item">
          {{ guardrail }}
        </div>
      </section>
    </div>
  `
};
