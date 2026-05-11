import { StatusBadge } from "./StatusBadge.js";

export const DataTable = {
  name: "DataTable",
  components: {
    StatusBadge
  },
  props: {
    columns: { type: Array, required: true },
    rows: { type: Array, required: true },
    rowActionLabel: { type: String, default: "" },
    emptyTitle: { type: String, default: "暂无记录" },
    emptyDetail: { type: String, default: "当前没有需要处理的数据，后续快照同步后会在这里展示。" }
  },
  computed: {
    colspan() {
      return this.columns.length + (this.rowActionLabel ? 1 : 0);
    }
  },
  methods: {
    displayValue(value) {
      return String(value ?? "")
        .replaceAll("verified_loaded", "已验证加载")
        .replaceAll("materialized/unverified", "已生成配置/未验证")
        .replaceAll("materialized", "已生成配置")
        .replaceAll("unverified", "未验证")
        .replaceAll("require_online", "在线校验")
        .replaceAll("Grant", "授权票")
        .replaceAll("TTL", "有效期")
        .replaceAll("DLQ", "异常队列")
        .replaceAll("Outbox Replay", "事件重放")
        .replaceAll("Outbox delivered", "事件已投递")
        .replaceAll("Outbox", "事件投递箱")
        .replaceAll("ReporterCredential", "上报器凭证")
        .replaceAll("Reporter", "上报器")
        .replaceAll("IngestionToken", "接入令牌")
        .replaceAll("DeviceKey", "设备密钥")
        .replaceAll("ready_for_manual_approval", "待人工审批")
        .replaceAll("needs_human_review", "需人工复核")
        .replaceAll("insufficient_evidence", "证据不足")
        .replaceAll("needs_review", "需复核")
        .replaceAll("review_required", "需复核")
        .replaceAll("disable_review_recommended", "建议禁用复核")
        .replaceAll("scorer_rollout", "评分器发布")
        .replaceAll("quality_evidence", "质量证据")
        .replaceAll("lifecycle", "生命周期")
        .replaceAll("missing_or_low_confidence_evidence", "缺失或低置信证据")
        .replaceAll("collect_more_evidence", "补充证据")
        .replaceAll("collect_more_samples", "补充样本")
        .replaceAll("submit_for_manual_rollout_approval", "提交人工发布审批")
        .replaceAll("open_ops_review", "打开人工复核")
        .replaceAll("open_disable_review", "打开禁用复核")
        .replaceAll("watching", "观察中")
        .replaceAll("watch", "观察")
        .replaceAll("none", "无");
    }
  },
  template: `
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th v-for="column in columns" :key="column.key">{{ column.label }}</th>
            <th v-if="rowActionLabel">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!rows.length" class="empty-table-row">
            <td :colspan="colspan">
              <div class="table-empty-state">
                <strong>{{ emptyTitle }}</strong>
                <span>{{ emptyDetail }}</span>
              </div>
            </td>
          </tr>
          <tr v-for="row in rows" :key="row.id || row.run_id || row.approval_id || row.evidence_id">
            <td v-for="column in columns" :key="column.key" :data-label="column.label">
              <status-badge v-if="column.type === 'status'" :status="row[column.key]" />
              <span v-else>{{ displayValue(row[column.key]) }}</span>
            </td>
            <td v-if="rowActionLabel" data-label="操作">
              <button class="table-action" type="button" @click="$emit('row-action', row)">{{ rowActionLabel }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  `
};
