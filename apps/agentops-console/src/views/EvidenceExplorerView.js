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
        <div><p class="eyebrow">Vault safety</p><h3>Evidence Explorer</h3></div>
        <p class="heading-copy">Only redacted summaries, hashes and access states are rendered. Raw payload display is blocked by contract.</p>
      </section>
      <section class="card-grid">
        <ent-card v-for="item in data.evidence" :key="item.evidence_id">
          <div class="section-title">
            <h4>{{ item.evidence_id }}</h4>
            <status-badge :status="item.raw_access_state" />
          </div>
          <p class="summary-copy">{{ item.raw_access_state === 'redaction_failed' ? 'Redaction failed. Summary body withheld.' : item.summary }}</p>
          <dl class="detail-list">
            <div><dt>Run</dt><dd>{{ item.run_id }}</dd></div>
            <div><dt>Payload hash</dt><dd>{{ item.payload_hash }}</dd></div>
            <div><dt>Audit</dt><dd>{{ item.audit_id }}</dd></div>
            <div v-if="item.denied_scope"><dt>Denied scope</dt><dd>{{ item.denied_scope }}</dd></div>
          </dl>
          <ent-button tone="secondary">{{ item.raw_access_state === 'permission_denied' ? 'Request access' : 'View safe summary' }}</ent-button>
        </ent-card>
      </section>
    </div>
  `
};
