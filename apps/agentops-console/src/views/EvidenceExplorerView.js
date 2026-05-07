import { StatusBadge } from "../components/StatusBadge.js";

export const EvidenceExplorerView = {
  name: "EvidenceExplorerView",
  components: {
    StatusBadge
  },
  props: {
    data: { type: Object, required: true }
  },
  computed: {
    evidenceVault() {
      return this.data.evidenceVault || {
        requests: [],
        grants: [],
        auditTrail: [],
        guardrails: []
      };
    },
    requestColumns() {
      return [
        { key: "evidence_id", label: "证据" },
        { key: "requester", label: "申请方" },
        { key: "reason", label: "申请理由" },
        { key: "status", label: "状态", type: "status" },
        { key: "ttl_summary", label: "TTL" },
        { key: "primary_action", label: "下一步" }
      ];
    },
    grantColumns() {
      return [
        { key: "evidence_id", label: "证据" },
        { key: "scope", label: "授权范围" },
        { key: "status", label: "状态", type: "status" },
        { key: "expires_at", label: "到期" },
        { key: "audit_id", label: "审计" }
      ];
    },
    auditColumns() {
      return [
        { key: "evidence_id", label: "证据" },
        { key: "stage", label: "阶段" },
        { key: "summary", label: "审计摘要" },
        { key: "owner", label: "负责人" },
        { key: "status", label: "状态", type: "status" }
      ];
    }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">证据安全</p><h3>证据检索与 Evidence Vault</h3></div>
        <p class="heading-copy">页面只展示脱敏摘要、哈希、申请、授权和审计状态；默认不展示原文，原文载荷展示被契约阻断。</p>
      </section>
      <section class="summary-band evidence-vault-band">
        <div>
          <p class="eyebrow">Evidence Vault 访问工作台</p>
          <h4>原文访问申请</h4>
          <p class="muted">把原文访问从“隐形后台动作”变成可审批、可追踪、可解释的只读流程。</p>
        </div>
        <dl class="evidence-vault-metrics">
          <div><dt>申请</dt><dd>{{ evidenceVault.requests.length }}</dd></div>
          <div><dt>限时授权</dt><dd>{{ evidenceVault.grants.filter((item) => item.status === 'active').length }}</dd></div>
          <div><dt>审计轨迹</dt><dd>{{ evidenceVault.auditTrail.length }}</dd></div>
        </dl>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>保护规则</h4>
          <span class="muted">默认不展示原文</span>
        </div>
        <ul class="guardrail-list">
          <li v-for="item in evidenceVault.guardrails" :key="item">{{ item }}</li>
        </ul>
      </section>
      <section class="card-grid">
        <ent-card v-for="item in data.evidence" :key="item.evidence_id">
          <div class="section-title">
            <h4>{{ item.evidence_id }}</h4>
            <status-badge :status="item.raw_access_state" />
          </div>
          <p class="summary-copy">{{ item.raw_access_state === 'redaction_failed' ? '脱敏失败，摘要正文已隐藏。' : item.summary }}</p>
          <dl class="detail-list">
            <div><dt>运行</dt><dd>{{ item.run_id }}</dd></div>
            <div><dt>载荷哈希</dt><dd>{{ item.payload_hash }}</dd></div>
            <div><dt>审计</dt><dd>{{ item.audit_id }}</dd></div>
            <div v-if="item.denied_scope"><dt>拒绝范围</dt><dd>{{ item.denied_scope }}</dd></div>
          </dl>
          <ent-button tone="secondary" @click="$emit('open-action-detail', 'action_evidence_' + item.evidence_id)">
            {{ item.raw_access_state === 'permission_denied' ? '查看申请预案' : '查看处置详情' }}
          </ent-button>
        </ent-card>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>原文访问申请</h4>
          <span class="muted">只读申请摘要</span>
        </div>
        <data-table :columns="requestColumns" :rows="evidenceVault.requests" />
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>限时授权</h4>
          <span class="muted">不提供原文下载</span>
        </div>
        <data-table :columns="grantColumns" :rows="evidenceVault.grants" />
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>审计轨迹</h4>
          <span class="muted">哈希、申请和授权可追溯</span>
        </div>
        <data-table :columns="auditColumns" :rows="evidenceVault.auditTrail" />
      </section>
    </div>
  `
};
