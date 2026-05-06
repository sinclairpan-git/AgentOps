import { StatusBadge } from "../components/StatusBadge.js";

export const EvidenceExplorerView = {
  name: "EvidenceExplorerView",
  components: {
    StatusBadge
  },
  props: {
    data: { type: Object, required: true }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">证据安全</p><h3>证据检索</h3></div>
        <p class="heading-copy">页面只展示脱敏摘要、哈希和访问状态；原文载荷展示被契约阻断。</p>
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
          <ent-button tone="secondary">{{ item.raw_access_state === 'permission_denied' ? '申请权限' : '查看安全摘要' }}</ent-button>
        </ent-card>
      </section>
    </div>
  `
};
