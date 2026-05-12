import { DataTable } from "../components/DataTable.js";
import { TermGlossary } from "../components/TermGlossary.js";

export const ConnectorStatusView = {
  name: "ConnectorStatusView",
  components: {
    DataTable,
    TermGlossary
  },
  props: {
    data: { type: Object, required: true }
  },
  data() {
    return {
      healthColumns: [
        { key: "name", label: "连接器" },
        { key: "status", label: "状态", type: "status" },
        { key: "last_seen_at", label: "最后心跳" },
        { key: "freshness", label: "新鲜度" },
        { key: "rate_limit_state", label: "限流", type: "status" },
        { key: "rate_limit_detail", label: "限流说明" },
        { key: "owner", label: "负责人" }
      ],
      dlqColumns: [
        { key: "connector_id", label: "连接器" },
        { key: "dlq_depth", label: "异常队列积压" },
        { key: "oldest_event_age", label: "最旧事件" },
        { key: "replay_state", label: "回放状态", type: "status" },
        { key: "retry_window", label: "回放窗口" },
        { key: "audit_id", label: "审计引用" }
      ],
      trailColumns: [
        { key: "connector_id", label: "连接器" },
        { key: "stage", label: "阶段" },
        { key: "occurred_at", label: "发生时间" },
        { key: "summary", label: "同步摘要" },
        { key: "owner", label: "负责人" },
        { key: "status", label: "状态", type: "status" }
      ],
      mcpA2aColumns: [
        { key: "protocol", label: "协议" },
        { key: "gateway_state", label: "Runtime Gateway", type: "status" },
        { key: "policy_check_state", label: "Policy Check", type: "status" },
        { key: "evidence_state", label: "证据状态", type: "status" },
        { key: "subject_agent_id", label: "Agent" },
        { key: "audit_id", label: "审计引用" }
      ],
      exporterColumns: [
        { key: "exporter_id", label: "Exporter" },
        { key: "exporter_type", label: "类型" },
        { key: "configuration_state", label: "配置", type: "status" },
        { key: "dispatch_state", label: "派发", type: "status" },
        { key: "configuration_hash", label: "配置哈希" }
      ],
      handoffColumns: [
        { key: "agent_id", label: "Agent" },
        { key: "version", label: "版本" },
        { key: "handoff_count", label: "移交数" },
        { key: "failed_handoff_count", label: "失败数" },
        { key: "handoff_quality_state", label: "质量状态", type: "status" },
        { key: "audit_id", label: "审计引用" }
      ],
      riskProfileColumns: [
        { key: "agent_id", label: "Agent" },
        { key: "version", label: "版本" },
        { key: "risk_profile_state", label: "风险画像", type: "status" },
        { key: "risk_factor_count", label: "风险因子" },
        { key: "recommended_action", label: "建议动作" },
        { key: "audit_id", label: "审计引用" }
      ],
      glossaryTerms: [
        { label: "异常队列", copy: "处理失败或待复核的事件集合，避免问题被静默丢失。" },
        { label: "事件重放", copy: "按审批后的安全流程重新投递事件，本页只展示状态。" },
        { label: "已验证加载", copy: "机器证明确认治理规则已被真实加载。" },
        { label: "限流", copy: "连接器主动降速，防止外部系统或证据链被压垮。" },
        { label: "Runtime Gateway", copy: "MCP/A2A 外部访问必须经过的运行时治理入口。" },
        { label: "直连禁止", copy: "外部工具和 Agent 间通信不得绕过网关、策略和证据校验。" },
        { label: "dry-run", copy: "仅生成摘要和配置哈希，不向外部系统写入。" }
      ]
    };
  },
  computed: {
    connectorWorkbench() {
      return this.data.connectorWorkbench || {
        health: [],
        dlq: [],
        syncTrail: [],
        ecosystemGovernance: this.emptyEcosystemGovernance(),
        guardrails: []
      };
    },
    ecosystemGovernance() {
      return this.connectorWorkbench.ecosystemGovernance || this.emptyEcosystemGovernance();
    },
    degradedCount() {
      return this.connectorWorkbench.health.filter((item) => item.status !== "healthy").length;
    },
    dlqRiskCount() {
      return this.connectorWorkbench.dlq.filter((item) => item.replay_state === "pending").length;
    },
    unverifiedCount() {
      return this.connectorWorkbench.health.filter((item) =>
        item.status === "materialized" || /verified_loaded/.test(item.evidence_impact || "")
      ).length;
    },
    directConnectionText() {
      return this.ecosystemGovernance.summary.direct_connection_allowed ? "需复核" : "直连禁止";
    },
    externalWriteText() {
      return this.ecosystemGovernance.summary.external_write_enabled ? "需复核" : "仅 dry-run";
    }
  },
  methods: {
    emptyEcosystemGovernance() {
      return {
        mcp_a2a: [],
        exporters: [],
        handoffs: [],
        riskProfiles: [],
        summary: {
          runtime_gateway_required: true,
          direct_connection_allowed: false,
          external_write_enabled: false,
          network_dispatch_performed: false,
          runtime_execution_performed: false,
          automatic_store_action: false,
          notification_sent: false,
          monitored_agent_count: 0,
          ecosystem_state: "not_configured"
        },
        guardrails: []
      };
    },
    readableText(value) {
      return String(value || "")
        .replaceAll("verified_loaded", "已验证加载")
        .replaceAll("materialized", "已生成配置")
        .replaceAll("unverified", "未验证")
        .replaceAll("DLQ", "异常队列")
        .replaceAll("Outbox Replay", "事件重放")
        .replaceAll("Outbox", "事件投递箱")
        .replaceAll("require_online", "在线校验")
        .replaceAll("not_configured", "未配置")
        .replaceAll("configured", "已配置")
        .replaceAll("not_started", "未开始")
        .replaceAll("summary_only", "仅摘要")
        .replaceAll("insufficient_data", "证据不足")
        .replaceAll("needs_review", "需复核");
    }
  },
  template: `
    <div class="view-stack">
      <section class="page-heading">
        <div><p class="eyebrow">集成治理</p><h3>连接器状态</h3></div>
        <p class="heading-copy">统一查看 Git、PR、CI、测试、IAM、证据、策略和生态连接器的新鲜度、限流、异常队列、回放边界与降级影响。</p>
      </section>
      <term-glossary :terms="glossaryTerms" />
      <section class="summary-band evidence-vault-band">
        <div>
          <p class="eyebrow">连接器健康工作台</p>
          <h4>新鲜度、限流与证据影响</h4>
          <p class="muted">“已生成配置/未验证”只能证明配置或预演存在，不构成 verified_loaded（已验证加载）的治理激活证明。</p>
        </div>
        <dl class="evidence-vault-metrics connector-metrics">
          <div><dt>连接器</dt><dd>{{ connectorWorkbench.health.length }}</dd></div>
          <div><dt>需复核</dt><dd>{{ degradedCount }}</dd></div>
          <div><dt>异常队列风险</dt><dd>{{ dlqRiskCount }}</dd></div>
          <div><dt>未验证</dt><dd>{{ unverifiedCount }}</dd></div>
        </dl>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>处置红线</h4>
          <span class="muted">只读连接器摘要</span>
        </div>
        <ul class="guardrail-list">
          <li v-for="item in connectorWorkbench.guardrails" :key="item">{{ readableText(item) }}</li>
        </ul>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>生态治理</h4>
          <span class="muted">MCP/A2A、Exporter dry-run、多 Agent 移交与复杂风险画像</span>
        </div>
        <dl class="evidence-vault-metrics connector-metrics">
          <div><dt>Runtime Gateway</dt><dd>{{ ecosystemGovernance.summary.runtime_gateway_required ? "必须经过" : "需复核" }}</dd></div>
          <div><dt>直连禁止</dt><dd>{{ directConnectionText }}</dd></div>
          <div><dt>Exporter dry-run</dt><dd>{{ externalWriteText }}</dd></div>
          <div><dt>监控 Agent</dt><dd>{{ ecosystemGovernance.summary.monitored_agent_count }}</dd></div>
        </dl>
        <ul class="guardrail-list compact-guardrails">
          <li v-for="item in ecosystemGovernance.guardrails" :key="item">{{ readableText(item) }}</li>
        </ul>
        <div class="subsection-stack">
          <div>
            <div class="section-title sub-title">
              <h5>MCP/A2A Runtime Gateway</h5>
              <span class="muted">直连禁止，策略校验必需</span>
            </div>
            <data-table
              :columns="mcpA2aColumns"
              :rows="ecosystemGovernance.mcp_a2a"
              empty-title="暂无 MCP/A2A 治理摘要"
              empty-detail="旧快照或未配置生态端点时仅显示安全空态，不推断已配置。"
            />
          </div>
          <div>
            <div class="section-title sub-title">
              <h5>Exporter dry-run</h5>
              <span class="muted">只展示 configuration_hash，不执行网络写入</span>
            </div>
            <data-table
              :columns="exporterColumns"
              :rows="ecosystemGovernance.exporters"
              empty-title="暂无 Exporter 摘要"
              empty-detail="当前没有 Exporter dry-run 记录；本页不会发起派发。"
            />
          </div>
          <div>
            <div class="section-title sub-title">
              <h5>多 Agent 移交</h5>
              <span class="muted">只读取 TraceSpan 摘要，不重跑 handoff</span>
            </div>
            <data-table
              :columns="handoffColumns"
              :rows="ecosystemGovernance.handoffs"
              empty-title="暂无 handoff 摘要"
              empty-detail="没有 TraceSpan 移交摘要时显示证据不足，不执行运行时移交。"
            />
          </div>
          <div>
            <div class="section-title sub-title">
              <h5>复杂风险画像</h5>
              <span class="muted">人工复核建议，不自动处置</span>
            </div>
            <data-table
              :columns="riskProfileColumns"
              :rows="ecosystemGovernance.riskProfiles"
              empty-title="暂无复杂风险画像"
              empty-detail="风险画像只读展示健康、异常队列和移交摘要，不写 Store、不发送通知。"
            />
          </div>
        </div>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>健康与限流</h4>
          <span class="muted">15 分钟 SLO，超过 20 分钟告警</span>
        </div>
        <data-table
          :columns="healthColumns"
          :rows="connectorWorkbench.health"
          empty-title="暂无连接器心跳"
          empty-detail="当前快照没有连接器健康记录；接入 Git、PR、CI、IAM 等连接器后会显示新鲜度、限流和负责人。"
        />
        <div class="boundary-list" aria-label="连接器证据影响">
          <h5 class="boundary-title">证据等级与处置建议</h5>
          <div v-for="item in connectorWorkbench.health" :key="item.id + '_impact'" class="boundary-row connector-boundary-row">
            <strong>{{ item.name }}</strong>
            <span>{{ readableText(item.evidence_impact) }}</span>
            <small>限流：{{ readableText(item.rate_limit_detail) }} · {{ readableText(item.primary_action) }} · {{ readableText(item.secondary_action) }} · {{ item.request_id }}</small>
          </div>
        </div>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>DLQ 与 Outbox Replay</h4>
          <span class="muted">DLQ 即异常队列，Outbox Replay 即事件重放；本页只读展示，不执行回放</span>
        </div>
        <data-table
          :columns="dlqColumns"
          :rows="connectorWorkbench.dlq"
          empty-title="暂无异常队列风险"
          empty-detail="当前没有死信或回放风险；出现积压后会显示最旧事件、回放窗口和审计引用。"
        />
        <div class="boundary-list" aria-label="异常队列回放边界">
          <h5 class="boundary-title">降级策略</h5>
          <div v-for="item in connectorWorkbench.dlq" :key="item.id + '_policy'" class="boundary-row connector-boundary-row">
            <strong>{{ item.connector_id }}</strong>
            <span>{{ readableText(item.degrade_policy) }}</span>
            <small>{{ readableText(item.safety_note) }}</small>
          </div>
        </div>
      </section>
      <section class="ent-card">
        <div class="section-title">
          <h4>同步轨迹</h4>
          <span class="muted">心跳、降级与待证明状态可追溯</span>
        </div>
        <data-table
          :columns="trailColumns"
          :rows="connectorWorkbench.syncTrail"
          empty-title="暂无同步轨迹"
          empty-detail="心跳、降级、限流和待证明状态发生后会记录在这里。"
        />
      </section>
    </div>
  `
};
