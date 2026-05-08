import { DataTable } from "../components/DataTable.js";
import { StatusBadge } from "../components/StatusBadge.js";
import { TermGlossary } from "../components/TermGlossary.js";

export const CredentialHandoffView = {
  name: "CredentialHandoffView",
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
      sessionColumns: [
        { key: "bootstrap_id", label: "启动会话" },
        { key: "bootstrap_status", label: "启动状态", type: "status" },
        { key: "credential_status", label: "凭证状态", type: "status" },
        { key: "installation_id", label: "安装标识" },
        { key: "device_id", label: "设备标识" },
        { key: "next_action_label", label: "下一步" },
        { key: "verified_loaded", label: "治理加载", type: "status" },
        { key: "l5_status", label: "L5", type: "status" }
      ],
      glossaryTerms: [
        { label: "只读回显", copy: "只展示后端事实，不在页面里签发、激活或撤销。" },
        { label: "签名测试", copy: "验证事件确实来自可信来源，但不等同治理已激活。" },
        { label: "已验证加载", copy: "需要机器证据证明治理规则真实加载。" },
        { label: "L5", copy: "最高等级证据，必须同时满足加载、签名、投递等条件。" }
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
    readableText(value) {
      return String(value || "")
        .replaceAll("verified_loaded", "已验证加载")
        .replaceAll("ReporterCredential", "上报器凭证")
        .replaceAll("IngestionToken", "接入令牌")
        .replaceAll("DeviceKey", "设备密钥")
        .replaceAll("infer_active", "本地推导可用")
        .replaceAll("issue_credential", "签发凭证")
        .replaceAll("issue_ingestion_token", "签发接入令牌")
        .replaceAll("issue_device_key", "签发设备密钥")
        .replaceAll("display_status", "展示状态")
        .replaceAll("show_next_action", "展示下一步")
        .replaceAll("active", "可用")
        .replaceAll("signature_verified", "签名测试通过");
    },
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
        <p class="heading-copy">展示 Agent Store 交接到 AgentOps 后的只读状态回显；本页不签发、不激活、不得本地推导 active（可用），也不推导“已验证加载”。</p>
      </section>
      <term-glossary :terms="glossaryTerms" />

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
          <p class="muted">不等同“已验证加载”或 L5。</p>
        </ent-card>
        <ent-card>
          <p class="eyebrow">已撤销</p>
          <h4>{{ workbench.summary.revoked || 0 }}</h4>
          <p class="muted">已重新签发 {{ workbench.summary.reissued || 0 }} 条。</p>
        </ent-card>
      </section>

      <section class="summary-band">
        <div>
          <p class="eyebrow">事实来源</p>
          <h4>{{ workbench.summary.agentops_fact_owner || "agentops" }}</h4>
          <p class="muted">{{ readableText(workbench.summary.safety_note) }}</p>
        </div>
        <status-badge :status="workbench.summary.verified_loaded || 'not_asserted'" />
      </section>

      <section class="view-stack">
        <div class="section-title">
          <h4>凭证状态回显</h4>
          <span>Agent Store 只消费展示字段</span>
        </div>
        <data-table
          :columns="sessionColumns"
          :rows="sessionRows"
          empty-title="暂无凭证联调记录"
          empty-detail="当前没有跨项目凭证回显；签发、签名测试、撤销或重新签发后会显示只读状态。"
        />
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
            <span>重新签发状态：{{ item.revocation_resolution }}</span>
            <span>reissue_id：{{ item.reissue_id }}</span>
            <span>新启动会话：{{ item.reissued_bootstrap_id }}</span>
            <span>新凭证：{{ item.reissued_credential_id }}</span>
            <span>允许动作：{{ readableText(item.allowed_actions) }}</span>
            <span>禁止动作：{{ readableText(item.forbidden_actions) }}</span>
          </div>
          <p class="muted">{{ item.display_scope }}</p>
        </ent-card>
      </section>

      <section class="guardrail-list">
        <div v-for="guardrail in workbench.guardrails" :key="guardrail" class="guardrail-item">
          {{ readableText(guardrail) }}
        </div>
      </section>
    </div>
  `
};
